"""
OpenAI client integration CLI for testing prompts directly.

This script provides a simple interface to test prompts against the OpenAI client
with all connections handled internally.

Examples:
  - Basic text generation:
      python backend/examples/integrations/openai_client_cli.py generate \
        --prompt "Write a haiku about coding" \
        --temperature 0.7 --max-tokens 256

  - Using a specific model:
      python backend/examples/integrations/openai_client_cli.py generate \
        --prompt "Explain quantum computing" \
        --model "claude-3-5-sonnet" --max-tokens 500

  - With system prompt:
      python backend/examples/integrations/openai_client_cli.py generate \
        --prompt "What is machine learning?" \
        --system-prompt "You are a helpful AI assistant. Be concise."

  - Health check:
      python backend/examples/integrations/openai_client_cli.py health

Environment setup:
  - Set OPENAI_API_KEY or OPENROUTER_API_KEY in your environment
  - Optional: Set OPENAI_API_BASE for custom endpoints
  - For OpenRouter: exports will be auto-detected

Note: Run from repo root so Python finds `backend/app` on PYTHONPATH:
  PYTHONPATH=backend python backend/examples/integrations/openai_client_cli.py generate --prompt "Hello"
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
from typing import Any, Dict, Optional, List

# Load environment variables automatically
try:
    from dotenv import load_dotenv

    # Find and load .env files from repo root
    REPO_ROOT = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    )

    # Load .env files in order of precedence (.env.local overrides .env)
    env_files = [
        os.path.join(REPO_ROOT, ".env"),
        os.path.join(REPO_ROOT, ".env.local"),
    ]

    for env_file in env_files:
        if os.path.exists(env_file):
            load_dotenv(env_file, override=True)
            print(f"✅ Loaded environment from: {env_file}")

except ImportError:
    print(
        "⚠️  Warning: python-dotenv not installed. Install with: pip install python-dotenv"
    )
    print("Environment variables will be loaded from system environment only.")

# Ensure `app` package is importable when running from repo root
REPO_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
BACKEND_DIR = os.path.join(REPO_ROOT, "backend")
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app.clients import get_openai_client  # noqa: E402
from app.clients.base.exceptions import (  # noqa: E402
    ClientError,
    ClientAuthenticationError,
    ClientRateLimitError,
    ClientQuotaExceededError,
)
from app.core.prompts.manager import get_prompt_manager  # noqa: E402
from app.core.prompts.context import PromptContext  # noqa: E402
from app.models.contract_state import AustralianState  # noqa: E402


def configure_logging(verbose: bool) -> None:
    """Configure logging based on verbosity level."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )


async def run_generate(args: argparse.Namespace) -> Dict[str, Any]:
    """Run text generation with OpenAI client."""
    client = await get_openai_client()

    # Build kwargs for generate_content using the client's interface
    kwargs = {}

    # Model parameters
    if args.model:
        kwargs["model"] = args.model
    if args.temperature is not None:
        kwargs["temperature"] = args.temperature
    if args.top_p is not None:
        kwargs["top_p"] = args.top_p
    if args.max_tokens is not None:
        kwargs["max_tokens"] = args.max_tokens
    if args.frequency_penalty is not None:
        kwargs["frequency_penalty"] = args.frequency_penalty
    if args.presence_penalty is not None:
        kwargs["presence_penalty"] = args.presence_penalty

    # System prompt
    if args.system_prompt:
        kwargs["system_prompt"] = args.system_prompt

    # Generate content using the existing client interface
    result_text = await client.generate_content(prompt=args.prompt, **kwargs)

    # Get client configuration for response metadata
    config_info = client.get_client_info() if hasattr(client, "get_client_info") else {}

    return {
        "mode": "generate",
        "model": args.model or config_info.get("model_name", "default"),
        "prompt": args.prompt,
        "system_prompt": args.system_prompt,
        "parameters": {
            "temperature": args.temperature,
            "top_p": args.top_p,
            "max_tokens": args.max_tokens,
            "frequency_penalty": args.frequency_penalty,
            "presence_penalty": args.presence_penalty,
        },
        "client_info": config_info,
        "output": result_text,
    }


