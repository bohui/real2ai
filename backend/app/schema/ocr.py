"""OCR processing schemas."""

from typing import Dict, List, Any, Optional
from pydantic import BaseModel, field_validator
from datetime import datetime

from app.model.enums import ContractType


class OCRCapabilitiesResponse(BaseModel):
    """OCR service capabilities response"""
    service_available: bool
    model_name: Optional[str] = None
    supported_formats: List[str] = []
    max_file_size_mb: float = 0.0
    features: List[str] = []
    reason: Optional[str] = None  # If service unavailable


class OCRProcessingRequest(BaseModel):
    """OCR processing request"""
    document_id: str
    force_reprocess: bool = False
    australian_context: Optional[Dict[str, Any]] = None


class OCRProcessingResponse(BaseModel):
    """OCR processing response"""
    message: str
    document_id: str
    estimated_completion_minutes: int
    processing_started: bool = True


class OCRExtractionResult(BaseModel):
    """OCR text extraction result"""
    extracted_text: str
    extraction_method: str
    extraction_confidence: float
    character_count: int
    word_count: int
    extraction_timestamp: datetime
    file_processed: str
    processing_details: Optional[Dict[str, Any]] = None
    enhancements_applied: List[str] = []
    contract_terms_found: int = 0


class BatchOCRRequest(BaseModel):
    """Batch OCR processing request"""
    document_ids: List[str]
    contract_type: Optional[ContractType] = ContractType.PURCHASE_AGREEMENT
    processing_priority: str = "standard"  # standard, priority
    include_analysis: bool = True
    batch_options: Optional[Dict[str, Any]] = None
    
    @field_validator('document_ids')
    @classmethod
    def validate_document_ids(cls, v):
        if not v or len(v) == 0:
            raise ValueError('At least one document ID is required')
        if len(v) > 20:  # Limit batch size
            raise ValueError('Maximum 20 documents per batch')
        return v
    
    @field_validator('processing_priority')
    @classmethod
    def validate_priority(cls, v):
        if v not in ['standard', 'priority', 'express']:
            raise ValueError('Priority must be standard, priority, or express')
        return v


class BatchOCRResponse(BaseModel):
    """Batch OCR processing response"""
    message: str
    batch_id: str
    documents_queued: int
    estimated_completion_minutes: int
    processing_features: List[str]
    queue_position: Optional[int] = None


class OCRStatusResponse(BaseModel):
    """Detailed OCR processing status response"""
    document_id: str
    filename: str
    status: str  # queued_for_ocr, processing_ocr, processed, ocr_failed
    processing_metrics: Dict[str, Any]
    ocr_features_used: List[str]
    last_updated: Optional[datetime] = None
    supports_reprocessing: bool = True
    task_id: Optional[str] = None
    progress_percent: Optional[int] = None
    current_step: Optional[str] = None
    estimated_time_remaining: Optional[int] = None


class EnhancedOCRCapabilities(BaseModel):
    """Enhanced OCR capabilities with Gemini 2.5 Pro features"""
    service_available: bool
    model_name: str = "gemini-2.5-pro"
    supported_formats: List[str]
    max_file_size_mb: float
    features: List[str]
    gemini_features: Dict[str, bool]
    processing_tiers: Dict[str, Dict[str, Any]]
    api_health: Dict[str, Any]
    queue_status: Optional[Dict[str, Any]] = None


class GeminiOCRResult(BaseModel):
    """Enhanced OCR result from Gemini 2.5 Pro"""
    extracted_text: str
    extraction_method: str = "gemini_2.5_pro_ocr"
    extraction_confidence: float
    document_type: str = "unknown"
    key_sections: Dict[str, str]
    australian_state_indicators: List[str]
    extraction_quality: Dict[str, Any]
    warnings: List[str]
    character_count: int
    word_count: int
    pages_processed: Optional[int] = None
    processing_time_seconds: Optional[float] = None
    contract_analysis: Optional[Dict[str, Any]] = None
    priority_analysis: Optional[Dict[str, Any]] = None


class OCRQueueStatus(BaseModel):
    """OCR processing queue status"""
    queue_position: int
    estimated_wait_time_minutes: int
    active_workers: int
    queue_length: int
    user_priority: str  # standard, priority, express
    processing_capacity: Dict[str, Any]
    current_load: float  # 0.0 - 1.0


class OCRProcessingOptions(BaseModel):
    """Advanced OCR processing options"""
    priority: bool = False
    enhanced_quality: bool = True
    detailed_analysis: bool = False
    contract_specific: bool = True
    include_contract_analysis: bool = True
    australian_context: Optional[Dict[str, Any]] = None
    quality_threshold: float = 0.7
    retry_on_low_confidence: bool = True


class OCRCostEstimate(BaseModel):
    """OCR processing cost estimate"""
    estimated_cost_usd: float
    estimated_time_seconds: int
    complexity_factor: float
    file_size_mb: float
    processing_tier: str
    features_included: List[str]


class OCRProgressUpdate(BaseModel):
    """OCR processing progress update via WebSocket"""
    document_id: str
    task_id: Optional[str] = None
    current_step: str
    progress_percent: int
    step_description: str
    estimated_completion: Optional[str] = None
    processing_features: List[str]


class BatchOCRProgressUpdate(BaseModel):
    """Batch OCR processing progress update"""
    batch_id: str
    completed: int
    total: int
    progress_percent: int
    current_document: Optional[str] = None
    failed_count: int = 0
    estimated_completion: Optional[str] = None


class OCRCompletionNotification(BaseModel):
    """OCR processing completion notification"""
    document_id: str
    task_id: Optional[str] = None
    extraction_confidence: float
    character_count: int
    word_count: int
    processing_method: str
    quality_score: str
    contract_elements_found: int


class OCRErrorNotification(BaseModel):
    """OCR processing error notification"""
    document_id: str
    task_id: Optional[str] = None
    error_message: str
    error_type: str
    retry_available: bool
    support_contact: Optional[str] = None