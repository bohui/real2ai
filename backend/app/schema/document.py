"""Document-related schemas."""

from typing import Dict, List, Any, Optional, Union
from pydantic import BaseModel, Field
from datetime import datetime

from app.prompts.schema.image_semantics_schema import ImageType


class SchemaBase(BaseModel):
    def get(self, key: str, default: Any = None) -> Any:
        return getattr(self, key, default)


class DocumentUploadResponse(SchemaBase):
    """Document upload response"""

    document_id: str
    filename: str
    file_size: int
    upload_status: str = "uploaded"
    processing_time: float = 0.0


class DocumentDetails(SchemaBase):
    """Document details response"""

    id: str
    user_id: str
    filename: str
    file_type: str
    file_size: int
    status: str  # uploaded, processing, processed, failed
    storage_path: str
    created_at: datetime
    processing_results: Optional[Dict[str, Any]] = None


class DocumentProcessingStatus(SchemaBase):
    """Enhanced document processing status with OCR details"""

    document_id: str
    status: str  # uploaded, processing, processed, reprocessing_ocr, ocr_failed, failed
    extraction_confidence: float
    extraction_method: str
    ocr_recommended: bool = False
    ocr_available: bool = False
    processing_results: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime


class LayoutFeatures(SchemaBase):
    has_header: bool = False
    has_footer: bool = False
    has_signatures: bool = False
    has_diagrams: bool = False
    has_tables: bool = False


class QualityIndicators(SchemaBase):
    structure_score: float = 0.0
    readability_score: float = 0.0


class ContentAnalysis(SchemaBase):
    content_types: List[str] = Field(default_factory=list)
    primary_type: str = "unknown"
    layout_features: LayoutFeatures = Field(default_factory=LayoutFeatures)
    quality_indicators: QualityIndicators = Field(default_factory=QualityIndicators)
    diagram_type: Optional[str] = None


class PageExtraction(SchemaBase):
    page_number: int
    text_content: str = ""
    text_length: int = 0
    word_count: int = 0
    extraction_method: Optional[str] = None
    confidence: float = 0.0
    content_analysis: ContentAnalysis = Field(default_factory=ContentAnalysis)


class TextExtractionResult(SchemaBase):
    success: bool = True
    error: Optional[str] = None
    full_text: str = ""
    pages: List[PageExtraction] = Field(default_factory=list)
    extraction_methods: Optional[List[str]] = None
    extraction_method: Optional[str] = None
    confidence: Optional[float] = None
    # Optional aggregate fields for comprehensive extraction flows
    total_pages: Optional[int] = None
    total_word_count: Optional[int] = None
    overall_confidence: Optional[float] = None
    processing_time: float = 0.0


class DiagramPageSummary(SchemaBase):
    page_number: int
    content_types: List[str] = Field(default_factory=list)
    primary_type: str = "unknown"
    confidence: float = 0.0


class DiagramProcessingResult(SchemaBase):
    total_diagrams: int = 0
    diagram_pages: List[DiagramPageSummary] = Field(default_factory=list)
    diagram_types: Dict[str, int] = Field(default_factory=dict)
    detection_summary: Dict[str, Union[int, str]] = Field(default_factory=dict)
    processing_notes: Optional[List[str]] = Field(default_factory=list)

    # Additional fields used by nodes
    success: Optional[bool] = None
    diagrams: Optional[List[Any]] = Field(
        default_factory=list, description="Raw diagram detection items"
    )
    pages_processed: Optional[List[int]] = Field(
        default_factory=list, description="List of page numbers that were processed"
    )
    processing_timestamp: Optional[str] = None


class DocumentProcessingSummary(SchemaBase):
    total_pages: int
    total_diagrams: int
    extraction_methods: List[str] = Field(default_factory=list)
    avg_confidence: float


class ProcessingResults(SchemaBase):
    text_extraction: Optional[TextExtractionResult] = None
    diagram_processing: Optional[DiagramProcessingResult] = None
    processing_summary: Optional[DocumentProcessingSummary] = None


