import asyncio
import os
import sys

# Ensure we can import from src
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

from services.api_providers.news_api import NewsAPIProvider
from services.api_providers.github_api import GitHubAPIProvider
from services.api_providers.apify_api import ApifyLinkedInProvider
from core.settings import settings

async def main():
    print("Testing News API...")
    news_provider = NewsAPIProvider()
    news_config = {"keywords": "AI startup"}
    try:
        news_entries = await news_provider.fetch_entries(news_config)
        print(f"News API returned {len(news_entries)} entries.")
        if news_entries:
            print(f"Sample: {news_entries[0]['title']}")
    except Exception as e:
        print(f"News API Error: {e}")

    print("\nTesting GitHub API...")
    github_provider = GitHubAPIProvider()
    github_config = {"keywords": "ai-agent stars:>500"}
    try:
        github_entries = await github_provider.fetch_entries(github_config)
        print(f"GitHub API returned {len(github_entries)} entries.")
        if github_entries:
            print(f"Sample: {github_entries[0]['title']}")
    except Exception as e:
        print(f"GitHub API Error: {e}")

    print("\nTesting Apify LinkedIn API...")
    apify_provider = ApifyLinkedInProvider()
    apify_config = {
        "searchQuery": "Software Engineer",
        "currentJobTitleFilter": ["Senior Developer"],
        "locationsFilter": ["United States"],
        "maxPagesPerQuery": 1 # Minimum to test
    }
    try:
        apify_entries = await apify_provider.fetch_entries(apify_config)
        print(f"Apify API returned {len(apify_entries)} entries.")
        if apify_entries:
            print(f"Sample: {apify_entries[0]['title']}")
        else:
            # Let's hit it directly to see what's wrong
            import httpx
            async with httpx.AsyncClient() as client:
                res = await client.post("https://api.apify.com/v2/acts/harvestapi~linkedin-profile-search/run-sync-get-dataset-items?token=" + settings.APIFY_API_TOKEN + "&waitForFinish=60", json=apify_config, timeout=65)
                print("RAW Apify Response:", res.status_code, res.text[:500])
    except Exception as e:
        print(f"Apify API Error: {e}")

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
    
    # Reload settings after loading dotenv
    import importlib
    from core import settings as core_settings
    importlib.reload(core_settings)
    
    asyncio.run(main())
