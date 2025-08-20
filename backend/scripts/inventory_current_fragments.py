#!/usr/bin/env python3
"""
Inventory current fragments and analyze migration requirements.

This script analyzes the existing fragment structure and provides:
1. Inventory of all current fragments with metadata
2. First-level folder candidates to derive group names
3. Base template analysis and placeholder mapping
4. Context key audit for metadata normalization
"""

import yaml
import re
from pathlib import Path
from typing import Dict, Any, List, Set, Optional
from collections import defaultdict, Counter


class FragmentInventory:
    """Comprehensive analysis of current fragment system"""

    def __init__(self, fragments_dir: Path, templates_dir: Path):
        self.fragments_dir = Path(fragments_dir)
        self.templates_dir = Path(templates_dir)

    def run_complete_inventory(self) -> Dict[str, Any]:
        """Run complete inventory and analysis"""
        print("📋 FRAGMENT SYSTEM INVENTORY")
        print("=" * 60)
        
        inventory = {
            "fragments": self.inventory_fragments(),
            "folder_analysis": self.analyze_folder_structure(),
            "template_analysis": self.analyze_templates(),
            "context_analysis": self.analyze_context_keys(),
            "migration_recommendations": {}
        }
        
        # Generate migration recommendations
        inventory["migration_recommendations"] = self.generate_migration_recommendations(inventory)
        
        return inventory

    def inventory_fragments(self) -> Dict[str, Any]:
        """Complete inventory of all fragments"""
        print("\n📁 FRAGMENT INVENTORY")
        print("-" * 40)
        
        fragments = []
        categories = Counter()
        states = Counter()
        tags_counter = Counter()
        priority_distribution = Counter()
        
        if not self.fragments_dir.exists():
            print(f"❌ Fragments directory not found: {self.fragments_dir}")
            return {"error": "Fragments directory not found"}
        
        for fragment_file in self.fragments_dir.rglob("*.md"):
            try:
                relative_path = fragment_file.relative_to(self.fragments_dir)
                folder_path = relative_path.parent
                
                content = fragment_file.read_text(encoding='utf-8')
                metadata, fragment_content = self._parse_fragment(content)
                
                # Extract analysis data
                category = metadata.get('category', 'unknown')
                state = metadata.get('state', 'unknown')
                tags = metadata.get('tags', [])
                priority = metadata.get('priority', 50)
                
                categories[category] += 1
                states[state] += 1
                tags_counter.update(tags)
                priority_distribution[str(priority)] += 1
                
                fragment_info = {
                    'file_path': str(relative_path),
                    'folder': str(folder_path),
                    'name': fragment_file.name,
                    'metadata': metadata,
                    'content_length': len(fragment_content),
                    'has_frontmatter': content.startswith('---')
                }
                
                fragments.append(fragment_info)
                
            except Exception as e:
                print(f"⚠️  Error processing {fragment_file}: {e}")
        
        print(f"✅ Found {len(fragments)} fragments")
        print(f"📊 Categories: {dict(categories.most_common())}")
        print(f"🗺️  States: {dict(states.most_common())}")
        print(f"🏷️  Top tags: {dict(tags_counter.most_common(10))}")
        
        return {
            "total_fragments": len(fragments),
            "fragments": fragments,
            "categories": dict(categories),
            "states": dict(states),
            "tags": dict(tags_counter),
            "priority_distribution": dict(priority_distribution)
        }

    def analyze_folder_structure(self) -> Dict[str, Any]:
        """Analyze current folder structure and propose group names"""
        print("\n📂 FOLDER STRUCTURE ANALYSIS")
        print("-" * 40)
        
        folders = defaultdict(list)
        proposed_groups = {}
        
        for fragment_file in self.fragments_dir.rglob("*.md"):
            relative_path = fragment_file.relative_to(self.fragments_dir)
            if len(relative_path.parts) > 1:
                first_level = relative_path.parts[0]
                folders[first_level].append(str(relative_path))
        
        # Propose group mappings based on PRD
        group_mapping = {
            # State-specific
            'nsw': 'state_requirements',
            'vic': 'state_requirements', 
            'qld': 'state_requirements',
            'sa': 'state_requirements',
            'wa': 'state_requirements',
            
            # Contract types
            'purchase': 'contract_types',
            'lease': 'contract_types',
            'option': 'contract_types',
            
            # User experience and analysis
            'analysis': 'analysis_depth',
            'guidance': 'user_experience',
            
            # Consumer protection
            'common': 'consumer_protection',
            
            # Other categories
            'commercial': 'shared',
            'high_value': 'shared',
            'ocr': 'shared'
        }
        
        for folder, fragments in folders.items():
            proposed_group = group_mapping.get(folder, 'shared')
            proposed_groups[folder] = {
                'fragment_count': len(fragments),
                'fragments': fragments,
                'proposed_group': proposed_group
            }
            
            print(f"📁 {folder}/ ({len(fragments)} fragments) → {proposed_group}")
        
        return {
            "current_folders": dict(folders),
            "proposed_groups": proposed_groups,
            "group_mapping": group_mapping
        }

    def analyze_templates(self) -> Dict[str, Any]:
        """Analyze base templates for placeholder usage"""
        print("\n📄 TEMPLATE ANALYSIS")
        print("-" * 40)
        
        templates = []
        placeholders_found = set()
        placeholder_mappings = {}
        
        if not self.templates_dir.exists():
            print(f"⚠️  Templates directory not found: {self.templates_dir}")
            return {"error": "Templates directory not found"}
        
        # Define placeholder mappings according to PRD
        old_to_new_mappings = {
            'state_legal_requirements_fragments': 'state_requirements',
            'consumer_protection_fragments': 'consumer_protection',
            'contract_type_specific_fragments': 'contract_types',
            'experience_level_guidance_fragments': 'user_experience',
            'analysis_depth_fragments': 'analysis_depth',
            'state_specific_fragments': 'state_requirements',
            'contract_type_fragments': 'contract_types',
            'quality_requirements_fragments': 'shared',
            'user_experience_fragments': 'user_experience',
            'financial_risk_fragments': 'risk_factors',
            'experience_level_fragments': 'user_experience',
            'state_specific_analysis_fragments': 'state_requirements',
            'state_compliance_fragments': 'state_requirements'
        }
        
        for template_file in self.templates_dir.rglob("*.md"):
            try:
                content = template_file.read_text(encoding='utf-8')
                
                # Find all {{ variable }} patterns
                variable_pattern = re.compile(r'\{\{\s*([a-zA-Z][a-zA-Z0-9_]*)\s*\}\}')
                variables = variable_pattern.findall(content)
                
                placeholders_found.update(variables)
                
                template_info = {
                    'file_path': str(template_file.relative_to(self.templates_dir)),
                    'variables': variables,
                    'content_length': len(content)
                }
                
                templates.append(template_info)
                
            except Exception as e:
                print(f"⚠️  Error processing template {template_file}: {e}")
        
        # Analyze placeholder mappings
        for placeholder in placeholders_found:
            if placeholder in old_to_new_mappings:
                placeholder_mappings[placeholder] = old_to_new_mappings[placeholder]
                print(f"🔄 {{ {placeholder} }} → {{ {old_to_new_mappings[placeholder]} }}")
            else:
                placeholder_mappings[placeholder] = placeholder  # Keep as-is
                print(f"✅ {{ {placeholder} }} (no change needed)")
        
        return {
            "templates": templates,
            "placeholders_found": list(placeholders_found),
            "placeholder_mappings": placeholder_mappings,
            "old_to_new_mappings": old_to_new_mappings
        }

    def analyze_context_keys(self) -> Dict[str, Any]:
        """Analyze existing metadata for context key normalization"""
        print("\n🔑 CONTEXT KEY ANALYSIS")
        print("-" * 40)
        
        context_keys = defaultdict(set)
        metadata_patterns = defaultdict(int)
        normalization_opportunities = []
        
        minimal_context_keys = {
            'state': 'Jurisdiction (NSW, VIC, QLD, etc.)',
            'contract_type': 'Contract type (purchase, lease, option)',
            'user_experience': 'User level (novice, intermediate, expert)',
            'analysis_depth': 'Analysis depth (comprehensive, quick, focused)'
        }
        
        for fragment_file in self.fragments_dir.rglob("*.md"):
            try:
                content = fragment_file.read_text(encoding='utf-8')
                metadata, _ = self._parse_fragment(content)
                
                # Collect all metadata keys and values
                for key, value in metadata.items():
                    context_keys[key].add(str(value))
                    metadata_patterns[key] += 1
                
                # Check for normalization opportunities
                fragment_name = fragment_file.name
                
                # Extract context clues from folder and metadata
                relative_path = fragment_file.relative_to(self.fragments_dir)
                folder = relative_path.parts[0] if len(relative_path.parts) > 1 else 'root'
                
                proposed_context = self._propose_context_for_fragment(metadata, folder, fragment_name)
                
                if proposed_context:
                    normalization_opportunities.append({
                        'fragment': str(relative_path),
                        'current_metadata': metadata,
                        'proposed_context': proposed_context
                    })
                
            except Exception as e:
                continue
        
        print("📊 Current metadata keys:")
        for key, count in sorted(metadata_patterns.items(), key=lambda x: x[1], reverse=True):
            values = list(context_keys[key])[:5]  # Show first 5 values
            print(f"  {key}: {count} fragments (values: {values})")
        
        print("\n🎯 Proposed minimal context keys:")
        for key, description in minimal_context_keys.items():
            print(f"  {key}: {description}")
        
        return {
            "current_keys": dict(context_keys),
            "key_usage_count": dict(metadata_patterns),
            "minimal_context_keys": minimal_context_keys,
            "normalization_opportunities": normalization_opportunities[:10]  # Show first 10
        }

    def generate_migration_recommendations(self, inventory: Dict[str, Any]) -> Dict[str, Any]:
        """Generate specific migration recommendations"""
        print("\n🚀 MIGRATION RECOMMENDATIONS")
        print("-" * 40)
        
        recommendations = {
            "folder_migrations": [],
            "template_updates": [],
            "metadata_normalizations": [],
            "priority_actions": []
        }
        
        # Folder migration recommendations
        folder_analysis = inventory.get("folder_analysis", {})
        for folder, info in folder_analysis.get("proposed_groups", {}).items():
            recommendations["folder_migrations"].append({
                "from": f"fragments/{folder}/",
                "to": f"fragments_new/{info['proposed_group']}/",
                "fragment_count": info["fragment_count"],
                "action": f"Move {info['fragment_count']} fragments to {info['proposed_group']} group"
            })
        
        # Template update recommendations
        template_analysis = inventory.get("template_analysis", {})
        for old_placeholder, new_placeholder in template_analysis.get("placeholder_mappings", {}).items():
            if old_placeholder != new_placeholder:
                recommendations["template_updates"].append({
                    "from": f"{{{{ {old_placeholder} }}}}",
                    "to": f"{{{{ {new_placeholder} }}}}",
                    "action": f"Replace placeholder in all templates"
                })
        
        # Priority actions
        recommendations["priority_actions"] = [
            "1. Create new folder structure with group directories",
            "2. Migrate fragments with metadata normalization",
            "3. Update base templates with new placeholder names",
            "4. Remove orchestrator fragment mapping configurations",
            "5. Test new system with realistic contexts",
            "6. Deploy with fallback to old system"
        ]
        
        for action in recommendations["priority_actions"]:
            print(f"📌 {action}")
        
        return recommendations

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

    def _propose_context_for_fragment(self, metadata: Dict[str, Any], folder: str, fragment_name: str) -> Optional[Dict[str, Any]]:
        """Propose context based on current metadata and file location"""
        context = {}
        
        # Derive state from folder or metadata
        if folder.upper() in ['NSW', 'VIC', 'QLD', 'SA', 'WA']:
            context['state'] = folder.upper()
        elif 'state' in metadata:
            context['state'] = str(metadata['state']).upper()
        else:
            context['state'] = '*'
        
        # Derive contract type from folder or metadata
        if folder in ['purchase', 'lease', 'option']:
            context['contract_type'] = folder
        elif metadata.get('category') in ['purchase', 'lease', 'option']:
            context['contract_type'] = metadata['category']
        else:
            context['contract_type'] = '*'
        
        # Derive user experience from file name or metadata
        if any(term in fragment_name.lower() for term in ['novice', 'beginner', 'first_time']):
            context['user_experience'] = 'novice'
        elif any(term in fragment_name.lower() for term in ['expert', 'advanced', 'technical']):
            context['user_experience'] = 'expert'
        elif any(term in fragment_name.lower() for term in ['intermediate']):
            context['user_experience'] = 'intermediate'
        else:
            context['user_experience'] = '*'
        
        # Derive analysis depth from file name or metadata
        if any(term in fragment_name.lower() for term in ['detailed', 'comprehensive', 'complete']):
            context['analysis_depth'] = 'comprehensive'
        elif any(term in fragment_name.lower() for term in ['quick', 'summary', 'brief']):
            context['analysis_depth'] = 'quick'
        elif any(term in fragment_name.lower() for term in ['focused', 'targeted']):
            context['analysis_depth'] = 'focused'
        else:
            context['analysis_depth'] = '*'
        
        return context if any(v != '*' for v in context.values()) else None

    def print_inventory_summary(self, inventory: Dict[str, Any]):
        """Print a comprehensive summary"""
        print("\n" + "=" * 60)
        print("📊 INVENTORY SUMMARY")
        print("=" * 60)
        
        fragments = inventory.get("fragments", {})
        print(f"📁 Total fragments: {fragments.get('total_fragments', 0)}")
        print(f"🏷️  Categories: {len(fragments.get('categories', {}))}")
        print(f"🗺️  States: {len(fragments.get('states', {}))}")
        
        folder_analysis = inventory.get("folder_analysis", {})
        print(f"📂 Current folders: {len(folder_analysis.get('current_folders', {}))}")
        
        template_analysis = inventory.get("template_analysis", {})
        print(f"📄 Templates: {len(template_analysis.get('templates', []))}")
        print(f"🔗 Placeholders: {len(template_analysis.get('placeholders_found', []))}")
        
        migration = inventory.get("migration_recommendations", {})
        print(f"🚀 Folder migrations needed: {len(migration.get('folder_migrations', []))}")
        print(f"🔄 Template updates needed: {len(migration.get('template_updates', []))}")


def main():
    """Main inventory script entry point"""
    # Get directories relative to script location
    script_dir = Path(__file__).parent
    backend_dir = script_dir.parent
    
    fragments_dir = backend_dir / "app" / "prompts" / "fragments"
    templates_dir = backend_dir / "app" / "prompts" / "templates"
    
    if not fragments_dir.exists():
        print(f"❌ Fragments directory not found: {fragments_dir}")
        return 1
    
    # Run inventory
    analyzer = FragmentInventory(fragments_dir, templates_dir)
    inventory = analyzer.run_complete_inventory()
    
    # Print summary
    analyzer.print_inventory_summary(inventory)
    
    # Save detailed results
    output_file = script_dir / "fragment_inventory_results.yaml"
    with open(output_file, 'w') as f:
        yaml.dump(inventory, f, default_flow_style=False, sort_keys=True)
    
    print(f"\n💾 Detailed results saved to: {output_file}")
    
    return 0


if __name__ == '__main__':
    exit(main())