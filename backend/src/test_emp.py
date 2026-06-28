import asyncio
import os
from services.llm_service import LLMService
from tavily import AsyncTavilyClient
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("TAVILY_API_KEY")

async def test_enrich():
    client = AsyncTavilyClient(api_key=api_key)
    search_content = ""
    try:
        response = await client.search("Key executives leadership ChatGPT CEO CTO VP linkedin", max_results=3)
        search_content = "\n".join([r.get("content", "") for r in response.get("results", [])])
    except:
        pass
        
    prompt = f"""
    Extract up to 3 key executives (CEO, CTO, VP, etc.) for ChatGPT. 
    Here is some search context that might help: {search_content}.
    If the text doesn't contain real executives, rely on your general knowledge to provide accurate real-world executives for this company.
    Return ONLY a JSON list of objects with 'name', 'title', and 'linkedin_url' (estimate URL if unknown).
    """
    
    service = LLMService()
    print("Testing find_company_employees prompt...")
    try:
        res = await service.generate_text(prompt, fallback="[]", require_json=True)
        print("Response:", res)
    except Exception as e:
        print("Error:", str(e))

if __name__ == "__main__":
    asyncio.run(test_enrich())