async def run_chat(args: argparse.Namespace) -> Dict[str, Any]:
    """Run interactive chat session with OpenAI client."""
    client = await get_openai_client()

    print("\n🤖 OpenAI Chat Session Started")
    print("Type 'exit' or 'quit' to end the session")
    print("-" * 50)

    messages = []
    if args.system_prompt:
        messages.append({"role": "system", "content": args.system_prompt})
        print(f"System: {args.system_prompt}\n")

    while True:
        try:
            # Get user input
            user_input = input("\nYou: ").strip()

            if user_input.lower() in ["exit", "quit"]:
                print("\n👋 Chat session ended")
                break

            if not user_input:
                continue

            # Add user message to history
            messages.append({"role": "user", "content": user_input})

            # Generate response using the existing client's messages interface
            kwargs = {
                "messages": messages,
            }

            # Add optional parameters
            if args.temperature is not None:
                kwargs["temperature"] = args.temperature
            if args.max_tokens is not None:
                kwargs["max_tokens"] = args.max_tokens
            if args.model:
                kwargs["model"] = args.model

            # Use the existing client interface which supports messages
            response = await client.generate_content(
                prompt="", **kwargs  # Not used when messages is provided
            )

            # Add assistant response to history
            messages.append({"role": "assistant", "content": response})

            # Display response
            print(f"\nAssistant: {response}")

        except KeyboardInterrupt:
            print("\n\n👋 Chat session interrupted")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")
            print("Continuing chat session...")

    # Get client info for metadata
    config_info = client.get_client_info() if hasattr(client, "get_client_info") else {}

    return {
        "mode": "chat",
        "model": args.model or config_info.get("model_name", "default"),
        "message_count": len(messages),
        "client_info": config_info,
        "messages": (
            messages[-10:] if len(messages) > 10 else messages
        ),  # Last 10 messages
    }


async def run_health(args: argparse.Namespace) -> Dict[str, Any]:
    """Check health status of OpenAI client."""
    client = await get_openai_client()
    result = await client.health_check()
    return {"mode": "health", **result}


async def run_quality_validation_test(args: argparse.Namespace) -> Dict[str, Any]:
    """Test connection and quality validation prompt from prompt manager."""
    # Test OpenAI client connection
    client = await get_openai_client()
    
    # Test client health
    health_result = await client.health_check()
    if not health_result.get("is_healthy", False):
        raise Exception(f"Client health check failed: {health_result}")
    
    # Get prompt manager and render quality validation prompt
    prompt_manager = get_prompt_manager()
    
    # Create sample context for quality validation
    context = PromptContext(
        document_type="property_contract",
        australian_state=AustralianState.NSW,
        extraction_method="ocr",
        document_text="This is a sample property contract for testing quality validation. " * 20,
        document_metadata={
            "file_size": 512000,
            "page_count": 2,
            "extraction_confidence": 0.85,
            "processing_time_ms": 1500,
            "source_format": "PDF"
        },
        analysis_timestamp="2025-01-15T10:30:00Z"
    )
    
    # Render the quality validation prompt
    rendered_prompt = await prompt_manager.render(
        template_name="validation/document_quality_validation",
        context=context,
        service_name="openai_client_test"
    )
    
    # Calculate prompt stats
    char_count = len(rendered_prompt)
    estimated_tokens = char_count // 4
    
    # Test with OpenAI client
    kwargs = {}
    if args.model:
        kwargs["model"] = args.model
    if args.temperature is not None:
        kwargs["temperature"] = args.temperature
    if args.max_tokens is not None:
        kwargs["max_tokens"] = args.max_tokens
    
    try:
        # Generate response using the quality validation prompt
        response = await client.generate_content(prompt=rendered_prompt, **kwargs)
        
        # Try to parse response as JSON
        response_json = None
        try:
            response_json = json.loads(response)
        except json.JSONDecodeError:
            pass
        
        return {
            "mode": "quality_validation_test",
            "client_health": health_result,
            "prompt_stats": {
                "char_count": char_count,
                "estimated_tokens": estimated_tokens,
                "template_name": "validation/document_quality_validation"
            },
            "test_context": {
                "document_type": context.document_type,
                "australian_state": str(context.australian_state),
                "extraction_method": context.extraction_method
            },
            "response_stats": {
                "response_length": len(response),
                "valid_json": response_json is not None,
                "has_quality_scores": response_json and "overall_quality_score" in response_json if response_json else False
            },
            "raw_response": response if len(response) < 1000 else response[:1000] + "...",
            "parsed_response": response_json if response_json else None
        }
        
    except Exception as e:
        return {
            "mode": "quality_validation_test",
            "client_health": health_result,
            "prompt_stats": {
                "char_count": char_count,
                "estimated_tokens": estimated_tokens,
                "template_name": "validation/document_quality_validation"
            },
            "error": str(e),
            "error_type": type(e).__name__
        }


