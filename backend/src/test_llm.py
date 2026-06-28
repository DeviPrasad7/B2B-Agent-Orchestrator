import asyncio
import os
from services.llm_service import LLMService

async def test_llm():
    service = LLMService()
    print("Testing generate_text with JSON required...")
    try:
        res = await service.generate_text("Tell me about ChatGPT", fallback="{}", require_json=True)
        print("Response:", res)
    except Exception as e:
        print("Error:", str(e))

if __name__ == "__main__":
    asyncio.run(test_llm())
