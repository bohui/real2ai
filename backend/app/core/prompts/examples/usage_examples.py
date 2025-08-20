"""Examples demonstrating the enhanced prompt management system"""

import asyncio
from pathlib import Path
from app.core.prompts.manager import PromptManager, PromptManagerConfig
from app.core.prompts.context import PromptContext, ContextType
from app.models.contract_state import AustralianState, ContractType


async def basic_composition_example():
    """Example of basic prompt composition"""

    # Configure the prompt manager
    prompts_dir = Path(__file__).parent.parent.parent.parent / "prompts"
    config = PromptManagerConfig(
        templates_dir=prompts_dir,
        config_dir=prompts_dir / "config",
        enable_composition=True,
    )

    manager = PromptManager(config)

    # Create context for contract analysis
    context = PromptContext(
        context_type=ContextType.USER,
        variables={
            "contract_text": "Sample contract text here...",
            "australian_state": "NSW",
            "analysis_type": "comprehensive",
            "user_experience_level": "novice",
            "transaction_value": 850000,
        },
    )

    # Compose and render a complete prompt
    try:
        composed_prompt = await manager.render_composed(
            composition_name="contract_analysis_complete",
            context=context,
            return_parts=True,
        )

        print("=== SYSTEM PROMPT ===")
        print(composed_prompt["system"])
        print("\n=== USER PROMPT ===")
        print(composed_prompt["user"])
        print(f"\n=== METADATA ===")
        print(composed_prompt["metadata"])

    except Exception as e:
        print(f"Composition failed: {e}")


async def state_specific_example():
    """Example of state-specific prompt composition"""

    config = PromptManagerConfig(
        templates_dir=Path(__file__).parent.parent.parent.parent / "prompts",
        config_dir=Path(__file__).parent.parent.parent.parent / "prompts" / "config",
        enable_composition=True,
    )

    manager = PromptManager(config)

    # Test different states
    states = ["NSW", "VIC", "QLD"]

    for state in states:
        context = PromptContext(
            context_type=ContextType.USER,
            variables={
                "contract_text": f"Sample {state} contract...",
                "australian_state": state,
                "analysis_type": "comprehensive",
                "contract_type": "PURCHASE_AGREEMENT",
            },
        )

        try:
            result = await manager.render_composed(
                composition_name="state_specific_analysis", context=context
            )

            print(f"\n=== {state} SPECIFIC ANALYSIS ===")
            print(result[:500] + "..." if len(result) > 500 else result)

        except Exception as e:
            print(f"Failed for {state}: {e}")


async def validation_example():
    """Example of prompt validation"""

    config = PromptManagerConfig(
        templates_dir=Path(__file__).parent.parent.parent.parent / "prompts",
        config_dir=Path(__file__).parent.parent.parent.parent / "prompts" / "config",
        enable_composition=True,
        validation_enabled=True,
    )

    manager = PromptManager(config)

    # List available compositions
    print("=== AVAILABLE COMPOSITIONS ===")
    compositions = manager.list_compositions()
    for comp in compositions:
        print(f"- {comp['name']}: {comp['description']}")

    # Validate compositions
    print("\n=== COMPOSITION VALIDATION ===")
    for comp in compositions:
        validation = manager.validate_composition(comp["name"])
        status = "✅ VALID" if validation["valid"] else "❌ INVALID"
        print(f"{comp['name']}: {status}")

        if not validation["valid"]:
            print(f"  Issues: {validation.get('issues', [])}")


