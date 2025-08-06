"""Document-related schemas."""

from typing import Dict, List, Any, Optional
from pydantic import BaseModel
from datetime import datetime


class DocumentUploadResponse(BaseModel):
    """Document upload response"""

    document_id: str
    filename: str
    file_size: int
    upload_status: str = "uploaded"
    processing_time: float = 0.0


class DocumentDetails(BaseModel):
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


class DocumentProcessingStatus(BaseModel):
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


class ReportGenerationRequest(BaseModel):
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


class ReportResponse(BaseModel):
    """Report response"""

    report_id: str
    download_url: str
    format: str
    file_size: int
    expires_at: datetime
