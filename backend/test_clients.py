import asyncio
import logging
from app.clients import get_openai_client, get_gemini_client

logging.basicConfig(level=logging.INFO)

async def test_clients():
    print("Testing client connections...")
    try:
        openai = await get_openai_client()
        print(f"OpenAI client: {openai is not None}")
        if openai:
            print(f"OpenAI client type: {type(openai)}")
    except Exception as e:
        print(f"OpenAI client error: {e}")
    
    try:
        gemini = await get_gemini_client()
        print(f"Gemini client: {gemini is not None}")
        if gemini:
            print(f"Gemini client type: {type(gemini)}")
    except Exception as e:
        print(f"Gemini client error: {e}")

if __name__ == "__main__":
    asyncio.run(test_clients())
