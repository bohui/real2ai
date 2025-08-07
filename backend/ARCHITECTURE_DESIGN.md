# Real2.AI Two-Tier Document Processing Architecture

## System Overview

This document outlines the architectural design for Real2.AI's document processing system, featuring a clean separation between basic document processing (Tier 1) and advanced contract analysis (Tier 2).

**Current Implementation Status**: This architecture is fully implemented using LangGraph multi-agent workflows, Supabase database with shared resource model, and real-time WebSocket progress tracking. Last updated: January 2025.

## Architecture Principles

### **Core Design Philosophy**
- **Separation of Concerns**: Basic processing separated from advanced analysis
- **Progressive Enhancement**: Build from simple extraction to complex analysis
- **Data Persistence**: All intermediate results stored for reliability and debugging
- **Scalability**: Each tier can scale independently
- **Modularity**: Clear interfaces between components

### **Data Flow Architecture**
```
User Upload → Tier 1 (DocumentService) → Database → Tier 2 (ContractAnalysisService) → Final Results
     ↓              ↓                        ↓              ↓                          ↓
  File Storage   Basic Entities          Persistence    LangGraph Analysis      Enhanced Results
```

## Tier 1: DocumentService - Basic Processing & Persistence

### **Purpose & Scope**
The DocumentService handles foundational document processing with high reliability and comprehensive data persistence.

### **Key Responsibilities**

#### 1. Document Upload & Validation
- File type validation (PDF, images)
- File size limits and security checks
- Virus scanning and content validation
- Storage path management

#### 2. Text Extraction & OCR
- **Primary**: PyMuPDF for native PDF text
- **Fallback**: Tesseract OCR for images and scanned PDFs
- **Advanced**: Gemini Vision API for complex documents
- **Quality Assessment**: Confidence scoring for extraction methods

#### 3. Page-Level Analysis
```python
# Page Analysis Schema
{
    "page_number": int,
    "text_content": str,
    "content_types": ["text", "diagram", "table", "signature"],
    "primary_content_type": ContentType,
    "extraction_confidence": float,
    "quality_metrics": {
        "text_clarity": float,
        "image_quality": float,
        "layout_complexity": float
    },
    "layout_features": {
        "has_header": bool,
        "has_footer": bool,
        "has_signatures": bool,
        "has_handwriting": bool,
        "has_diagrams": bool,
        "has_tables": bool
    }
}
```

#### 4. Basic Entity Extraction
Using pattern matching and simple NLP for:
- **Addresses**: Australian address formats with postcode validation
- **Dates**: Multiple date formats with business day calculations
- **Financial Amounts**: Currency detection and normalization
- **Party Names**: Person and company name patterns
- **Property References**: Lot/plan numbers, title references

#### 5. Diagram Detection & Classification
```python
# Diagram Detection Pipeline
{
    "detection": {
        "method": "visual_analysis|text_context|hybrid",
        "confidence": float,
        "bounding_box": [x, y, width, height]
    },
    "classification": {
        "diagram_type": DiagramType,
        "classification_confidence": float,
        "keywords_found": [str]
    },
    "extraction": {
        "image_path": str,
        "image_quality": float,
        "resolution": [width, height]
    }
}
```

#### 6. Data Persistence
All data persisted using existing SQLAlchemy models:
- `Document`: Master record with metadata
- `DocumentPage`: Page-level content and analysis
- `DocumentEntity`: Basic entities with page references
- `DocumentDiagram`: Diagram metadata and storage paths

### **API Interface**
```python
class DocumentService:
    async def process_document(
        self, 
        file_path: str, 
        user_id: str, 
        original_filename: str
    ) -> DocumentProcessingResult
    
    async def get_document_summary(
        self, 
        document_id: str
    ) -> DocumentSummary
    
    async def get_document_pages(
        self, 
        document_id: str, 
        page_numbers: Optional[List[int]] = None
    ) -> List[DocumentPage]
    
    async def get_document_diagrams(
        self, 
        document_id: str
    ) -> List[DocumentDiagram]
```

