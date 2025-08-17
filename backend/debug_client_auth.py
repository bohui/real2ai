"""
Debug actual API key being used for OpenAI client.
"""

import asyncio
import logging
from app.clients.openai.config import OpenAISettings

async def main():
    settings = OpenAISettings()
    
    print("Environment variables check:")
    print(f"openai_api_key: {'*' * len(settings.openai_api_key) if settings.openai_api_key else 'None'}")
    print(f"openrouter_api_key: {'*' * len(settings.openrouter_api_key) if settings.openrouter_api_key else 'None'}")
    
    config = settings.to_client_config()
    
    print(f"\nEffective API key: {'*' * len(config.api_key) if config.api_key else 'None'}")
    print(f"API key length: {len(config.api_key) if config.api_key else 0}")
    print(f"API key starts with: {config.api_key[:10] if config.api_key else 'None'}...")
    
    # Check if it's a valid-looking key
    if config.api_key:
        if config.api_key.startswith('sk-'):
            print("✅ Looks like OpenAI key format")
        elif config.api_key.startswith('sk-or-'):
            print("✅ Looks like OpenRouter key format")
        else:
            print("⚠️  Unknown key format")
    else:
        print("❌ No API key found")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
