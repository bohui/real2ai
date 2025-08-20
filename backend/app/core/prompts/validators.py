"""Validators for fragment system structure and metadata"""

import logging
import re
import yaml
from typing import Dict, Any, List, Optional, Set
from pathlib import Path

logger = logging.getLogger(__name__)


class FragmentStructureValidator:
    """Validator for fragment folder structure and naming conventions"""

    def __init__(self, fragments_dir: Path):
        self.fragments_dir = Path(fragments_dir)
        self.valid_name_pattern = re.compile(r'^[a-zA-Z][a-zA-Z0-9_]*$')

    def validate_folder_structure(self) -> Dict[str, Any]:
        """
        Validate fragment folder structure and naming
        
        Returns:
            Validation result with issues and recommendations
        """
        issues = []
        warnings = []
        groups = []

        if not self.fragments_dir.exists():
            return {
                "valid": False,
                "issues": [f"Fragments directory does not exist: {self.fragments_dir}"],
                "warnings": [],
                "groups": [],
                "total_groups": 0
            }

        # Check first-level folders (groups)
        for item in self.fragments_dir.iterdir():
            if item.is_dir() and not item.name.startswith('.'):
                group_name = item.name
                groups.append(group_name)

                # Validate group name
                if not self.valid_name_pattern.match(group_name):
                    issues.append(
                        f"Invalid group name: '{group_name}' "
                        "(must start with letter, contain only letters, digits, underscore)"
                    )

                # Check for fragments in group
                fragment_count = len(list(item.rglob("*.md")))
                if fragment_count == 0:
                    warnings.append(f"Group '{group_name}' contains no fragments")

        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "warnings": warnings,
            "groups": sorted(groups),
            "total_groups": len(groups)
        }

    def validate_template_references(
        self, 
        template_content: str, 
        available_groups: List[str]
    ) -> Dict[str, Any]:
        """
        Validate that template variable references match available groups
        
        Args:
            template_content: Content of base template
            available_groups: List of available fragment groups
            
        Returns:
            Validation result for template references
        """
        issues = []
        warnings = []
        referenced_groups = set()
        missing_groups = []
        unused_groups = []

        # Find template variable references (simple regex for {{ variable_name }})
        import re
        variable_pattern = re.compile(r'\{\{\s*([a-zA-Z][a-zA-Z0-9_]*)\s*\}\}')
        matches = variable_pattern.findall(template_content)

        for match in matches:
            referenced_groups.add(match)

        # Check for referenced groups that don't exist
        for ref_group in referenced_groups:
            if ref_group not in available_groups:
                missing_groups.append(ref_group)
                issues.append(
                    f"Template references group '{ref_group}' but no corresponding folder exists"
                )

        # Check for available groups that aren't referenced
        for group in available_groups:
            if group not in referenced_groups:
                unused_groups.append(group)
                warnings.append(
                    f"Group '{group}' exists but is not referenced in template"
                )

        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "warnings": warnings,
            "referenced_groups": sorted(list(referenced_groups)),
            "missing_groups": missing_groups,
            "unused_groups": unused_groups
        }