async def run_batch(args: argparse.Namespace) -> Dict[str, Any]:
    """Run batch processing of multiple prompts."""
    client = await get_openai_client()

    # Read prompts from file or use provided list
    prompts = []
    if args.prompts_file:
        with open(args.prompts_file, "r") as f:
            prompts = [line.strip() for line in f if line.strip()]
    else:
        prompts = args.prompts

    if not prompts:
        raise ValueError("No prompts provided")

    results = []
    for i, prompt in enumerate(prompts, 1):
        print(f"Processing prompt {i}/{len(prompts)}...")

        # Build kwargs using existing client interface
        kwargs = {}

        if args.temperature is not None:
            kwargs["temperature"] = args.temperature
        if args.max_tokens is not None:
            kwargs["max_tokens"] = args.max_tokens
        if args.model:
            kwargs["model"] = args.model
        if args.system_prompt:
            kwargs["system_prompt"] = args.system_prompt

        try:
            response = await client.generate_content(prompt=prompt, **kwargs)
            results.append(
                {"prompt": prompt, "response": response, "status": "success"}
            )
        except Exception as e:
            results.append({"prompt": prompt, "error": str(e), "status": "failed"})

    # Get client info for metadata
    config_info = client.get_client_info() if hasattr(client, "get_client_info") else {}

    return {
        "mode": "batch",
        "model": args.model or config_info.get("model_name", "default"),
        "total_prompts": len(prompts),
        "successful": sum(1 for r in results if r["status"] == "success"),
        "failed": sum(1 for r in results if r["status"] == "failed"),
        "client_info": config_info,
        "results": results,
    }


def add_common_gen_args(p: argparse.ArgumentParser) -> None:
    """Add common generation arguments to parser."""
    p.add_argument("--prompt", default="Hello, how are you?", help="User prompt text")
    p.add_argument(
        "--system-prompt", dest="system_prompt", default=None, help="System instruction"
    )
    p.add_argument(
        "--temperature", type=float, default=0.7, help="Sampling temperature (0.0-2.0)"
    )
    p.add_argument(
        "--top-p", dest="top_p", type=float, default=1.0, help="Nucleus sampling"
    )
    p.add_argument(
        "--max-tokens",
        dest="max_tokens",
        type=int,
        default=256,
        help="Max output tokens",
    )
    p.add_argument(
        "--model",
        default=None,
        help="Model name (e.g., 'deepseek-chat', 'claude-3-5-sonnet')",
    )
    p.add_argument(
        "--frequency-penalty",
        dest="frequency_penalty",
        type=float,
        default=None,
        help="Frequency penalty (-2.0 to 2.0)",
    )
    p.add_argument(
        "--presence-penalty",
        dest="presence_penalty",
        type=float,
        default=None,
        help="Presence penalty (-2.0 to 2.0)",
    )