### **Performance Targets**
- **Processing Speed**: <30 seconds for 20-page PDF
- **Text Extraction**: 95%+ accuracy for native PDF text
- **OCR Accuracy**: 90%+ for clear scanned documents  
- **Entity Detection**: 80%+ recall for basic entities
- **Diagram Detection**: 85%+ accuracy for common diagram types

## Tier 2: ContractAnalysisService - Advanced LangGraph Analysis

### **Purpose & Scope**  
The ContractAnalysisService performs sophisticated contract analysis using LangGraph workflows and AI models.

### **Key Responsibilities**

#### 1. Document Context Retrieval
- Load complete document data from Tier 1 processing
- Assemble full document context with page-level details
- Prioritize content based on relevance and quality scores

#### 2. LangGraph Workflow Execution
```python
# LangGraph Analysis Workflow
workflow_steps = [
    "document_validation",      # Validate document completeness
    "detailed_entity_extraction", # Extract structured entities
    "page_diagram_analysis",    # Analyze diagrams by page
    "compliance_analysis",      # Australian law compliance
    "risk_assessment",         # Risk identification
    "recommendation_generation" # Actionable recommendations
]
```

#### 3. Detailed Entity Extraction
Using the comprehensive `ContractEntityExtraction` schema:
```python
# Enhanced Entity Schema
{
    "property_address": PropertyAddress,
    "parties": [ContractParty],
    "dates": [ContractDate],
    "financial_amounts": [FinancialAmount],
    "legal_references": [LegalReference],
    "conditions": [ContractCondition],
    "property_details": PropertyDetails
}
```

#### 4. Page-Specific Diagram Analysis
```python
# Per-page diagram analysis using vision models
async def analyze_diagram_by_page(
    document_id: str, 
    page_number: int, 
    diagram_id: str
) -> DiagramAnalysis:
    """
    Analyze single diagram using page-specific context
    - Load diagram image from Tier 1
    - Get page text context for better understanding
    - Use vision model for detailed analysis
    - Extract infrastructure, compliance, and risk elements
    """
```

#### 5. Australian Compliance Analysis
- State-specific property law compliance
- Mandatory disclosure requirements
- Cooling-off period validation
- Stamp duty and legal fee calculations

#### 6. Risk Assessment & Recommendations
```python
# Risk Assessment Schema
{
    "overall_risk_score": float,
    "risk_categories": {
        "legal_compliance": RiskAssessment,
        "financial_exposure": RiskAssessment,
        "property_specific": RiskAssessment,
        "contractual_terms": RiskAssessment
    },
    "recommendations": [ActionableRecommendation]
}
```

### **LangGraph Workflow Design**

```python
# Workflow State Management
class ContractAnalysisState(TypedDict):
    document_id: str
    document_data: Dict[str, Any]
    current_step: str
    progress_percentage: int
    
    # Processing results
    detailed_entities: Optional[ContractEntityExtraction]
    diagram_analyses: Dict[int, DiagramEntityExtraction]
    compliance_results: Optional[ComplianceAssessment]
    risk_assessment: Optional[RiskAssessment]
    recommendations: List[ActionableRecommendation]
    
    # Quality metrics
    confidence_scores: Dict[str, float]
    processing_quality: QualityMetrics
```

### **WebSocket Progress Integration**
Real-time progress updates for each workflow step:
```python
workflow_progress = {
    "document_validation": 14,
    "detailed_entity_extraction": 28,
    "page_diagram_analysis": 42,
    "compliance_analysis": 57,
    "risk_assessment": 71,
    "recommendation_generation": 85,
    "report_compilation": 100
}
```

### **API Interface**
```python
class ContractAnalysisService:
    async def analyze_contract(
        self,
        document_id: str,
        user_id: str,
        australian_state: str,
        analysis_options: Optional[AnalysisOptions] = None
    ) -> ContractAnalysisResult
    
    async def get_analysis_status(
        self,
        analysis_id: str
    ) -> AnalysisStatus
    
    async def retry_analysis(
        self,
        analysis_id: str
    ) -> RetryResult
```

## Integration Design

