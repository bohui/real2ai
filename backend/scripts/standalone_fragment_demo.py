#!/usr/bin/env python3
"""
Standalone demonstration of the new fragment system.

This script creates a minimal working example of the fragment system
without dependencies on the existing codebase.
"""

import tempfile
import shutil
import yaml
from pathlib import Path
from typing import Dict, Any, List, Optional


class ContextMatcher:
    """Generic context matching with wildcard and list support"""

    def matches_context(self, fragment_context: Dict[str, Any], runtime_context: Dict[str, Any]) -> bool:
        """Check if fragment context matches runtime context"""
        if not fragment_context:
            return True

        for key, required in fragment_context.items():
            # Wildcard matches anything
            if required == "*":
                continue

            actual = runtime_context.get(key)
            if actual is None:
                return False

            # Normalize strings for case-insensitive comparison
            def norm(v):
                return v.lower() if isinstance(v, str) else v

            if isinstance(required, list):
                if norm(actual) not in [norm(x) for x in required]:
                    return False
            else:
                if norm(actual) != norm(required):
                    return False

        return True


class FolderFragmentManager:
    """Simplified folder-structure-driven fragment manager"""

    def __init__(self, fragments_dir: Path):
        self.fragments_dir = Path(fragments_dir)
        self.context_matcher = ContextMatcher()
        self._fragment_cache = {}

    def get_available_groups(self) -> List[str]:
        """Get all available fragment groups from folder structure"""
        groups = []
        if not self.fragments_dir.exists():
            return groups
            
        for item in self.fragments_dir.iterdir():
            if item.is_dir() and not item.name.startswith('.'):
                groups.append(item.name)
        
        return sorted(groups)

    def compose_fragments(self, runtime_context: Dict[str, Any]) -> Dict[str, str]:
        """Compose fragments based on context and return group variables"""
        groups = self.get_available_groups()
        group_variables = {}
        
        for group_name in groups:
            # Load all fragments for this group
            all_fragments = self._load_fragments_for_group(group_name)
            
            # Filter fragments based on context
            matching_fragments = []
            for fragment in all_fragments:
                fragment_context = fragment.get('metadata', {}).get('context', {})
                if self.context_matcher.matches_context(fragment_context, runtime_context):
                    matching_fragments.append(fragment)
            
            # Sort by priority and compose content
            matching_fragments.sort(key=lambda f: f.get('priority', 50), reverse=True)
            
            if matching_fragments:
                content_parts = [f['content'] for f in matching_fragments]
                group_variables[group_name] = "\n\n".join(content_parts)
            else:
                group_variables[group_name] = ""
        
        return group_variables

    def _load_fragments_for_group(self, group_name: str) -> List[Dict[str, Any]]:
        """Load all fragments for a specific group"""
        group_dir = self.fragments_dir / group_name
        if not group_dir.exists():
            return []
        
        fragments = []
        for fragment_file in group_dir.rglob("*.md"):
            try:
                content = fragment_file.read_text(encoding="utf-8")
                metadata, fragment_content = self._parse_fragment(content)
                
                fragment = {
                    'name': fragment_file.name,
                    'content': fragment_content,
                    'metadata': metadata,
                    'priority': metadata.get('priority', 50)
                }
                fragments.append(fragment)
                
            except Exception as e:
                print(f"Error loading fragment {fragment_file}: {e}")
        
        return fragments

    def _parse_fragment(self, content: str) -> tuple:
        """Parse fragment content to extract metadata and content"""
        metadata = {}
        fragment_content = content
        
        if content.startswith("---"):
            end_pos = content.find("---", 3)
            if end_pos > 0:
                frontmatter = content[3:end_pos].strip()
                fragment_content = content[end_pos + 3:].strip()
                
                try:
                    metadata = yaml.safe_load(frontmatter) or {}
                except yaml.YAMLError:
                    pass
        
        return metadata, fragment_content


