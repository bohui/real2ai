"""Advanced prompt templating with Jinja2 and custom filters"""

import logging
import re
from typing import Dict, Any, Optional, List, Callable, Union
from datetime import datetime, UTC
from pathlib import Path
from dataclasses import dataclass
from jinja2 import Environment, FileSystemLoader, meta, StrictUndefined
from jinja2.exceptions import TemplateError, UndefinedError

from .context import PromptContext
from .exceptions import PromptTemplateError
from .output_parser import BaseOutputParser, ParsingResult

logger = logging.getLogger(__name__)


@dataclass
class TemplateMetadata:
    """Metadata for a prompt template"""
    name: str
    version: str
    description: str
    required_variables: List[str]
    optional_variables: List[str] = None
    model_compatibility: List[str] = None
    max_tokens: Optional[int] = None
    temperature_range: tuple = (0.0, 1.0)
    created_at: datetime = None
    tags: List[str] = None
    output_parser_enabled: bool = False
    expects_structured_output: bool = False


class PromptTemplate:
    """Advanced prompt template with Jinja2 rendering and validation"""
    
    def __init__(
        self, 
        template_content: str, 
        metadata: TemplateMetadata,
        template_dir: Optional[Path] = None,
        output_parser: Optional[BaseOutputParser] = None
    ):
        self.content = template_content
        self.metadata = metadata
        self.template_dir = template_dir
        self.output_parser = output_parser
        
        # Update metadata if parser is provided
        if output_parser is not None:
            self.metadata.output_parser_enabled = True
            self.metadata.expects_structured_output = True
        
        # Set up Jinja2 environment
        if template_dir:
            self.env = Environment(
                loader=FileSystemLoader(str(template_dir)),
                undefined=StrictUndefined,
                trim_blocks=True,
                lstrip_blocks=True
            )
        else:
            self.env = Environment(undefined=StrictUndefined)
        
        # Add custom filters
        self._register_custom_filters()
        
        # Parse template
        try:
            self.template = self.env.from_string(template_content)
            self._analyze_template()
        except TemplateError as e:
            raise PromptTemplateError(
                f"Invalid template syntax: {str(e)}",
                prompt_id=metadata.name,
                details={"template_error": str(e)}
            )
    
    def render(self, context: PromptContext, **kwargs) -> str:
        """Render template with context and additional variables"""
        try:
            # Merge context with additional kwargs
            render_vars = context.to_dict()
            render_vars.update(kwargs)
            
            # Add helper functions
            render_vars['now'] = datetime.now(UTC)
            render_vars['format_currency'] = self._format_currency
            render_vars['format_date'] = self._format_date
            render_vars['extract_numbers'] = self._extract_numbers
            
            # Auto-inject format instructions if output parser is available
            if self.output_parser is not None:
                render_vars['format_instructions'] = self.output_parser.get_format_instructions()
                render_vars['expects_structured_output'] = True
                render_vars['output_format'] = self.output_parser.output_format.value
                
                logger.debug(f"Injected format instructions for {self.metadata.name}")
            else:
                render_vars['expects_structured_output'] = False
            
            # Validate required variables
            self._validate_variables(render_vars)
            
            # Render template
            rendered = self.template.render(**render_vars)
            
            # Post-process output
            rendered = self._post_process(rendered)
            
            return rendered
            
        except UndefinedError as e:
            missing_var = str(e).split("'")[1] if "'" in str(e) else "unknown"
            raise PromptTemplateError(
                f"Missing required variable: {missing_var}",
                prompt_id=self.metadata.name,
                details={"missing_variable": missing_var, "available_variables": list(render_vars.keys())}
            )
        except TemplateError as e:
            raise PromptTemplateError(
                f"Template rendering failed: {str(e)}",
                prompt_id=self.metadata.name,
                details={"template_error": str(e)}
            )
    
    def validate_context(self, context: PromptContext) -> List[str]:
        """Validate context against template requirements"""
        issues = []
        context_vars = context.to_dict()
        
        # Check required variables
        for var in self.metadata.required_variables:
            if var not in context_vars or context_vars[var] is None:
                issues.append(f"Missing required variable: {var}")
        
        # Check variable types if specified in metadata
        if hasattr(self.metadata, 'variable_types'):
            for var, expected_type in self.metadata.variable_types.items():
                if var in context_vars:
                    actual_value = context_vars[var]
                    if not isinstance(actual_value, expected_type):
                        issues.append(
                            f"Variable '{var}' should be {expected_type.__name__}, "
                            f"got {type(actual_value).__name__}"
                        )
        
        return issues
    
    def parse_output(self, ai_response: str, use_retry: bool = True) -> Union[ParsingResult, str]:
        """Parse AI response using configured output parser
        
        Args:
            ai_response: Raw AI response text
            use_retry: Whether to use retry mechanism for parsing failures
            
        Returns:
            ParsingResult if parser is configured, otherwise returns raw response
        """
        if self.output_parser is None:
            logger.debug(f"No output parser configured for template {self.metadata.name}")
            return ai_response
        
        try:
            if use_retry:
                result = self.output_parser.parse_with_retry(ai_response)
            else:
                result = self.output_parser.parse(ai_response)
            
            if result.success:
                logger.debug(f"Successfully parsed output for template {self.metadata.name}")
            else:
                logger.warning(
                    f"Failed to parse output for template {self.metadata.name}: "
                    f"parsing_errors={result.parsing_errors}, validation_errors={result.validation_errors}"
                )
            
            return result
            
        except Exception as e:
            logger.error(f"Unexpected error parsing output for template {self.metadata.name}: {e}")
            # Return failed parsing result
            return ParsingResult(
                success=False,
                raw_output=ai_response,
                parsing_errors=[f"Unexpected error: {str(e)}"]
            )
    
    def set_output_parser(self, parser: BaseOutputParser) -> None:
        """Set or update the output parser for this template
        
        Args:
            parser: Output parser instance
        """
        self.output_parser = parser
        self.metadata.output_parser_enabled = True
        self.metadata.expects_structured_output = True
        
        logger.debug(f"Set output parser for template {self.metadata.name}")
    
    def get_estimated_tokens(self, context: PromptContext) -> int:
        """Estimate token count for rendered template"""
        try:
            rendered = self.render(context)
            # Rough estimation: ~4 characters per token
            return len(rendered) // 4
        except Exception as e:
            logger.warning(f"Could not estimate tokens for template {self.metadata.name}: {e}")
            return self.metadata.max_tokens or 1000
    
    def _register_custom_filters(self):
        """Register custom Jinja2 filters for Australian legal context"""
        
        def currency_filter(value):
            """Format currency as AUD"""
            if isinstance(value, (int, float)):
                return f"${value:,.2f}"
            return str(value)
        
        def legal_format(text):
            """Format text for legal documents"""
            if not isinstance(text, str):
                return str(text)
            # Convert to proper case, handle abbreviations
            return text.title().replace("Nsw", "NSW").replace("Vic", "VIC").replace("Qld", "QLD")
        
        def extract_price(text):
            """Extract price from text"""
            if not isinstance(text, str):
                return None
            price_match = re.search(r'\$([\d,]+(?:\.\d{2})?)', text)
            if price_match:
                return float(price_match.group(1).replace(',', ''))
            return None
        
        def australian_date(date_obj):
            """Format date in Australian format (DD/MM/YYYY)"""
            if isinstance(date_obj, datetime):
                return date_obj.strftime("%d/%m/%Y")
            return str(date_obj)
        
        def business_days(days):
            """Convert days to business days context"""
            if isinstance(days, int):
                return f"{days} business day{'s' if days != 1 else ''}"
            return str(days)
        
        def state_specific(value, state):
            """Apply state-specific formatting"""
            state_formats = {
                "NSW": lambda x: f"{x} (NSW)",
                "VIC": lambda x: f"{x} (Victoria)",
                "QLD": lambda x: f"{x} (Queensland)",
            }
            formatter = state_formats.get(state, lambda x: str(x))
            return formatter(value)
        
        # Register filters
        self.env.filters['currency'] = currency_filter
        self.env.filters['legal_format'] = legal_format
        self.env.filters['extract_price'] = extract_price
        self.env.filters['australian_date'] = australian_date
        self.env.filters['business_days'] = business_days
        self.env.filters['state_specific'] = state_specific
    
    def _analyze_template(self):
        """Analyze template to extract variable requirements"""
        try:
            # Parse template to find undefined variables
            parsed = self.env.parse(self.content)
            undefined_vars = meta.find_undeclared_variables(parsed)
            
            # Update metadata if not already specified
            if not self.metadata.required_variables:
                self.metadata.required_variables = list(undefined_vars)
            
            logger.debug(
                f"Template {self.metadata.name} analysis: "
                f"found {len(undefined_vars)} variables: {list(undefined_vars)}"
            )
            
        except Exception as e:
            logger.warning(f"Could not analyze template {self.metadata.name}: {e}")
    
    def _validate_variables(self, render_vars: Dict[str, Any]):
        """Validate that all required variables are present"""
        missing = []
        for var in self.metadata.required_variables:
            if var not in render_vars or render_vars[var] is None:
                missing.append(var)
        
        if missing:
            raise PromptTemplateError(
                f"Missing required variables: {', '.join(missing)}",
                prompt_id=self.metadata.name,
                details={"missing_variables": missing}
            )
    
    def _post_process(self, rendered: str) -> str:
        """Post-process rendered template"""
        # Remove excessive whitespace
        rendered = re.sub(r'\n\s*\n\s*\n', '\n\n', rendered)
        rendered = rendered.strip()
        
        # Ensure proper formatting for JSON blocks
        rendered = re.sub(r'```json\s*\n', '```json\n', rendered)
        
        return rendered
    
    def _format_currency(self, value: Any) -> str:
        """Helper function for currency formatting"""
        if isinstance(value, (int, float)):
            return f"${value:,.2f}"
        return str(value)
    
    def _format_date(self, date_obj: Any, format_str: str = "%d/%m/%Y") -> str:
        """Helper function for date formatting"""
        if isinstance(date_obj, datetime):
            return date_obj.strftime(format_str)
        return str(date_obj)
    
    def _extract_numbers(self, text: str) -> List[float]:
        """Helper function to extract numbers from text"""
        if not isinstance(text, str):
            return []
        
        # Find all numbers including currency
        numbers = re.findall(r'[\d,]+(?:\.\d{2})?', text.replace('$', ''))
        return [float(num.replace(',', '')) for num in numbers]