async def batch_rendering_example():
    """Example of batch prompt rendering"""

    config = PromptManagerConfig(
        templates_dir=Path(__file__).parent.parent.parent.parent / "prompts",
        config_dir=Path(__file__).parent.parent.parent.parent / "prompts" / "config",
        enable_composition=True,
    )

    manager = PromptManager(config)

    # Prepare multiple contexts
    contexts = [
        {
            "composition": "contract_analysis_complete",
            "context": PromptContext(
                context_type=ContextType.USER,
                variables={
                    "contract_text": "NSW Purchase Agreement...",
                    "australian_state": "NSW",
                    "analysis_type": "comprehensive",
                },
            ),
        },
        {
            "composition": "ocr_extraction_specialized",
            "context": PromptContext(
                context_type=ContextType.USER,
                variables={
                    "document_type": "contract",
                    "australian_state": "VIC",
                    "quality_requirements": "high",
                },
            ),
        },
        {
            "composition": "risk_assessment_comprehensive",
            "context": PromptContext(
                context_type=ContextType.USER,
                variables={
                    "contract_type": "PURCHASE_AGREEMENT",
                    "australian_state": "QLD",
                    "user_experience": "experienced",
                },
            ),
        },
    ]

    # Process all contexts
    results = []
    for item in contexts:
        try:
            result = await manager.render_composed(
                composition_name=item["composition"], context=item["context"]
            )
            results.append(
                {
                    "composition": item["composition"],
                    "success": True,
                    "length": len(result),
                    "preview": result[:200] + "...",
                }
            )
        except Exception as e:
            results.append(
                {"composition": item["composition"], "success": False, "error": str(e)}
            )

    print("=== BATCH RENDERING RESULTS ===")
    for result in results:
        status = "✅" if result["success"] else "❌"
        print(f"{status} {result['composition']}")

        if result["success"]:
            print(f"   Length: {result['length']} characters")
            print(f"   Preview: {result['preview']}")
        else:
            print(f"   Error: {result['error']}")
        print()


async def metrics_and_monitoring_example():
    """Example of metrics and monitoring"""

    config = PromptManagerConfig(
        templates_dir=Path(__file__).parent.parent.parent.parent / "prompts",
        config_dir=Path(__file__).parent.parent.parent.parent / "prompts" / "config",
        enable_composition=True,
        enable_metrics=True,
    )

    manager = PromptManager(config)

    # Perform some operations to generate metrics
    context = PromptContext(
        context_type=ContextType.USER,
        variables={
            "contract_text": "Sample contract",
            "australian_state": "NSW",
            "analysis_type": "quick",
        },
    )

    # Multiple renders to generate metrics
    for i in range(3):
        try:
            await manager.render_composed(
                composition_name="contract_analysis_complete",
                context=context,
                cache_key=f"test_render_{i}",
            )
        except Exception as e:
            print(f"Render {i} failed: {e}")

    # Get metrics
    metrics = manager.get_metrics()
    print("=== SYSTEM METRICS ===")
    print(f"Total renders: {metrics['prompt_manager']['renders']}")
    print(f"Cache hits: {metrics['prompt_manager']['cache_hits']}")
    print(f"Validation failures: {metrics['prompt_manager']['validation_failures']}")
    print(
        f"Average render time: {metrics['prompt_manager']['avg_render_time_seconds']:.3f}s"
    )

    # Health check
    health = await manager.health_check()
    print(f"\n=== HEALTH CHECK ===")
    print(f"Overall status: {health['status']}")
    for component, status in health["components"].items():
        print(f"  {component}: {status['status']}")


def legacy_compatibility_example():
    """Example showing backward compatibility with existing code"""

    # This shows how existing code continues to work
    config = PromptManagerConfig(
        templates_dir=Path(__file__).parent.parent.parent.parent / "prompts" / "user",
        enable_composition=False,  # Disable composition for legacy mode
    )

    manager = PromptManager(config)

    # Existing code using individual templates still works
    print("=== LEGACY COMPATIBILITY ===")
    templates = manager.list_templates()
    print(f"Available templates: {len(templates)}")

    for template in templates[:3]:  # Show first 3
        print(f"- {template['name']}: {template.get('description', 'No description')}")


async def main():
    """Run all examples"""
    print("🚀 Prompt Management System Examples\n")

    examples = [
        ("Basic Composition", basic_composition_example),
        ("State-Specific Analysis", state_specific_example),
        ("Validation", validation_example),
        ("Batch Rendering", batch_rendering_example),
        ("Metrics & Monitoring", metrics_and_monitoring_example),
        ("Legacy Compatibility", legacy_compatibility_example),
    ]

    for name, example_func in examples:
        print(f"{'='*50}")
        print(f"🔧 {name}")
        print(f"{'='*50}")

        try:
            if asyncio.iscoroutinefunction(example_func):
                await example_func()
            else:
                example_func()
        except Exception as e:
            print(f"❌ Example failed: {e}")

        print("\n")


if __name__ == "__main__":
    asyncio.run(main())