class FragmentMetadataValidator:
    """Validator for fragment metadata schema"""

    def __init__(self):
        self.required_fields = []  # No required fields in new schema
        self.deprecated_fields = ["group", "domain"]
        self.valid_context_types = [str, list, type(None)]

    def validate_fragment_metadata(self, metadata: Dict[str, Any], fragment_path: str) -> Dict[str, Any]:
        """
        Validate individual fragment metadata against new schema
        
        Args:
            metadata: Fragment metadata dictionary
            fragment_path: Path to fragment for error reporting
            
        Returns:
            Validation result for fragment metadata
        """
        issues = []
        warnings = []
        deprecated_found = []

        # Check for deprecated fields
        for field in self.deprecated_fields:
            if field in metadata:
                deprecated_found.append(field)
                warnings.append(f"Deprecated field '{field}' found in {fragment_path}")

        # Validate context structure if present
        context = metadata.get("context")
        if context is not None:
            context_validation = self._validate_context_structure(context, fragment_path)
            issues.extend(context_validation["issues"])
            warnings.extend(context_validation["warnings"])

        # Validate priority if present
        priority = metadata.get("priority")
        if priority is not None:
            if not isinstance(priority, int) or priority < 0 or priority > 100:
                issues.append(f"Priority must be integer between 0-100 in {fragment_path}")

        # Validate version if present
        version = metadata.get("version")
        if version is not None and not isinstance(version, str):
            issues.append(f"Version must be string in {fragment_path}")

        # Validate tags if present
        tags = metadata.get("tags")
        if tags is not None:
            if not isinstance(tags, list) or not all(isinstance(tag, str) for tag in tags):
                issues.append(f"Tags must be list of strings in {fragment_path}")

        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "warnings": warnings,
            "deprecated_fields": deprecated_found
        }

    def _validate_context_structure(self, context: Any, fragment_path: str) -> Dict[str, Any]:
        """Validate context object structure"""
        issues = []
        warnings = []

        if not isinstance(context, dict):
            issues.append(f"Context must be dictionary in {fragment_path}")
            return {"issues": issues, "warnings": warnings}

        for key, value in context.items():
            # Key must be string
            if not isinstance(key, str):
                issues.append(f"Context key must be string in {fragment_path}, got {type(key)}")

            # Value must be string, list of strings, or "*"
            if value == "*":
                continue  # Wildcard is valid
            elif isinstance(value, str):
                continue  # String is valid
            elif isinstance(value, list):
                if not all(isinstance(item, str) for item in value):
                    issues.append(f"Context list values must be strings in {fragment_path}")
            else:
                issues.append(
                    f"Context value must be string, list of strings, or '*' in {fragment_path}, "
                    f"got {type(value)}"
                )

        return {"issues": issues, "warnings": warnings}

    def validate_all_fragments(self, fragments_dir: Path) -> Dict[str, Any]:
        """
        Validate metadata for all fragments in directory
        
        Args:
            fragments_dir: Path to fragments directory
            
        Returns:
            Comprehensive validation result
        """
        all_issues = []
        all_warnings = []
        all_deprecated = []
        fragment_count = 0
        valid_fragments = 0

        if not fragments_dir.exists():
            return {
                "valid": False,
                "issues": [f"Fragments directory does not exist: {fragments_dir}"],
                "warnings": [],
                "deprecated_fields": [],
                "fragment_count": 0,
                "valid_fragments": 0
            }

        # Process all .md files
        for fragment_file in fragments_dir.rglob("*.md"):
            fragment_count += 1
            relative_path = str(fragment_file.relative_to(fragments_dir))

            try:
                content = fragment_file.read_text(encoding="utf-8")
                metadata = self._extract_metadata(content)

                validation = self.validate_fragment_metadata(metadata, relative_path)
                
                if validation["valid"]:
                    valid_fragments += 1
                
                all_issues.extend(validation["issues"])
                all_warnings.extend(validation["warnings"])
                all_deprecated.extend(validation["deprecated_fields"])

            except Exception as e:
                all_issues.append(f"Failed to process {relative_path}: {str(e)}")

        return {
            "valid": len(all_issues) == 0,
            "issues": all_issues,
            "warnings": all_warnings,
            "deprecated_fields": list(set(all_deprecated)),
            "fragment_count": fragment_count,
            "valid_fragments": valid_fragments
        }

    def _extract_metadata(self, content: str) -> Dict[str, Any]:
        """Extract metadata from fragment content"""
        metadata = {}
        
        if content.startswith("---"):
            end_pos = content.find("---", 3)
            if end_pos > 0:
                frontmatter = content[3:end_pos].strip()
                try:
                    metadata = yaml.safe_load(frontmatter) or {}
                except yaml.YAMLError:
                    pass
        
        return metadata


class FragmentSystemValidator:
    """Comprehensive validator for the entire fragment system"""

    def __init__(self, fragments_dir: Path):
        self.fragments_dir = Path(fragments_dir)
        self.structure_validator = FragmentStructureValidator(fragments_dir)
        self.metadata_validator = FragmentMetadataValidator()

    def validate_complete_system(self, template_content: Optional[str] = None) -> Dict[str, Any]:
        """
        Perform complete validation of fragment system
        
        Args:
            template_content: Optional base template content to validate references
            
        Returns:
            Comprehensive validation result
        """
        # Validate folder structure
        structure_result = self.structure_validator.validate_folder_structure()
        
        # Validate metadata
        metadata_result = self.metadata_validator.validate_all_fragments(self.fragments_dir)
        
        # Validate template references if provided
        template_result = None
        if template_content and structure_result["valid"]:
            template_result = self.structure_validator.validate_template_references(
                template_content, structure_result["groups"]
            )

        # Combine results
        all_issues = structure_result["issues"] + metadata_result["issues"]
        all_warnings = structure_result["warnings"] + metadata_result["warnings"]
        
        if template_result:
            all_issues.extend(template_result["issues"])
            all_warnings.extend(template_result["warnings"])

        return {
            "valid": len(all_issues) == 0,
            "issues": all_issues,
            "warnings": all_warnings,
            "structure": structure_result,
            "metadata": metadata_result,
            "template_references": template_result,
            "summary": {
                "total_groups": structure_result["total_groups"],
                "total_fragments": metadata_result["fragment_count"],
                "valid_fragments": metadata_result["valid_fragments"],
                "deprecated_fields_found": len(metadata_result["deprecated_fields"]) > 0
            }
        }