class TemplateLibrary:
    """Library for managing multiple templates"""
    
    def __init__(self, template_dir: Path):
        self.template_dir = Path(template_dir)
        self.templates: Dict[str, PromptTemplate] = {}
        self._load_templates()
    
    def _load_templates(self):
        """Load all templates from directory"""
        if not self.template_dir.exists():
            logger.warning(f"Template directory does not exist: {self.template_dir}")
            return
        
        for template_file in self.template_dir.rglob("*.md"):
            try:
                self._load_template_file(template_file)
            except Exception as e:
                logger.error(f"Failed to load template {template_file}: {e}")
    
    def _load_template_file(self, template_file: Path):
        """Load a single template file"""
        content = template_file.read_text(encoding='utf-8')
        
        # Parse frontmatter for metadata
        metadata = self._parse_frontmatter(content)
        template_content = self._extract_template_content(content)
        
        # Create template
        template = PromptTemplate(
            template_content=template_content,
            metadata=metadata,
            template_dir=self.template_dir
        )
        
        self.templates[metadata.name] = template
        logger.debug(f"Loaded template: {metadata.name} from {template_file}")
    
    def _parse_frontmatter(self, content: str) -> TemplateMetadata:
        """Parse YAML frontmatter from template file"""
        import yaml
        
        if content.startswith('---'):
            end_pos = content.find('---', 3)
            if end_pos > 0:
                frontmatter = content[3:end_pos].strip()
                try:
                    metadata_dict = yaml.safe_load(frontmatter)
                    return TemplateMetadata(
                        name=metadata_dict['name'],
                        version=metadata_dict.get('version', '1.0'),
                        description=metadata_dict.get('description', ''),
                        required_variables=metadata_dict.get('required_variables', []),
                        optional_variables=metadata_dict.get('optional_variables', []),
                        model_compatibility=metadata_dict.get('model_compatibility', []),
                        max_tokens=metadata_dict.get('max_tokens'),
                        temperature_range=tuple(metadata_dict.get('temperature_range', [0.0, 1.0])),
                        tags=metadata_dict.get('tags', [])
                    )
                except yaml.YAMLError as e:
                    logger.error(f"Invalid YAML frontmatter: {e}")
        
        # Fallback metadata
        return TemplateMetadata(
            name="unknown",
            version="1.0",
            description="No metadata provided",
            required_variables=[]
        )
    
    def _extract_template_content(self, content: str) -> str:
        """Extract template content after frontmatter"""
        if content.startswith('---'):
            end_pos = content.find('---', 3)
            if end_pos > 0:
                return content[end_pos + 3:].strip()
        return content
    
    def get(self, name: str) -> Optional[PromptTemplate]:
        """Get template by name"""
        return self.templates.get(name)
    
    def list_templates(self) -> List[str]:
        """List all available template names"""
        return list(self.templates.keys())
    
    def find_by_tags(self, tags: List[str]) -> List[PromptTemplate]:
        """Find templates by tags"""
        matching = []
        for template in self.templates.values():
            if template.metadata.tags and any(tag in template.metadata.tags for tag in tags):
                matching.append(template)
        return matching