### **Service Communication Pattern**
```python
# Tier 1 → Tier 2 Integration
class DocumentAnalysisPipeline:
    async def full_document_analysis(
        self,
        file_path: str,
        user_id: str,
        analysis_options: AnalysisOptions
    ) -> FullAnalysisResult:
        
        # Step 1: Basic processing
        doc_result = await self.document_service.process_document(
            file_path, user_id, original_filename
        )
        
        if not doc_result.success:
            return FailureResult(doc_result.error)
        
        # Step 2: Advanced analysis
        analysis_result = await self.contract_service.analyze_contract(
            document_id=doc_result.document_id,
            user_id=user_id,
            australian_state=analysis_options.state
        )
        
        return CombinedResult(doc_result, analysis_result)
```

### **Database Integration Strategy**
- **Shared Models**: Both tiers use same SQLAlchemy models
- **Progressive Enhancement**: Tier 1 creates records, Tier 2 enhances them
- **Atomic Transactions**: Each tier manages its own transaction boundaries
- **Status Tracking**: Clear status progression through processing stages

### **Error Handling & Recovery**
```python
# Multi-tier error handling
class ProcessingError(Exception):
    tier: int
    step: str
    recoverable: bool
    retry_strategy: Optional[RetryStrategy]

# Recovery patterns
- Tier 1 failure → Retry with different extraction method
- Tier 2 failure → Retry with simplified analysis
- Partial success → Continue with available data
- Complete failure → Rollback and preserve error state
```

## Performance & Scalability Considerations

### **Resource Management**
- **Memory**: Stream processing for large files
- **Storage**: Efficient image compression and storage
- **CPU**: Parallel processing where possible
- **Network**: Optimize API calls and data transfer

### **Caching Strategy**
```python
cache_layers = {
    "document_text": "redis_cache",      # 24 hours
    "basic_entities": "redis_cache",     # 12 hours  
    "diagram_analysis": "persistent_cache", # 7 days
    "compliance_templates": "memory_cache"   # 1 hour
}
```

### **Monitoring & Metrics**
```python
metrics = {
    "processing_time_tier1": histogram,
    "processing_time_tier2": histogram,
    "entity_extraction_accuracy": gauge,
    "diagram_detection_rate": gauge,
    "analysis_success_rate": gauge,
    "user_satisfaction_score": gauge
}
```

## Implementation Roadmap

### **Phase 1: Enhanced DocumentService**
- [ ] Redesign existing DocumentService for database persistence
- [ ] Implement comprehensive page-level analysis
- [ ] Add basic entity extraction with improved patterns
- [ ] Enhance diagram detection and classification
- [ ] Add quality scoring and validation

### **Phase 2: LangGraph Integration**
- [ ] Update ContractAnalysisService with LangGraph workflows
- [ ] Implement detailed entity extraction using Pydantic schemas
- [ ] Add page-specific diagram analysis with vision models
- [ ] Integrate WebSocket progress tracking

### **Phase 3: System Integration**
- [ ] Create unified API endpoints combining both tiers
- [ ] Add comprehensive error handling and recovery
- [ ] Implement caching and performance optimizations
- [ ] Add monitoring and metrics collection

### **Phase 4: Advanced Features**
- [ ] Machine learning model integration for better classification
- [ ] Advanced compliance checking with rule engines
- [ ] Automated quality assurance and validation
- [ ] Performance optimization and scaling improvements

## Configuration & Environment

### **Environment Variables**
```bash
# Database
DATABASE_URL=postgresql://...

# AI Services  
OPENAI_API_KEY=...
GEMINI_API_KEY=...

# Storage
DOCUMENT_STORAGE_PATH=/app/storage
MAX_FILE_SIZE_MB=50

# Processing
ENABLE_OCR=true
ENABLE_DIAGRAM_ANALYSIS=true
PROCESSING_TIMEOUT_SECONDS=300

# LangGraph
LANGGRAPH_TRACING=true
WORKFLOW_CHECKPOINT_ENABLED=true
```

### **Service Dependencies**
```yaml
services:
  - postgresql (document persistence)
  - redis (caching and WebSocket state)
  - openai (LLM for analysis)
  - gemini (vision API for diagrams)  
  - supabase (optional backup storage)
  - langsmith (workflow tracing)
```

This architecture provides a solid foundation for scalable, reliable document processing with clear separation of concerns and progressive enhancement capabilities.