def create_demo_fragments(base_dir: Path):
    """Create demonstration fragments"""
    
    # Create folder structure
    folders = [
        "state_requirements/NSW",
        "state_requirements/VIC",
        "contract_types/purchase",
        "contract_types/lease",
        "user_experience/novice",
        "user_experience/expert",
        "consumer_protection"
    ]
    
    for folder in folders:
        (base_dir / folder).mkdir(parents=True, exist_ok=True)
    
    # NSW Planning Requirements
    nsw_planning = """---
category: "legal_requirement"
context:
  state: "NSW"
  contract_type: "*"
priority: 80
version: "1.0.0"
description: "NSW Section 149 planning certificate requirements"
---

### NSW Section 149 Planning Certificates

**Critical NSW Requirement**: Section 149 planning certificates must be provided under NSW Conveyancing Act.

**Key Information to Verify**:
- Zoning Classification: Residential, commercial, industrial designation
- Development Restrictions: Height limits, floor space ratios, setbacks
- Heritage Listings: Conservation areas or individual listings"""

    (base_dir / "state_requirements/NSW/planning_certificates.md").write_text(nsw_planning)

    # VIC Vendor Statement
    vic_vendor = """---
category: "legal_requirement"
context:
  state: "VIC"
  contract_type: "*"
priority: 85
version: "1.0.0"
description: "Victorian vendor statement requirements"
---

### Victorian Vendor Statement Requirements

**Section 32 Statement**: Must be provided before contract signing.

**Key Components**:
- Property details and title information
- Planning and building permits
- Outgoings and rates information"""

    (base_dir / "state_requirements/VIC/vendor_statements.md").write_text(vic_vendor)

    # Purchase Settlement
    purchase_settlement = """---
category: "contract_specific"
context:
  state: "*"
  contract_type: "purchase"
priority: 70
version: "1.0.0"
description: "Purchase settlement requirements"
---

### Purchase Settlement Requirements

**Settlement Process**:
- Final inspection before settlement
- Balance payment on settlement date
- Title transfer and registration"""

    (base_dir / "contract_types/purchase/settlement_requirements.md").write_text(purchase_settlement)

    # Lease Obligations
    lease_obligations = """---
category: "contract_specific"
context:
  state: "*"
  contract_type: "lease"
priority: 70
version: "1.0.0"
description: "Lease rental obligations"
---

### Lease Rental Obligations

**Tenant Responsibilities**:
- Regular rental payments
- Property maintenance duties
- Compliance with lease terms"""

    (base_dir / "contract_types/lease/rental_obligations.md").write_text(lease_obligations)

    # Novice User Guidance
    novice_guidance = """---
category: "guidance"
context:
  user_experience: "novice"
priority: 60
version: "1.0.0"
description: "Guidance for first-time property buyers"
---

### First Time Buyer Guidance

**Important Steps**:
- Understand cooling off periods
- Arrange building and pest inspections
- Secure finance pre-approval"""

    (base_dir / "user_experience/novice/first_time_buyer.md").write_text(novice_guidance)

    # Expert User Guidance
    expert_guidance = """---
category: "guidance"
context:
  user_experience: "expert"
priority: 65
version: "1.0.0"
description: "Advanced considerations for experienced buyers"
---

### Advanced Buyer Considerations

**Due Diligence**:
- Market analysis and comparable sales
- Legal structure optimization
- Tax implications assessment"""

    (base_dir / "user_experience/expert/advanced_considerations.md").write_text(expert_guidance)

    # Universal Consumer Protection
    consumer_protection = """---
category: "consumer_protection"
context: {}
priority: 90
version: "1.0.0"
description: "Universal consumer protection framework"
---

### Consumer Protection Rights

**Universal Protection**: All states provide cooling off periods for residential property purchases.

**Key Rights**:
- Right to withdraw within cooling off period
- Penalty limitations for early withdrawal
- Exceptions for auction purchases"""

    (base_dir / "consumer_protection/cooling_off_framework.md").write_text(consumer_protection)


def create_demo_template() -> str:
    """Create demonstration template"""
    return """# Contract Analysis Report

## State-Specific Legal Requirements
{{ state_requirements }}

## Contract Type Analysis
{{ contract_types }}

## User Guidance
{{ user_experience }}

## Consumer Protection Information
{{ consumer_protection }}

---

**Analysis Complete**: Review all sections above for relevant requirements and guidance."""


def demonstrate_context_matching():
    """Demonstrate context matching functionality"""
    print("🧪 DEMONSTRATING CONTEXT MATCHING")
    print("-" * 50)
    
    matcher = ContextMatcher()
    
    test_cases = [
        {
            "name": "Exact match",
            "fragment_context": {"state": "NSW"},
            "runtime_context": {"state": "NSW"},
            "expected": True
        },
        {
            "name": "Case insensitive match",
            "fragment_context": {"state": "NSW"},
            "runtime_context": {"state": "nsw"},
            "expected": True
        },
        {
            "name": "Wildcard match",
            "fragment_context": {"state": "*", "contract_type": "*"},
            "runtime_context": {"state": "NSW", "contract_type": "purchase"},
            "expected": True
        },
        {
            "name": "List match",
            "fragment_context": {"contract_type": ["purchase", "option"]},
            "runtime_context": {"contract_type": "purchase"},
            "expected": True
        },
        {
            "name": "No match",
            "fragment_context": {"state": "NSW"},
            "runtime_context": {"state": "VIC"},
            "expected": False
        },
        {
            "name": "Missing context key",
            "fragment_context": {"state": "NSW", "missing_key": "value"},
            "runtime_context": {"state": "NSW"},
            "expected": False
        }
    ]
    
    for test_case in test_cases:
        result = matcher.matches_context(
            test_case["fragment_context"], 
            test_case["runtime_context"]
        )
        status = "✅ PASS" if result == test_case["expected"] else "❌ FAIL"
        print(f"{status} {test_case['name']}: {result}")


