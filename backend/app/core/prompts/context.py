"""Prompt context management with intelligent variable resolution"""

import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime, UTC
from enum import Enum

from app.schema import AustralianState
from app.schema.enums.property import (
    ContractType,
    PropertyType,
    PurchaseMethod,
    UseCategory,
    DocumentType,
    DocumentStatus,
    ProcessingStatus,
)
from .exceptions import PromptContextError

logger = logging.getLogger(__name__)


class ContextType(Enum):
    """Types of prompt contexts"""

    SYSTEM = "system"
    USER = "user"
    CONTRACT = "contract"
    ANALYSIS = "analysis"
    CONTRACT_ANALYSIS = "contract_analysis"
    OCR = "ocr"
    COMPLIANCE = "compliance"
    RISK = "risk"
    FINANCIAL = "financial"
    RECOMMENDATION = "recommendation"
    VALIDATION = "validation"
    EXTRACTION = "extraction"
    GENERATION = "generation"


@dataclass
class PromptContext:
    """Context container for prompt variable resolution"""

    context_type: ContextType
    variables: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    # Australian-specific context
    australian_state: Optional[AustralianState] = None
    contract_type: Optional[ContractType] = None

    # Property/transaction context (new enums)
    property_type: Optional[PropertyType] = None
    purchase_method: Optional[PurchaseMethod] = None
    use_category: Optional[UseCategory] = None

    # User context
    user_id: Optional[str] = None
    user_type: Optional[str] = None  # buyer, seller, investor, etc.
    user_experience: Optional[str] = None  # novice, intermediate, expert

    # Document context
    document_id: Optional[str] = None
    document_type: Optional[str] = None
    ocr_processing: Dict[str, Any] = field(default_factory=dict)
    # New document/processing enums (kept separate for backward compatibility)
    document_type_enum: Optional[DocumentType] = None
    document_status: Optional[DocumentStatus] = None
    processing_status: Optional[ProcessingStatus] = None

    # Processing context
    processing_priority: Optional[str] = None
    analysis_depth: Optional[str] = None
    focus_areas: List[str] = field(default_factory=list)

    def __post_init__(self):
        """Validate and ensure proper types for critical fields"""
        # Ensure variables is always a dictionary
        if not isinstance(self.variables, dict):
            logger.warning(
                f"PromptContext variables expected dict, got {type(self.variables)}. Converting to empty dict."
            )
            self.variables = {}

        # Ensure metadata is always a dictionary
        if not isinstance(self.metadata, dict):
            logger.warning(
                f"PromptContext metadata expected dict, got {type(self.metadata)}. Converting to empty dict."
            )
            self.metadata = {}

        # Ensure ocr_processing is always a dictionary
        if not isinstance(self.ocr_processing, dict):
            logger.warning(
                f"PromptContext ocr_processing expected dict, got {type(self.ocr_processing)}. Converting to empty dict."
            )
            self.ocr_processing = {}

        # Ensure focus_areas is always a list
        if not isinstance(self.focus_areas, list):
            logger.warning(
                f"PromptContext focus_areas expected list, got {type(self.focus_areas)}. Converting to empty list."
            )
            self.focus_areas = []

    def get(self, key: str, default: Any = None) -> Any:
        """Get variable with dot notation support"""
        return self._get_nested(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set variable with dot notation support"""
        self._set_nested(key, value)

    def merge(self, other: "PromptContext") -> "PromptContext":
        """Merge with another context, returning new instance"""
        merged_variables = {**self.variables, **other.variables}
        merged_metadata = {**self.metadata, **other.metadata}

        return PromptContext(
            context_type=self.context_type,
            variables=merged_variables,
            metadata=merged_metadata,
            australian_state=other.australian_state or self.australian_state,
            contract_type=other.contract_type or self.contract_type,
            user_id=other.user_id or self.user_id,
            user_type=other.user_type or self.user_type,
            user_experience=other.user_experience or self.user_experience,
            document_id=other.document_id or self.document_id,
            document_type=other.document_type or self.document_type,
            ocr_processing={**self.ocr_processing, **other.ocr_processing},
            processing_priority=other.processing_priority or self.processing_priority,
            analysis_depth=other.analysis_depth or self.analysis_depth,
            focus_areas=list(set(self.focus_areas + other.focus_areas)),
        )

    def validate_required(self, required_vars: List[str]) -> None:
        """Validate that all required variables are present"""
        missing = []
        for var in required_vars:
            if self.get(var) is None:
                missing.append(var)

        if missing:
            raise PromptContextError(
                f"Missing required context variables: {', '.join(missing)}",
                details={
                    "missing_variables": missing,
                    "available_variables": list(self.variables.keys()),
                },
            )

    def to_dict(self) -> Dict[str, Any]:
        """Convert context to dictionary for template rendering"""
        result = {
            **self.variables,
            "context_type": self.context_type.value,
            "created_at": self.created_at.isoformat(),
            "metadata": self.metadata,
        }

        # Add structured fields
        if self.australian_state:
            result["australian_state"] = self.australian_state.value
        if self.contract_type:
            result["contract_type"] = self.contract_type.value
        if self.property_type:
            result["property_type"] = self.property_type.value
        if self.purchase_method:
            result["purchase_method"] = self.purchase_method.value
        if self.use_category:
            result["use_category"] = self.use_category.value
        if self.user_id:
            result["user_id"] = self.user_id
        if self.user_type:
            result["user_type"] = self.user_type
        if self.user_experience:
            result["user_experience"] = self.user_experience
        if self.document_id:
            result["document_id"] = self.document_id
        if self.document_type:
            result["document_type"] = self.document_type
        if self.document_type_enum:
            result["document_type_enum"] = self.document_type_enum.value
        if self.document_status:
            result["document_status"] = self.document_status.value
        if self.processing_status:
            result["processing_status"] = self.processing_status.value
        if self.ocr_processing:
            result["ocr_processing"] = self.ocr_processing
        if self.processing_priority:
            result["processing_priority"] = self.processing_priority
        if self.analysis_depth:
            result["analysis_depth"] = self.analysis_depth
        if self.focus_areas:
            result["focus_areas"] = self.focus_areas

        return result

    def _get_nested(self, key: str, default: Any = None) -> Any:
        """Get nested value using dot notation"""
        keys = key.split(".")
        value = self.variables

        try:
            for k in keys:
                if isinstance(value, dict):
                    value = value[k]
                else:
                    return default
            return value
        except (KeyError, TypeError):
            return default

    def _set_nested(self, key: str, value: Any) -> None:
        """Set nested value using dot notation"""
        keys = key.split(".")
        target = self.variables

        for k in keys[:-1]:
            if k not in target:
                target[k] = {}
            target = target[k]

        target[keys[-1]] = value


class ContextBuilder:
    """Builder for creating prompt contexts"""

    def __init__(self, context_type: ContextType):
        self._context = PromptContext(context_type=context_type)

    def with_contract_context(
        self,
        australian_state: Optional[AustralianState] = None,
        contract_type: Optional[ContractType] = None,
        property_type: Optional[PropertyType] = None,
        purchase_method: Optional[PurchaseMethod] = None,
        use_category: Optional[UseCategory] = None,
    ) -> "ContextBuilder":
        """Add or update contract-related context.

        Any parameter left as None is ignored (existing value preserved).
        """
        if australian_state is not None:
            self._context.australian_state = australian_state
        if contract_type is not None:
            self._context.contract_type = contract_type
        if property_type is not None:
            self._context.property_type = property_type
        if purchase_method is not None:
            self._context.purchase_method = purchase_method
        if use_category is not None:
            self._context.use_category = use_category
        return self

    def with_variable(self, key: str, value: Any) -> "ContextBuilder":
        """Add a variable to the context"""
        self._context.set(key, value)
        return self

    def with_variables(self, variables: Dict[str, Any]) -> "ContextBuilder":
        """Add multiple variables to the context"""
        self._context.variables.update(variables)
        return self

    def with_metadata(self, key: str, value: Any) -> "ContextBuilder":
        """Add metadata to the context"""
        self._context.metadata[key] = value
        return self

    def with_australian_context(
        self, state: AustralianState, contract_type: ContractType
    ) -> "ContextBuilder":
        """Deprecated: use with_contract_context instead."""
        return self.with_contract_context(
            australian_state=state, contract_type=contract_type
        )

    def with_user_context(
        self, user_id: str, user_type: str, experience: str
    ) -> "ContextBuilder":
        """Add user context"""
        self._context.user_id = user_id
        self._context.user_type = user_type
        self._context.user_experience = experience
        return self

    def with_document_context(
        self, doc_id: str, doc_type: str, metadata: Dict[str, Any] = None
    ) -> "ContextBuilder":
        """Add document context"""
        self._context.document_id = doc_id
        self._context.document_type = doc_type
        if metadata:
            self._context.ocr_processing.update(metadata)
        return self

    def with_processing_context(
        self, priority: str, depth: str, focus_areas: List[str] = None
    ) -> "ContextBuilder":
        """Add processing context"""
        self._context.processing_priority = priority
        self._context.analysis_depth = depth
        if focus_areas:
            self._context.focus_areas.extend(focus_areas)
        return self

    def build(self) -> PromptContext:
        """Build the final context"""
        return self._context


class ContextPresets:
    """Predefined context presets for common use cases"""

    @staticmethod
    def contract_analysis(
        australian_state: AustralianState,
        contract_type: ContractType,
        *,
        property_type: Optional[PropertyType] = None,
        purchase_method: Optional[PurchaseMethod] = None,
        use_category: Optional[UseCategory] = None,
        user_type: str = "buyer",
        experience: str = "novice",
    ) -> PromptContext:
        """Create context for contract analysis"""
        return (
            ContextBuilder(ContextType.ANALYSIS)
            .with_contract_context(
                australian_state=australian_state,
                contract_type=contract_type,
                property_type=property_type,
                purchase_method=purchase_method,
                use_category=use_category,
            )
            .with_user_context("default", user_type, experience)
            .with_processing_context("standard", "comprehensive")
            .build()
        )

    @staticmethod
    def ocr_extraction(
        document_type: str = "contract",
        quality: str = "high",
        australian_state: AustralianState = AustralianState.NSW,
    ) -> PromptContext:
        """Create context for OCR text extraction"""
        return (
            ContextBuilder(ContextType.OCR)
            .with_variable("document_type", document_type)
            .with_variable("quality_requirements", quality)
            .with_variable("australian_state", australian_state.value)
            .with_processing_context("high", "detailed")
            .build()
        )

    @staticmethod
    def risk_assessment(
        contract_type: ContractType,
        user_experience: str = "novice",
        focus_areas: List[str] = None,
    ) -> PromptContext:
        """Create context for risk assessment"""
        return (
            ContextBuilder(ContextType.RISK)
            .with_variable("contract_type", contract_type.value)
            .with_variable("user_experience", user_experience)
            .with_processing_context("critical", "comprehensive", focus_areas or [])
            .build()
        )

    @staticmethod
    def compliance_check(
        australian_state: AustralianState,
        contract_type: ContractType,
        *,
        property_type: Optional[PropertyType] = None,
        purchase_method: Optional[PurchaseMethod] = None,
        use_category: Optional[UseCategory] = None,
    ) -> PromptContext:
        """Create context for compliance checking"""
        return (
            ContextBuilder(ContextType.COMPLIANCE)
            .with_contract_context(
                australian_state=australian_state,
                contract_type=contract_type,
                property_type=property_type,
                purchase_method=purchase_method,
                use_category=use_category,
            )
            .with_processing_context("critical", "detailed")
            .build()
        )
