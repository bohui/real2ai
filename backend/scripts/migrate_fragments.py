#!/usr/bin/env python3
"""
Fragment migration script for transitioning to the new folder-structure-driven system.

This script migrates existing fragments from the old orchestrator-based system 
to the new folder-structure-driven system according to the PRD requirements.
"""

import argparse
import logging
import yaml
from pathlib import Path
from typing import Dict, Any, Optional

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class FragmentMigrator:
    """Migrates fragments from old system to new folder-structure-driven system"""

    def __init__(self, old_fragments_dir: Path, new_fragments_dir: Path):
        self.old_fragments_dir = Path(old_fragments_dir)
        self.new_fragments_dir = Path(new_fragments_dir)
        
        # Migration mapping based on PRD specifications
        self.folder_mapping = {
            # State-specific fragments
            'nsw': 'state_requirements/NSW',
            'vic': 'state_requirements/VIC', 
            'qld': 'state_requirements/QLD',
            'sa': 'state_requirements/SA',
            'wa': 'state_requirements/WA',
            
            # Contract type specific
            'purchase': 'contract_types/purchase',
            'lease': 'contract_types/lease',
            'option': 'contract_types/option',
            
            # User experience and analysis
            'analysis': 'analysis_depth',  # Will need subfolder logic
            'guidance': 'user_experience', # Will need subfolder logic
            
            # Consumer protection
            'common': 'consumer_protection',
            
            # Other categories
            'commercial': 'shared',
            'high_value': 'shared',
            'ocr': 'shared'  # OCR fragments go to shared
        }
        
        # Category-specific context mappings
        self.context_mappings = {
            'state_specific': {'state': 'NSW'},  # Will be updated per fragment
            'legal_framework': {'state': '*', 'contract_type': '*'},
            'purchase': {'state': '*', 'contract_type': 'purchase'},
            'lease': {'state': '*', 'contract_type': 'lease'}, 
            'option': {'state': '*', 'contract_type': 'option'},
            'user_experience': {'user_experience': 'novice'},  # Default, will be refined
            'analysis': {'analysis_depth': 'comprehensive'},  # Default, will be refined
            'guidance': {'user_experience': '*'},
            'consumer_protection': {'state': '*', 'contract_type': '*'}
        }

    def migrate_all_fragments(self, dry_run: bool = False) -> Dict[str, Any]:
        """
        Migrate all fragments from old system to new system
        
        Args:
            dry_run: If True, show what would be done without making changes
            
        Returns:
            Migration report with statistics and issues
        """
        if not self.old_fragments_dir.exists():
            raise FileNotFoundError(f"Old fragments directory not found: {self.old_fragments_dir}")
        
        migration_report = {
            'migrated': [],
            'skipped': [],
            'errors': [],
            'dry_run': dry_run
        }
        
        # Create new directory structure
        if not dry_run:
            self._create_new_directory_structure()
        
        # Process all fragment files
        for fragment_file in self.old_fragments_dir.rglob("*.md"):
            try:
                result = self._migrate_fragment(fragment_file, dry_run)
                if result['status'] == 'migrated':
                    migration_report['migrated'].append(result)
                elif result['status'] == 'skipped':
                    migration_report['skipped'].append(result)
                else:
                    migration_report['errors'].append(result)
                    
            except Exception as e:
                logger.error(f"Failed to process {fragment_file}: {e}")
                migration_report['errors'].append({
                    'old_path': str(fragment_file),
                    'error': str(e),
                    'status': 'error'
                })
        
        # Print summary
        self._print_migration_summary(migration_report)
        
        return migration_report

    def _create_new_directory_structure(self):
        """Create the new directory structure"""
        directories = [
            'state_requirements/NSW',
            'state_requirements/VIC',
            'state_requirements/QLD', 
            'state_requirements/SA',
            'state_requirements/WA',
            'contract_types/purchase',
            'contract_types/lease',
            'contract_types/option',
            'user_experience/novice',
            'user_experience/intermediate',
            'user_experience/expert',
            'analysis_depth/comprehensive',
            'analysis_depth/quick',
            'analysis_depth/focused',
            'consumer_protection/cooling_off',
            'consumer_protection/statutory_warranties',
            'consumer_protection/unfair_terms',
            'risk_factors',
            'shared'
        ]
        
        for directory in directories:
            (self.new_fragments_dir / directory).mkdir(parents=True, exist_ok=True)
            
        logger.info(f"Created directory structure in {self.new_fragments_dir}")

    def _migrate_fragment(self, fragment_file: Path, dry_run: bool) -> Dict[str, Any]:
        """Migrate a single fragment file"""
        relative_path = fragment_file.relative_to(self.old_fragments_dir)
        old_folder = relative_path.parts[0] if len(relative_path.parts) > 1 else 'root'
        
        # Determine target directory
        target_dir = self._determine_target_directory(fragment_file, old_folder)
        if not target_dir:
            return {
                'status': 'skipped',
                'old_path': str(relative_path),
                'reason': f"No mapping found for folder: {old_folder}"
            }
        
        # Read and parse fragment
        content = fragment_file.read_text(encoding='utf-8')
        old_metadata, fragment_content = self._parse_fragment(content)
        
        # Transform metadata to new schema
        new_metadata = self._transform_metadata(old_metadata, fragment_file, old_folder)
        
        # Generate new file path
        new_file_path = self.new_fragments_dir / target_dir / fragment_file.name
        
        if dry_run:
            logger.info(f"Would migrate: {relative_path} -> {target_dir}/{fragment_file.name}")
            return {
                'status': 'migrated',
                'old_path': str(relative_path),
                'new_path': str(target_dir / fragment_file.name),
                'metadata_changes': self._get_metadata_changes(old_metadata, new_metadata)
            }
        else:
            # Write new fragment
            new_content = self._generate_new_fragment_content(new_metadata, fragment_content)
            new_file_path.parent.mkdir(parents=True, exist_ok=True)
            new_file_path.write_text(new_content, encoding='utf-8')
            
            logger.info(f"Migrated: {relative_path} -> {target_dir}/{fragment_file.name}")
            return {
                'status': 'migrated',
                'old_path': str(relative_path),
                'new_path': str(target_dir / fragment_file.name)
            }

    def _determine_target_directory(self, fragment_file: Path, old_folder: str) -> Optional[Path]:
        """Determine target directory for fragment based on old folder and metadata"""
        base_mapping = self.folder_mapping.get(old_folder)
        if not base_mapping:
            return None
        
        # Read fragment to get additional context for subfolder determination
        try:
            content = fragment_file.read_text(encoding='utf-8')
            old_metadata, _ = self._parse_fragment(content)
            
            # Special handling for analysis and guidance folders
            if base_mapping == 'analysis_depth':
                return Path(self._determine_analysis_depth_subfolder(old_metadata, fragment_file))
            elif base_mapping == 'user_experience':
                return Path(self._determine_user_experience_subfolder(old_metadata, fragment_file))
            
            return Path(base_mapping)
            
        except Exception:
            return Path(base_mapping) if base_mapping else None

    def _determine_analysis_depth_subfolder(self, metadata: Dict[str, Any], fragment_file: Path) -> str:
        """Determine analysis_depth subfolder based on fragment characteristics"""
        name = fragment_file.name.lower()
        description = metadata.get('description', '').lower()
        tags = [tag.lower() for tag in metadata.get('tags', [])]
        
        if any(keyword in name or keyword in description for keyword in ['detailed', 'comprehensive', 'complete', 'thorough']):
            return 'analysis_depth/comprehensive'
        elif any(keyword in name or keyword in description for keyword in ['quick', 'summary', 'brief', 'key']):
            return 'analysis_depth/quick'
        elif any(keyword in name or keyword in description for keyword in ['focused', 'targeted', 'specific']):
            return 'analysis_depth/focused'
        else:
            return 'analysis_depth/comprehensive'  # Default

    def _determine_user_experience_subfolder(self, metadata: Dict[str, Any], fragment_file: Path) -> str:
        """Determine user_experience subfolder based on fragment characteristics"""
        name = fragment_file.name.lower()
        description = metadata.get('description', '').lower()
        
        if any(keyword in name or keyword in description for keyword in ['novice', 'beginner', 'first_time', 'basic']):
            return 'user_experience/novice'
        elif any(keyword in name or keyword in description for keyword in ['expert', 'advanced', 'technical', 'professional']):
            return 'user_experience/expert'
        elif any(keyword in name or keyword in description for keyword in ['intermediate', 'advanced_considerations']):
            return 'user_experience/intermediate'
        else:
            return 'user_experience/novice'  # Default to novice

    def _parse_fragment(self, content: str) -> tuple[Dict[str, Any], str]:
        """Parse fragment content to extract metadata and content"""
        metadata = {}
        fragment_content = content
        
        if content.startswith('---'):
            end_pos = content.find('---', 3)
            if end_pos > 0:
                frontmatter = content[3:end_pos].strip()
                fragment_content = content[end_pos + 3:].strip()
                
                try:
                    metadata = yaml.safe_load(frontmatter) or {}
                except yaml.YAMLError:
                    pass
        
        return metadata, fragment_content

    def _transform_metadata(self, old_metadata: Dict[str, Any], fragment_file: Path, old_folder: str) -> Dict[str, Any]:
        """Transform old metadata schema to new schema"""
        new_metadata = {}
        
        # Copy over fields that remain the same
        for field in ['version', 'description', 'tags', 'priority']:
            if field in old_metadata:
                new_metadata[field] = old_metadata[field]
        
        # Set default priority if not present
        if 'priority' not in new_metadata:
            new_metadata['priority'] = 50
        
        # Transform category
        old_category = old_metadata.get('category', old_folder)
        new_metadata['category'] = self._transform_category(old_category)
        
        # Generate context based on old metadata and file location
        new_metadata['context'] = self._generate_context(old_metadata, fragment_file, old_folder)
        
        # Add version if not present
        if 'version' not in new_metadata:
            new_metadata['version'] = '1.0.0'
        
        return new_metadata

    def _transform_category(self, old_category: str) -> str:
        """Transform old category to new category"""
        category_mapping = {
            'state_specific': 'legal_requirement',
            'legal_framework': 'consumer_protection',
            'purchase': 'contract_specific',
            'lease': 'contract_specific',
            'option': 'contract_specific',
            'user_experience': 'guidance',
            'analysis': 'analysis',
            'guidance': 'guidance'
        }
        
        return category_mapping.get(old_category, old_category)

    def _generate_context(self, old_metadata: Dict[str, Any], fragment_file: Path, old_folder: str) -> Dict[str, Any]:
        """Generate context object for new schema"""
        context = {}
        
        # Start with base context from folder mapping
        base_context = self.context_mappings.get(old_metadata.get('category', old_folder), {})
        context.update(base_context)
        
        # Override with specific values from old metadata
        if 'state' in old_metadata:
            context['state'] = old_metadata['state'].upper()
        elif old_folder in ['nsw', 'vic', 'qld', 'sa', 'wa']:
            context['state'] = old_folder.upper()
        
        # Set contract type based on folder or metadata
        if old_folder in ['purchase', 'lease', 'option']:
            context['contract_type'] = old_folder
        
        # Ensure all context keys have values
        context_defaults = {
            'state': '*',
            'contract_type': '*',
            'user_experience': '*',
            'analysis_depth': '*'
        }
        
        for key, default_value in context_defaults.items():
            if key not in context:
                context[key] = default_value
        
        return context

    def _generate_new_fragment_content(self, metadata: Dict[str, Any], content: str) -> str:
        """Generate new fragment file content with updated metadata"""
        frontmatter = yaml.dump(metadata, default_flow_style=False, sort_keys=True)
        return f"---\n{frontmatter}---\n\n{content}"

    def _get_metadata_changes(self, old_metadata: Dict[str, Any], new_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Get summary of metadata changes for reporting"""
        changes = {
            'added': [],
            'removed': [],
            'modified': []
        }
        
        # Find added fields
        for key in new_metadata:
            if key not in old_metadata:
                changes['added'].append(key)
        
        # Find removed fields
        for key in old_metadata:
            if key not in new_metadata:
                changes['removed'].append(key)
        
        # Find modified fields
        for key in old_metadata:
            if key in new_metadata and old_metadata[key] != new_metadata[key]:
                changes['modified'].append(f"{key}: {old_metadata[key]} -> {new_metadata[key]}")
        
        return changes

    def _print_migration_summary(self, report: Dict[str, Any]):
        """Print migration summary"""
        print("\n" + "="*60)
        print("FRAGMENT MIGRATION SUMMARY")
        print("="*60)
        print(f"Mode: {'DRY RUN' if report['dry_run'] else 'ACTUAL MIGRATION'}")
        print(f"Migrated: {len(report['migrated'])}")
        print(f"Skipped: {len(report['skipped'])}")
        print(f"Errors: {len(report['errors'])}")
        
        if report['skipped']:
            print("\nSkipped fragments:")
            for item in report['skipped']:
                print(f"  - {item['old_path']}: {item['reason']}")
        
        if report['errors']:
            print("\nErrors:")
            for item in report['errors']:
                print(f"  - {item['old_path']}: {item.get('error', 'Unknown error')}")


def main():
    """Main migration script entry point"""
    parser = argparse.ArgumentParser(description='Migrate fragments to new folder-structure-driven system')
    parser.add_argument('old_fragments_dir', help='Path to existing fragments directory')
    parser.add_argument('new_fragments_dir', help='Path to new fragments directory')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done without making changes')
    
    args = parser.parse_args()
    
    migrator = FragmentMigrator(
        old_fragments_dir=Path(args.old_fragments_dir),
        new_fragments_dir=Path(args.new_fragments_dir)
    )
    
    try:
        report = migrator.migrate_all_fragments(dry_run=args.dry_run)
        
        if not args.dry_run:
            print(f"\nMigration complete! New fragments created in: {args.new_fragments_dir}")
            print("Remember to:")
            print("1. Update base templates to use new group variable names")
            print("2. Remove deprecated orchestrator fragment mapping configurations")
            print("3. Test the new system with realistic contexts")
        
        return 0
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        return 1


if __name__ == '__main__':
    exit(main())