def build_parser() -> argparse.ArgumentParser:
    """Build argument parser for CLI."""
    parser = argparse.ArgumentParser(
        description="OpenAI Client Integration CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    subparsers = parser.add_subparsers(dest="mode", help="Operation mode")

    # Generate mode
    gen_parser = subparsers.add_parser("generate", help="Generate text from a prompt")
    add_common_gen_args(gen_parser)
    gen_parser.add_argument(
        "--json", dest="as_json", action="store_true", help="Output JSON only"
    )
    gen_parser.add_argument(
        "--verbose", action="store_true", help="Enable debug logging"
    )

    # Chat mode
    chat_parser = subparsers.add_parser("chat", help="Interactive chat session")
    chat_parser.add_argument(
        "--system-prompt",
        dest="system_prompt",
        default=None,
        help="System instruction for chat",
    )
    chat_parser.add_argument(
        "--temperature", type=float, default=0.7, help="Sampling temperature"
    )
    chat_parser.add_argument(
        "--max-tokens",
        dest="max_tokens",
        type=int,
        default=256,
        help="Max tokens per response",
    )
    chat_parser.add_argument("--model", default=None, help="Model name")
    chat_parser.add_argument(
        "--verbose", action="store_true", help="Enable debug logging"
    )

    # Batch mode
    batch_parser = subparsers.add_parser("batch", help="Process multiple prompts")
    batch_parser.add_argument("--prompts", nargs="+", help="List of prompts to process")
    batch_parser.add_argument(
        "--prompts-file",
        dest="prompts_file",
        help="File containing prompts (one per line)",
    )
    batch_parser.add_argument(
        "--system-prompt", dest="system_prompt", default=None, help="System instruction"
    )
    batch_parser.add_argument(
        "--temperature", type=float, default=0.7, help="Sampling temperature"
    )
    batch_parser.add_argument(
        "--max-tokens", dest="max_tokens", type=int, default=256, help="Max tokens"
    )
    batch_parser.add_argument("--model", default=None, help="Model name")
    batch_parser.add_argument(
        "--json", dest="as_json", action="store_true", help="Output JSON only"
    )
    batch_parser.add_argument(
        "--verbose", action="store_true", help="Enable debug logging"
    )

    # Health check mode
    health_parser = subparsers.add_parser("health", help="Check client health")
    health_parser.add_argument(
        "--json", dest="as_json", action="store_true", help="Output JSON only"
    )
    health_parser.add_argument(
        "--verbose", action="store_true", help="Enable debug logging"
    )

    # Quality validation test mode
    quality_parser = subparsers.add_parser("quality-test", help="Test connection and quality validation prompt")
    quality_parser.add_argument(
        "--model", default=None, help="Model name to use for testing"
    )
    quality_parser.add_argument(
        "--temperature", type=float, default=0.1, help="Temperature for generation"
    )
    quality_parser.add_argument(
        "--max-tokens", dest="max_tokens", type=int, default=2048, help="Max tokens for response"
    )
    quality_parser.add_argument(
        "--json", dest="as_json", action="store_true", help="Output JSON only"
    )
    quality_parser.add_argument(
        "--verbose", action="store_true", help="Enable debug logging"
    )

    return parser


async def main_async(argv: list[str]) -> int:
    """Main async entry point."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.mode:
        parser.print_help()
        return 1

    configure_logging(args.verbose)

    # Show environment configuration
    api_key = os.getenv("OPENAI_API_KEY") or os.getenv("OPENROUTER_API_KEY")
    api_base = os.getenv("OPENAI_API_BASE")
    model_name = os.getenv("OPENAI_MODEL_NAME")

    if args.verbose or args.mode == "health":
        print("\n🔧 Environment Configuration:")
        print(f"  API Key: {'✅ Set' if api_key else '❌ Not set'}")
        print(f"  API Base: {api_base or 'Default (OpenAI)'}")
        print(f"  Default Model: {model_name or 'Default'}")
        print()

    # Check for API key
    if not api_key:
        logging.getLogger(__name__).error(
            "❌ No API key found. Please set OPENAI_API_KEY or OPENROUTER_API_KEY in your .env file."
        )
        return 1

    try:
        if args.mode == "generate":
            result = await run_generate(args)
        elif args.mode == "chat":
            result = await run_chat(args)
        elif args.mode == "batch":
            result = await run_batch(args)
        elif args.mode == "health":
            result = await run_health(args)
        elif args.mode == "quality-test":
            result = await run_quality_validation_test(args)
        else:
            parser.error(f"Unsupported mode: {args.mode}")
            return 2

        # Output results
        if hasattr(args, "as_json") and args.as_json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            if args.mode == "generate":
                print("\n" + "=" * 50)
                print("RESPONSE:")
                print("=" * 50)
                print(result["output"])
            elif args.mode == "health":
                print("\n" + "=" * 50)
                print("HEALTH CHECK RESULT:")
                print("=" * 50)
                print(json.dumps(result, indent=2))
            elif args.mode == "quality-test":
                print("\n" + "=" * 50)
                print("QUALITY VALIDATION TEST RESULT:")
                print("=" * 50)
                print(f"✅ Client Health: {result['client_health']['is_healthy']}")
                print(f"📏 Prompt Size: {result['prompt_stats']['char_count']} chars ({result['prompt_stats']['estimated_tokens']} tokens)")
                print(f"📝 Template: {result['prompt_stats']['template_name']}")
                if 'error' in result:
                    print(f"❌ Error: {result['error']}")
                else:
                    print(f"📤 Response Length: {result['response_stats']['response_length']} chars")
                    print(f"🔍 Valid JSON: {result['response_stats']['valid_json']}")
                    print(f"📊 Has Quality Scores: {result['response_stats']['has_quality_scores']}")
                    if result['response_stats']['valid_json']:
                        print("\n--- Parsed Response Sample ---")
                        parsed = result['parsed_response']
                        if parsed and 'overall_quality_score' in parsed:
                            print(f"Overall Quality Score: {parsed['overall_quality_score']}")
                        if parsed and 'suitability_assessment' in parsed:
                            print(f"Automated Analysis Suitable: {parsed['suitability_assessment'].get('automated_analysis_suitable')}")
            elif args.mode == "batch":
                print("\n" + "=" * 50)
                print(f"BATCH PROCESSING COMPLETE:")
                print(f"  Total: {result['total_prompts']}")
                print(f"  Success: {result['successful']}")
                print(f"  Failed: {result['failed']}")
                print("=" * 50)
                if not args.as_json:
                    for i, r in enumerate(result["results"], 1):
                        print(f"\n--- Prompt {i} ---")
                        print(f"Input: {r['prompt'][:100]}...")
                        if r["status"] == "success":
                            print(f"Output: {r['response'][:200]}...")
                        else:
                            print(f"Error: {r['error']}")
            else:
                print(json.dumps(result, ensure_ascii=False, indent=2))

        return 0

    except KeyboardInterrupt:
        print("\nInterrupted")
        return 130
    except ClientAuthenticationError as e:
        logging.getLogger(__name__).error(f"Authentication error: {e}")
        return 1
    except ClientRateLimitError as e:
        logging.getLogger(__name__).error(f"Rate limit exceeded: {e}")
        return 1
    except ClientQuotaExceededError as e:
        logging.getLogger(__name__).error(f"Quota exceeded: {e}")
        return 1
    except ClientError as e:
        logging.getLogger(__name__).error(f"Client error: {e}")
        return 1
    except Exception as e:
        logging.getLogger(__name__).exception("Unexpected error")
        print(f"Unexpected error: {e}")
        return 1


def main() -> None:
    """Main entry point."""
    exit_code = asyncio.run(main_async(sys.argv[1:]))


if __name__ == "__main__":
    main()