class DocumentProcessingUpdate(SchemaBase):
    """Strongly-typed payload for updating `documents` with processing metrics."""

    total_pages: int
    total_word_count: int
    total_text_length: int
    has_diagrams: bool
    diagram_count: int
    extraction_confidence: float
    overall_quality_score: float
    text_extraction_method: Optional[str] = None
    processing_completed_at: datetime
    processing_results: ProcessingResults


class ReportGenerationRequest(SchemaBase):
    """Report generation request"""

    contract_id: str
    format: str = "pdf"  # pdf, html, json
    include_sections: List[str] = [
        "executive_summary",
        "risk_assessment",
        "compliance_check",
        "recommendations",
    ]
    custom_branding: bool = False


class ReportResponse(SchemaBase):
    """Report response"""

    report_id: str
    download_url: str
    format: str
    file_size: int
    expires_at: datetime


# ========== Service return schemas for DocumentService ==========


class UploadedFileInfo(SchemaBase):
    original_filename: str
    file_type: str
    file_size: int
    content_hash: str
    mime_type: str


class FileValidationResult(SchemaBase):
    valid: bool
    error: Optional[str] = None
    file_info: Optional[UploadedFileInfo] = None


class UploadRecordResult(SchemaBase):
    success: bool
    document_id: Optional[str] = None
    storage_path: Optional[str] = None
    error: Optional[str] = None


class FastUploadResult(SchemaBase):
    success: bool
    document_id: Optional[str] = None
    storage_path: Optional[str] = None
    processing_time: float = 0.0
    status: str = "uploaded"
    error: Optional[str] = None


class ProcessedDocumentSummary(SchemaBase):
    success: bool
    document_id: str
    australian_state: str

    # Primary fields used by services and background tasks
    full_text: Optional[str] = None
    total_word_count: Optional[int] = None
    total_pages: Optional[int] = None
    character_count: int = 0
    extraction_method: Optional[str] = None
    extraction_confidence: float = 0.0
    processing_timestamp: str
    llm_used: bool = False

    # Optional metadata commonly needed downstream
    original_filename: Optional[str] = None
    filename: Optional[str] = None
    file_type: Optional[str] = None
    storage_path: Optional[str] = None
    content_hash: Optional[str] = None


class TextExtractionOverview(SchemaBase):
    total_pages: int = 0
    total_word_count: int = 0
    extraction_methods: List[str] = Field(default_factory=list)
    overall_confidence: float = 0.0


class ContentAnalysisOverview(SchemaBase):
    pages_analyzed: int = 0
    entities_extracted: int = 0
    diagrams_detected: int = 0
    document_classification: Dict[str, Any] = Field(default_factory=dict)


class ProcessingSuccessResponse(SchemaBase):
    success: bool = True
    document_id: str
    processing_time: float
    processing_timestamp: str
    text_extraction: TextExtractionOverview
    content_analysis: ContentAnalysisOverview


class ProcessingErrorResponse(SchemaBase):
    success: bool = False
    error: str
    processing_time: float
    processing_timestamp: str
    recovery_suggestions: List[str] = Field(default_factory=list)


class ProcessingSummaryBreakdown(SchemaBase):
    text_pages: int = 0
    diagram_pages: int = 0
    mixed_pages: int = 0
    table_pages: int = 0
    signature_pages: int = 0
    empty_pages: int = 0


class PageProcessingSummary(SchemaBase):
    pages: List[PageExtraction] = Field(default_factory=list)
    total_pages_processed: int = 0
    content_type_distribution: Dict[str, int] = Field(default_factory=dict)
    average_confidence: float = 0.0
    processing_summary: ProcessingSummaryBreakdown = Field(
        default_factory=ProcessingSummaryBreakdown
    )


class ServiceHealthStatus(SchemaBase):
    service: str
    status: str
    authenticated: bool
    dependencies: Dict[str, Any] = Field(default_factory=dict)
    capabilities: List[str] = Field(default_factory=list)


class SystemStatsResponse(SchemaBase):
    data: Dict[str, Any] = Field(default_factory=dict)
