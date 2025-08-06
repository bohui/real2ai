"""
Document Processing Models for Fresh Architecture
Database models for document metadata, pages, entities, and diagrams
"""

from sqlalchemy import Column, String, Integer, Float, Text, JSON, DateTime, Boolean, ForeignKey, ARRAY
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime, UTC
from typing import Dict, Any, List, Optional
from enum import Enum
import uuid

Base = declarative_base()


class ProcessingStatus(str, Enum):
    """Document processing status"""
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    BASIC_COMPLETE = "basic_complete"
    ANALYSIS_PENDING = "analysis_pending"
    ANALYSIS_COMPLETE = "analysis_complete"
    FAILED = "failed"


class ContentType(str, Enum):
    """Page content types"""
    TEXT = "text"
    DIAGRAM = "diagram"
    TABLE = "table"
    SIGNATURE = "signature"
    MIXED = "mixed"
    EMPTY = "empty"


class DiagramType(str, Enum):
    """Diagram classification types"""
    SITE_PLAN = "site_plan"
    SEWER_DIAGRAM = "sewer_diagram"
    FLOOD_MAP = "flood_map"
    BUSHFIRE_MAP = "bushfire_map"
    TITLE_PLAN = "title_plan"
    SURVEY_DIAGRAM = "survey_diagram"
    FLOOR_PLAN = "floor_plan"
    ELEVATION = "elevation"
    UNKNOWN = "unknown"


class EntityType(str, Enum):
    """Basic entity types for document processing"""
    ADDRESS = "address"
    PROPERTY_REFERENCE = "property_reference"
    DATE = "date"
    FINANCIAL_AMOUNT = "financial_amount"
    PARTY_NAME = "party_name"
    LEGAL_REFERENCE = "legal_reference"
    CONTACT_INFO = "contact_info"
    PROPERTY_DETAILS = "property_details"


class Document(Base):
    """Main document record"""
    __tablename__ = "documents"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String(255), nullable=False, index=True)
    
    # File metadata
    original_filename = Column(String(512), nullable=False)
    file_type = Column(String(50), nullable=False)
    storage_path = Column(String(1024), nullable=False)
    file_size = Column(Integer, nullable=False)
    
    # Processing metadata
    upload_timestamp = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    processing_status = Column(String(50), default=ProcessingStatus.UPLOADED.value, index=True)
    processing_started_at = Column(DateTime(timezone=True), nullable=True)
    processing_completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Quality metrics
    overall_quality_score = Column(Float, default=0.0)
    extraction_confidence = Column(Float, default=0.0)
    text_extraction_method = Column(String(100), nullable=True)
    
    # Document characteristics
    total_pages = Column(Integer, default=0)
    total_text_length = Column(Integer, default=0)
    total_word_count = Column(Integer, default=0)
    has_diagrams = Column(Boolean, default=False)
    diagram_count = Column(Integer, default=0)
    
    # Analysis metadata
    document_type = Column(String(100), nullable=True)  # contract, lease, etc.
    australian_state = Column(String(10), nullable=True)
    contract_type = Column(String(100), nullable=True)
    
    # Processing errors and notes
    processing_errors = Column(JSON, nullable=True)
    processing_notes = Column(Text, nullable=True)
    
    # Relationships
    pages = relationship("DocumentPage", back_populates="document", cascade="all, delete-orphan")
    entities = relationship("DocumentEntity", back_populates="document", cascade="all, delete-orphan")
    diagrams = relationship("DocumentDiagram", back_populates="document", cascade="all, delete-orphan")
    analysis_results = relationship("DocumentAnalysis", back_populates="document", cascade="all, delete-orphan")


class DocumentPage(Base):
    """Individual page metadata and content"""
    __tablename__ = "document_pages"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False, index=True)
    page_number = Column(Integer, nullable=False, index=True)
    
    # Content analysis
    content_summary = Column(Text, nullable=True)
    text_content = Column(Text, nullable=True)
    text_length = Column(Integer, default=0)
    word_count = Column(Integer, default=0)
    
    # Content classification
    content_types = Column(ARRAY(String), default=list)  # ['text', 'diagram', 'table']
    primary_content_type = Column(String(50), default=ContentType.EMPTY.value)
    
    # Quality metrics
    extraction_confidence = Column(Float, default=0.0)
    content_quality_score = Column(Float, default=0.0)
    
    # Layout analysis
    has_header = Column(Boolean, default=False)
    has_footer = Column(Boolean, default=False)
    has_signatures = Column(Boolean, default=False)
    has_handwriting = Column(Boolean, default=False)
    has_diagrams = Column(Boolean, default=False)
    has_tables = Column(Boolean, default=False)
    
    # Processing metadata
    processed_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    processing_method = Column(String(100), nullable=True)
    
    # Relationships
    document = relationship("Document", back_populates="pages")
    entities = relationship("DocumentEntity", back_populates="page")
    diagrams = relationship("DocumentDiagram", back_populates="page")


