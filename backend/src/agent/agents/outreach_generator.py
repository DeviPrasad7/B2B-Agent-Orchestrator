"""
Outreach Generator Node.

This agent uses the discovered firmographics, tech stack, and decision maker contacts
to draft highly personalized outbound sales emails for each contact.
"""

from typing import Any
import json
from core.logging import logger

from ..state import GraphState
from ..utils import Toolbox
from services.memory_service import MemoryService
from ..base import AgentNode
from ..registry import register_agent

@register_agent(
    "outreach_generator_node",
    description="Drafts highly personalized outbound sales emails for decision-makers based on firmographics, tech stack, and competitor context."
)
class OutreachGeneratorNode(AgentNode):
    def __init__(self, toolbox: Toolbox, memory: MemoryService, config: dict):
        self.toolbox = toolbox
        self.memory = memory
        self.config = config

    async def __call__(self, state: GraphState) -> dict[str, Any]:
        data = state.get("data", {})
        contacts = data.get("contacts", [])
        company_name = data.get("company_name", "Unknown Company")
        
        if not contacts:
            return {
                "executed_agents": ["outreach_generator_node"],
                "recent_thoughts": ["No decision makers found to generate outreach for."]
            }
            
        recent_thoughts = []
        outreach_drafts = []
        
        for contact in contacts:
            contact_name = contact.get("name", "Decision Maker")
            contact_title = contact.get("title", "")
            
            recent_thoughts.append(f"Drafting personalized outreach for {contact_name} ({contact_title}).")
            
            prompt = f"""
You are a top-tier B2B sales development representative.
Your task is to draft a highly personalized, concise cold outreach email to a decision maker.

Company: {company_name}
Decision Maker: {contact_name}
Title: {contact_title}
Firmographics: {json.dumps(data.get("firmographics", {}))}
Tech Stack: {json.dumps(data.get("tech_stack", []))}
Competitor Context: {data.get("competitors_context", "")}

Requirements:
1. Subject line should be catchy and relevant.
2. The body should be concise (under 4 sentences).
3. Mention their specific title or company context.
4. If applicable, mention how their tech stack or competitors make your product a perfect fit.
5. End with a soft call to action.

Return ONLY JSON in this exact format:
{{"subject": "The subject line", "body": "The email body text"}}
"""
            try:
                llm_response = await self.toolbox.generate_text(
                    prompt=prompt,
                    require_json=True,
                    strategy="fast"
                )
                
                # Clean response
                clean_response = llm_response.strip()
                if clean_response.startswith('```json'):
                    clean_response = clean_response[7:]
                elif clean_response.startswith('```'):
                    clean_response = clean_response[3:]
                if clean_response.endswith('```'):
                    clean_response = clean_response[:-3]
                    
                parsed = json.loads(clean_response)
                
                outreach_drafts.append({
                    "contact_name": contact_name,
                    "contact_title": contact_title,
                    "subject": parsed.get("subject", ""),
                    "body": parsed.get("body", "")
                })
            except Exception as e:
                logger.error(f"Failed to generate outreach for {contact_name}", error=str(e))
                outreach_drafts.append({
                    "contact_name": contact_name,
                    "contact_title": contact_title,
                    "subject": f"Quick question regarding {company_name}",
                    "body": "Hi there, I noticed your role and would love to connect to discuss how we can help your team."
                })
                
        return {
            "executed_agents": ["outreach_generator_node"],
            "data": {"outreach_drafts": outreach_drafts},
            "recent_thoughts": recent_thoughts
        }
