#!/usr/bin/env python3
"""
Simple script to test LLM calls with prompts

Usage:
    python test_llm_call.py --client openai --prompt "Your prompt here"
    python test_llm_call.py --client gemini --prompt "Your prompt here"
    python test_llm_call.py --list-clients
"""

import asyncio
import argparse
import sys
from pathlib import Path

# Add the backend directory to the Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from app.clients.factory import get_openai_client, get_gemini_client
from app.core.config import get_settings


async def test_openai_call(prompt: str):
    """Test OpenAI API call"""
    try:
        print("🚀 Testing OpenAI API...")

        # Get OpenAI client
        client = await get_openai_client()

        # Make the call
        print(f"📤 Sending prompt: {prompt[:100]}{'...' if len(prompt) > 100 else ''}")

        response = await client.generate_content(prompt)

        print("✅ OpenAI Response:")
        print("=" * 50)
        print(response)
        print("=" * 50)

        return response

    except Exception as e:
        print(f"❌ OpenAI API error: {e}")
        return None


async def test_gemini_call(prompt: str):
    """Test Gemini API call"""
    try:
        print("🚀 Testing Gemini API...")

        # Get Gemini client
        client = await get_gemini_client()

        # Make the call
        print(f"📤 Sending prompt: {prompt[:100]}{'...' if len(prompt) > 100 else ''}")

        response = await client.generate_content(prompt)

        print("✅ Gemini Response:")
        print("=" * 50)
        print(response)
        print("=" * 50)

        return response

    except Exception as e:
        print(f"❌ Gemini API error: {e}")
        return None


async def test_with_prompt_template(template_name: str, client_type: str):
    """Test with an actual prompt template from your system"""
    try:
        print(f"🔍 Testing with prompt template: {template_name}")

        # Import prompt manager
        from app.core.prompts.manager import PromptManager, PromptManagerConfig
        from app.core.prompts.context import PromptContext, ContextType

        # Create prompt manager
        prompts_dir = Path(__file__).parent / "app" / "prompts"
        config = PromptManagerConfig(
            templates_dir=prompts_dir, cache_enabled=False, validation_enabled=False
        )

        manager = PromptManager(config)
        await manager.initialize()

        # Create test context
        context = PromptContext(
            context_type=ContextType.USER,
            variables={
                "extracted_text": "This is a sample NSW property purchase agreement for $850,000. The property is located at 123 Main Street, Sydney NSW 2000. Purchase price is $850,000 with a 10% deposit required. Settlement is set for 60 days from contract date. The vendor is John Smith and purchaser is Jane Doe. Special conditions include building inspection and finance approval.",
                "australian_state": "NSW",
                "contract_type": "purchase_agreement",
                "user_type": "buyer",
                "user_experience_level": "novice",
                "analysis_type": "comprehensive",
            },
        )

        # Render the prompt
        rendered_prompt = await manager.render(template_name, context)
        print(f"📝 Rendered prompt length: {len(rendered_prompt)} characters")
        print(f"📝 First 200 chars: {rendered_prompt[:200]}...")

        # Test with the rendered prompt
        if client_type == "openai":
            return await test_openai_call(rendered_prompt)
        elif client_type == "gemini":
            return await test_gemini_call(rendered_prompt)
        else:
            print(f"❌ Unknown client type: {client_type}")
            return None

    except Exception as e:
        print(f"❌ Error testing with prompt template: {e}")
        return None


def list_available_templates():
    """List available prompt templates"""
    try:
        templates_dir = Path(__file__).parent / "app" / "prompts" / "user"

        print("📁 Available Prompt Templates:")
        print("=" * 50)

        for template_file in templates_dir.rglob("*.md"):
            relative_path = template_file.relative_to(templates_dir)
            print(f"  📄 {relative_path}")

            # Try to read frontmatter for description
            try:
                content = template_file.read_text()
                if content.startswith("---"):
                    end_pos = content.find("---", 3)
                    if end_pos > 0:
                        frontmatter = content[3:end_pos].strip()
                        import yaml

                        parsed = yaml.safe_load(frontmatter)
                        if parsed and "description" in parsed:
                            print(f"     💬 {parsed['description']}")
            except:
                pass

        print("=" * 50)

    except Exception as e:
        print(f"❌ Error listing templates: {e}")


async def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Test LLM calls with prompts")
    parser.add_argument(
        "--client", choices=["openai", "gemini"], help="LLM client to use"
    )
    parser.add_argument("--prompt", help="Custom prompt to send")
    parser.add_argument("--template", help="Use a specific prompt template")
    parser.add_argument(
        "--list-templates", action="store_true", help="List available templates"
    )

    args = parser.parse_args()

    if args.list_templates:
        list_available_templates()
        return

    if not args.client:
        print("❌ Please specify a client with --client")
        parser.print_help()
        return

    if args.template:
        # Test with prompt template
        await test_with_prompt_template(args.template, args.client)
    elif args.prompt:
        # Test with custom prompt
        if args.client == "openai":
            await test_openai_call(args.prompt)
        elif args.client == "gemini":
            await test_gemini_call(args.prompt)
    else:
        # Default test prompt
        default_prompt = "Hello! Please provide a brief analysis of Australian real estate contracts in 2-3 sentences."

        if args.client == "openai":
            await test_openai_call(default_prompt)
        elif args.client == "gemini":
            await test_gemini_call(default_prompt)


if __name__ == "__main__":
    asyncio.run(main())