class DocumentEntity(Base):
    """Basic entities extracted from documents"""
    __tablename__ = "document_entities"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False, index=True)
    page_id = Column(UUID(as_uuid=True), ForeignKey("document_pages.id"), nullable=True, index=True)
    page_number = Column(Integer, nullable=False, index=True)
    
    # Entity data
    entity_type = Column(String(100), nullable=False, index=True)
    entity_value = Column(Text, nullable=False)
    normalized_value = Column(Text, nullable=True)  # Cleaned/standardized value
    
    # Context and quality
    context = Column(Text, nullable=True)  # Surrounding text for context
    confidence = Column(Float, default=0.0)
    extraction_method = Column(String(100), nullable=True)
    
    # Location metadata (for future UI highlighting)
    position_data = Column(JSON, nullable=True)  # Bounding box, coordinates, etc.
    
    # Processing metadata
    extracted_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    
    # Relationships
    document = relationship("Document", back_populates="entities")
    page = relationship("DocumentPage", back_populates="entities")


class DocumentDiagram(Base):
    """Diagram detection and basic analysis"""
    __tablename__ = "document_diagrams"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False, index=True)
    page_id = Column(UUID(as_uuid=True), ForeignKey("document_pages.id"), nullable=True, index=True)
    page_number = Column(Integer, nullable=False, index=True)
    
    # Classification
    diagram_type = Column(String(100), default=DiagramType.UNKNOWN.value, index=True)
    classification_confidence = Column(Float, default=0.0)
    
    # Storage and processing
    extracted_image_path = Column(String(1024), nullable=True)  # Extracted diagram image
    basic_analysis_completed = Column(Boolean, default=False)
    detailed_analysis_completed = Column(Boolean, default=False)
    
    # Basic analysis results
    basic_analysis = Column(JSON, nullable=True)  # Simple description, elements found
    
    # Quality metrics
    image_quality_score = Column(Float, default=0.0)
    clarity_score = Column(Float, default=0.0)
    
    # Metadata
    detected_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    basic_analysis_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    document = relationship("Document", back_populates="diagrams")
    page = relationship("DocumentPage", back_populates="diagrams")


class DocumentAnalysis(Base):
    """Comprehensive contract analysis results"""
    __tablename__ = "document_analyses"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False, index=True)
    
    # Analysis metadata
    analysis_type = Column(String(100), default="contract_analysis")
    analysis_version = Column(String(50), default="v1.0")
    started_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Analysis status
    status = Column(String(50), default="pending")  # pending, in_progress, completed, failed
    progress_percentage = Column(Integer, default=0)
    current_step = Column(String(100), nullable=True)
    
    # Results
    detailed_entities = Column(JSON, nullable=True)  # Complex entity extractions
    diagram_analyses = Column(JSON, nullable=True)  # Detailed diagram analysis
    compliance_results = Column(JSON, nullable=True)  # Legal compliance analysis
    risk_assessment = Column(JSON, nullable=True)  # Risk analysis
    recommendations = Column(JSON, nullable=True)  # Actionable recommendations
    
    # Quality and confidence
    overall_confidence = Column(Float, default=0.0)
    analysis_quality_score = Column(Float, default=0.0)
    
    # Processing metadata
    processing_time_seconds = Column(Float, default=0.0)
    langgraph_workflow_id = Column(String(255), nullable=True)
    
    # Errors and issues
    analysis_errors = Column(JSON, nullable=True)
    analysis_warnings = Column(JSON, nullable=True)
    
    # Relationships
    document = relationship("Document", back_populates="analysis_results")


# Create all tables
def create_tables(engine):
    """Create all tables in the database"""
    Base.metadata.create_all(engine)


# Database helper functions
def get_document_with_metadata(db, document_id: str) -> Optional[Document]:
    """Get document with all related metadata"""
    return db.query(Document).filter(Document.id == document_id).first()


def get_document_pages_summary(db, document_id: str) -> List[Dict[str, Any]]:
    """Get summary of all pages for a document"""
    pages = db.query(DocumentPage).filter(DocumentPage.document_id == document_id).order_by(DocumentPage.page_number).all()
    
    return [
        {
            "page_number": page.page_number,
            "content_types": page.content_types,
            "primary_content_type": page.primary_content_type,
            "has_diagrams": page.has_diagrams,
            "text_length": page.text_length,
            "confidence": page.extraction_confidence
        }
        for page in pages
    ]


def get_document_diagrams_by_page(db, document_id: str) -> Dict[int, List[Dict[str, Any]]]:
    """Get diagrams organized by page number"""
    diagrams = db.query(DocumentDiagram).filter(DocumentDiagram.document_id == document_id).order_by(DocumentDiagram.page_number).all()
    
    diagrams_by_page = {}
    for diagram in diagrams:
        page_num = diagram.page_number
        if page_num not in diagrams_by_page:
            diagrams_by_page[page_num] = []
        
        diagrams_by_page[page_num].append({
            "id": str(diagram.id),
            "diagram_type": diagram.diagram_type,
            "confidence": diagram.classification_confidence,
            "basic_analysis": diagram.basic_analysis,
            "image_path": diagram.extracted_image_path
        })
    
    return diagrams_by_page


def get_document_entities_by_type(db, document_id: str) -> Dict[str, List[Dict[str, Any]]]:
    """Get entities organized by type"""
    entities = db.query(DocumentEntity).filter(DocumentEntity.document_id == document_id).all()
    
    entities_by_type = {}
    for entity in entities:
        entity_type = entity.entity_type
        if entity_type not in entities_by_type:
            entities_by_type[entity_type] = []
        
        entities_by_type[entity_type].append({
            "id": str(entity.id),
            "value": entity.entity_value,
            "normalized_value": entity.normalized_value,
            "page_number": entity.page_number,
            "confidence": entity.confidence,
            "context": entity.context
        })
    
    return entities_by_type