def demonstrate_fragment_composition():
    """Demonstrate complete fragment composition"""
    print("\n🔧 DEMONSTRATING FRAGMENT COMPOSITION")
    print("-" * 50)
    
    # Create temporary directory with demo fragments
    with tempfile.TemporaryDirectory() as temp_dir:
        fragments_dir = Path(temp_dir) / "fragments"
        create_demo_fragments(fragments_dir)
        
        manager = FolderFragmentManager(fragments_dir)
        
        # Test scenarios
        scenarios = [
            {
                "name": "NSW Purchase - Novice User",
                "context": {
                    "state": "NSW",
                    "contract_type": "purchase",
                    "user_experience": "novice"
                }
            },
            {
                "name": "VIC Lease - Expert User",
                "context": {
                    "state": "VIC",
                    "contract_type": "lease",
                    "user_experience": "expert"
                }
            },
            {
                "name": "Unknown State - Any Contract",
                "context": {
                    "state": "QLD",  # No QLD fragments
                    "contract_type": "purchase",
                    "user_experience": "novice"
                }
            }
        ]
        
        for scenario in scenarios:
            print(f"\n📋 Scenario: {scenario['name']}")
            print(f"   Context: {scenario['context']}")
            
            result = manager.compose_fragments(scenario['context'])
            
            for group, content in result.items():
                if content.strip():
                    print(f"   ✅ {group}: {len(content)} chars")
                else:
                    print(f"   ⭕ {group}: empty")


def demonstrate_template_composition():
    """Demonstrate complete template composition with Jinja2"""
    print("\n🎨 DEMONSTRATING TEMPLATE COMPOSITION")
    print("-" * 50)
    
    try:
        from jinja2 import Environment, BaseLoader, Undefined
        
        with tempfile.TemporaryDirectory() as temp_dir:
            fragments_dir = Path(temp_dir) / "fragments"
            create_demo_fragments(fragments_dir)
            
            manager = FolderFragmentManager(fragments_dir)
            
            # Test context
            context = {
                "state": "NSW",
                "contract_type": "purchase",
                "user_experience": "novice"
            }
            
            # Get fragment variables
            fragment_variables = manager.compose_fragments(context)
            
            # Create template
            template_content = create_demo_template()
            
            class StringLoader(BaseLoader):
                def get_source(self, environment, template):
                    return template_content, None, lambda: True
            
            env = Environment(
                loader=StringLoader(),
                undefined=Undefined,
                trim_blocks=True,
                lstrip_blocks=True,
            )
            
            template = env.get_template("")
            
            # Render with fragment variables
            render_vars = context.copy()
            render_vars.update(fragment_variables)
            
            composed_result = template.render(**render_vars)
            
            print(f"✅ Template composition successful!")
            print(f"   Template length: {len(template_content)} chars")
            print(f"   Composed length: {len(composed_result)} chars")
            print(f"   Contains NSW content: {'NSW' in composed_result}")
            print(f"   Contains purchase content: {'settlement' in composed_result.lower()}")
            
            # Show sample of composed content
            print("\n📄 Sample composed content:")
            lines = composed_result.split('\n')
            for i, line in enumerate(lines[:15]):  # Show first 15 lines
                print(f"   {line}")
            if len(lines) > 15:
                print(f"   ... ({len(lines) - 15} more lines)")
    
    except ImportError:
        print("❌ Jinja2 not available - skipping template composition demo")


def main():
    """Main demonstration script"""
    print("🚀 FRAGMENT SYSTEM REDESIGN DEMONSTRATION")
    print("=" * 60)
    print("This script demonstrates the new folder-structure-driven fragment system")
    print("according to the PRD requirements.\n")
    
    # Run demonstrations
    demonstrate_context_matching()
    demonstrate_fragment_composition()
    demonstrate_template_composition()
    
    print("\n" + "=" * 60)
    print("✅ DEMONSTRATION COMPLETE")
    print("\nKey Features Demonstrated:")
    print("• Folder-structure-driven grouping (state_requirements/, contract_types/, etc.)")
    print("• Generic context matching with wildcards and list support")
    print("• Template variables automatically named after group folders")
    print("• Empty groups render as empty strings (no template errors)")
    print("• Fragment priority ordering within groups")
    print("• Complete template composition with Jinja2")
    
    print("\nNext Steps:")
    print("1. Complete migration of all existing fragments")
    print("2. Update base templates to use new group variable names")
    print("3. Remove deprecated orchestrator fragment mapping code")
    print("4. Deploy and test with real contract analysis workflows")


if __name__ == '__main__':
    main()