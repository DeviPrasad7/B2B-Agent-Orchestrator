from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field
import json
import asyncio

class WebSearchInput(BaseModel):
    query: str = Field(description="The company name or URL to search for")

class CrunchbaseInput(BaseModel):
    company_name: str = Field(description="The company name to lookup in crunchbase")

class LinkedInInput(BaseModel):
    company_name: str = Field(description="The company name to lookup on LinkedIn")

class EmployeeSearchInput(BaseModel):
    company_name: str = Field(description="The company name to search employees for")

def get_agent_tools(toolbox, agent_id: str):
    """
    Returns a dictionary of available tools that wrap the toolbox methods
    and emit real-time logs for the Custom Agent.
    """
    
    def log_action(msg: str, level: str = "INFO"):
        toolbox.emit_event("CustomAgentLog", {
            "agent_id": str(agent_id),
            "message": msg,
            "level": level
        })

    async def fetch_webpage(query: str) -> str:
        log_action(f"Initiating WebSearch for: {query}")
        try:
            url = query if query.startswith("http") else f"https://html.duckduckgo.com/html/?q={query}"
            res = await toolbox.fetch_webpage(url)
            log_action(f"WebSearch completed. Extracted {len(res.html_content)} bytes of HTML.")
            return res.text_content[:2000]
        except Exception as e:
            log_action(f"WebSearch failed: {str(e)}", level="ERROR")
            return f"Error: {str(e)}"

    async def fetch_crunchbase(company_name: str) -> str:
        log_action(f"Querying Crunchbase profile for: {company_name}")
        try:
            res = await toolbox.fetch_crunchbase(company_name)
            log_action(f"Crunchbase query successful for {company_name}.")
            return res.model_dump_json()
        except Exception as e:
            log_action(f"Crunchbase lookup failed: {str(e)}", level="ERROR")
            return f"Error: {str(e)}"

    async def scrape_linkedin(company_name: str) -> str:
        log_action(f"Scraping LinkedIn data for: {company_name}")
        try:
            res = await toolbox.scrape_linkedin(company_name)
            log_action(f"LinkedIn scrape successful for {company_name}.")
            return json.dumps(res)
        except Exception as e:
            log_action(f"LinkedIn scrape failed: {str(e)}", level="WARN")
            return f"Error: {str(e)}"

    async def find_employees(company_name: str) -> str:
        log_action(f"Searching employee directory for: {company_name}")
        try:
            res = await toolbox.find_company_employees(company_name)
            log_action(f"Employee search completed. Found {len(res)} employees.")
            return json.dumps(res)
        except Exception as e:
            log_action(f"Employee search failed: {str(e)}", level="WARN")
            return f"Error: {str(e)}"

    tools = {
        "WebSearch": StructuredTool.from_function(
            coroutine=fetch_webpage,
            name="WebSearch",
            description="Searches the web or fetches a specific URL for company information.",
            args_schema=WebSearchInput
        ),
        "Crunchbase": StructuredTool.from_function(
            coroutine=fetch_crunchbase,
            name="Crunchbase",
            description="Fetches detailed company profile, revenue, and funding data from Crunchbase.",
            args_schema=CrunchbaseInput
        ),
        "LinkedIn": StructuredTool.from_function(
            coroutine=scrape_linkedin,
            name="LinkedIn",
            description="Scrapes LinkedIn for company posts, follower count, and recent news.",
            args_schema=LinkedInInput
        ),
        "EmployeeSearch": StructuredTool.from_function(
            coroutine=find_employees,
            name="EmployeeSearch",
            description="Searches for employees or executives at a given company.",
            args_schema=EmployeeSearchInput
        )
    }
    
    return tools
