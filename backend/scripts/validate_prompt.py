#!/usr/bin/env python3
"""
CLI script for validating prompt templates

Usage:
    python scripts/validate_prompt.py validate <template_path>
    python scripts/validate_prompt.py validate-all <templates_dir>
    python scripts/validate_prompt.py info <template_path>
"""

import sys
import argparse
from pathlib import Path

# Add the backend directory to the Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.core.prompts.validator import PromptValidator
from app.core.prompts.template import PromptTemplate, TemplateMetadata
from app.core.prompts.loader import PromptLoader
from app.core.config import get_settings


class PromptValidatorCLI:
    """CLI interface for prompt validation"""

    def __init__(self):
        self.settings = get_settings()
        self.validator = PromptValidator(config=self.settings)
        # Initialize loader with a default templates directory
        default_templates_dir = (
            Path(__file__).parent.parent / "app" / "prompts" / "user"
        )
        self.loader = PromptLoader(templates_dir=default_templates_dir)

    def validate_template(self, template_path: Path) -> bool:
        """Validate a single template file"""
        try:
            print(f"🔍 Validating template: {template_path}")

            if not template_path.exists():
                print(f"❌ Template file not found: {template_path}")
                return False

            # Load and parse the template
            template_content = template_path.read_text(encoding="utf-8")

            # Extract metadata from frontmatter
            metadata = self._extract_metadata(template_content)

            # Create template object
            template = PromptTemplate(
                template_content=template_content, metadata=metadata
            )

            # Validate the template
            result = self.validator.validate_template(template)

            # Display results
            self._display_validation_result(result, template_path.name)

            return result.is_valid

        except Exception as e:
            print(f"❌ Error validating template {template_path}: {e}")
            return False

    def validate_all_templates(self, templates_dir: Path) -> dict:
        """Validate all templates in a directory"""
        results = {"valid": [], "invalid": [], "errors": []}

        print(f"🔍 Validating all templates in: {templates_dir}")

        if not templates_dir.exists():
            print(f"❌ Templates directory not found: {templates_dir}")
            return results

        # Find all markdown files
        template_files = list(templates_dir.rglob("*.md"))

        if not template_files:
            print(f"⚠️  No markdown files found in {templates_dir}")
            return results

        print(f"📁 Found {len(template_files)} template files")

        for template_file in template_files:
            try:
                is_valid = self.validate_template(template_file)
                if is_valid:
                    results["valid"].append(str(template_file))
                else:
                    results["invalid"].append(str(template_file))
            except Exception as e:
                results["errors"].append((str(template_file), str(e)))

        # Display summary
        self._display_summary(results)

        return results

    def show_template_info(self, template_path: Path):
        """Display information about a template"""
        try:
            if not template_path.exists():
                print(f"❌ Template file not found: {template_path}")
                return

            template_content = template_path.read_text(encoding="utf-8")
            metadata = self._extract_metadata(template_content)

            print(f"📋 Template Information: {template_path.name}")
            print("=" * 50)
            print(f"Name: {metadata.name}")
            print(f"Version: {metadata.version}")
            print(f"Description: {metadata.description}")
            print(
                f"Required Variables: {', '.join(metadata.required_variables) or 'None'}"
            )
            print(
                f"Optional Variables: {', '.join(metadata.optional_variables) or 'None'}"
            )
            print(f"Tags: {', '.join(metadata.tags) or 'None'}")

            # Basic content analysis
            content_length = len(template_content)
            print(f"Content Length: {content_length} characters")

            # Check for common patterns
            has_variables = "{{" in template_content and "}}" in template_content
            has_conditionals = "{%" in template_content and "%}" in template_content
            has_includes = "{% include" in template_content

            print(f"Has Variables: {'Yes' if has_variables else 'No'}")
            print(f"Has Conditionals: {'Yes' if has_conditionals else 'No'}")
            print(f"Has Includes: {'Yes' if has_includes else 'No'}")

        except Exception as e:
            print(f"❌ Error reading template {template_path}: {e}")

    def _extract_metadata(self, content: str) -> TemplateMetadata:
        """Extract metadata from template frontmatter"""
        # Default metadata
        metadata = TemplateMetadata(
            name="unknown",
            version="1.0.0",
            description="No description provided",
            required_variables=[],
            optional_variables=[],
            tags=[],
            created_at=None,
        )

        # Try to parse frontmatter
        if content.startswith("---"):
            try:
                end_pos = content.find("---", 3)
                if end_pos > 0:
                    frontmatter = content[3:end_pos].strip()
                    import yaml

                    parsed = yaml.safe_load(frontmatter)

                    if parsed:
                        metadata.name = parsed.get("name", metadata.name)
                        metadata.version = parsed.get("version", metadata.version)
                        metadata.description = parsed.get(
                            "description", metadata.description
                        )
                        metadata.required_variables = parsed.get(
                            "required_variables", []
                        )
                        metadata.optional_variables = parsed.get(
                            "optional_variables", []
                        )
                        metadata.tags = parsed.get("tags", [])

            except Exception as e:
                print(f"⚠️  Warning: Could not parse frontmatter: {e}")

        return metadata

    def _display_validation_result(self, result, template_name: str):
        """Display validation results for a single template"""
        print(f"\n📊 Validation Results for {template_name}")
        print("-" * 40)

        if result.is_valid:
            print(f"✅ Template is VALID (Score: {result.score:.2f})")
        else:
            print(f"❌ Template is INVALID (Score: {result.score:.2f})")

        # Display metrics
        print(f"📏 Content Length: {result.metrics.get('content_length', 'N/A')}")
        print(f"🔤 Variable Count: {result.metrics.get('variable_count', 'N/A')}")
        print(f"🏷️  Tags Found: {result.metrics.get('tags_found', 'N/A')}")

        # Display issues
        if result.issues:
            print(f"\n⚠️  Issues Found ({len(result.issues)}):")
            for i, issue in enumerate(result.issues, 1):
                severity_icon = {
                    "info": "ℹ️",
                    "warning": "⚠️",
                    "error": "❌",
                    "critical": "🚨",
                }.get(issue.severity.value, "❓")

                print(
                    f"  {i}. {severity_icon} [{issue.severity.value.upper()}] {issue.message}"
                )
                if issue.suggestion:
                    print(f"     💡 Suggestion: {issue.suggestion}")
        else:
            print("✅ No issues found")

        print()

    def _display_summary(self, results: dict):
        """Display validation summary"""
        print("\n" + "=" * 50)
        print("📊 VALIDATION SUMMARY")
        print("=" * 50)

        total = len(results["valid"]) + len(results["invalid"]) + len(results["errors"])

        print(f"Total Templates: {total}")
        print(f"✅ Valid: {len(results['valid'])}")
        print(f"❌ Invalid: {len(results['invalid'])}")
        print(f"🚨 Errors: {len(results['errors'])}")

        if results["errors"]:
            print(f"\n🚨 Templates with errors:")
            for template_path, error in results["errors"]:
                print(f"  - {template_path}: {error}")

        if results["invalid"]:
            print(f"\n❌ Invalid templates:")
            for template_path in results["invalid"]:
                print(f"  - {template_path}")

        success_rate = (len(results["valid"]) / total * 100) if total > 0 else 0
        print(f"\n🎯 Success Rate: {success_rate:.1f}%")


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Validate prompt templates for Real2.AI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/validate_prompt.py validate app/prompts/user/analysis/contract_analysis.md
  python scripts/validate_prompt.py validate-all app/prompts/user
  python scripts/validate_prompt.py info app/prompts/user/analysis/contract_analysis.md
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Validate single template
    validate_parser = subparsers.add_parser(
        "validate", help="Validate a single template"
    )
    validate_parser.add_argument(
        "template_path", type=Path, help="Path to template file"
    )

    # Validate all templates
    validate_all_parser = subparsers.add_parser(
        "validate-all", help="Validate all templates in directory"
    )
    validate_all_parser.add_argument(
        "templates_dir", type=Path, help="Path to templates directory"
    )

    # Show template info
    info_parser = subparsers.add_parser(
        "info", help="Show information about a template"
    )
    info_parser.add_argument("template_path", type=Path, help="Path to template file")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    # Initialize CLI
    cli = PromptValidatorCLI()

    try:
        if args.command == "validate":
            success = cli.validate_template(args.template_path)
            sys.exit(0 if success else 1)

        elif args.command == "validate-all":
            results = cli.validate_all_templates(args.templates_dir)
            success = len(results["invalid"]) == 0 and len(results["errors"]) == 0
            sys.exit(0 if success else 1)

        elif args.command == "info":
            cli.show_template_info(args.template_path)

    except KeyboardInterrupt:
        print("\n⚠️  Validation interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
