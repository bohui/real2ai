"""
Fix for client authentication issue.

The problem is that the OpenAI client tries to connect to OpenRouter without proper API keys,
causing authentication failures. This leads to the "No valid response from available clients" error.
"""

import asyncio
import logging
from app.clients.openai.config import OpenAISettings, OpenAIClientConfig

async def main():
    settings = OpenAISettings()
    config = settings.to_client_config()
    
    print(f"API Key configured: {'Yes' if config.api_key else 'No'}")
    print(f"API Base: {config.api_base}")
    print(f"Model: {config.model_name}")
    print(f"Extra config: {config.extra_config}")
    
    if not config.api_key:
        print("\n❌ ISSUE FOUND: No API key configured!")
        print("The OpenAI client is trying to use OpenRouter but has no authentication.")
        print("\nSOLUTION: Set one of these environment variables:")
        print("  - OPENROUTER_API_KEY=your_openrouter_key")
        print("  - OPENAI_API_KEY=your_openai_key (if using OpenAI directly)")
        print("\nAlternatively, disable OpenAI client in fallback mode until keys are configured.")
    else:
        print("\n✅ API key is configured")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
