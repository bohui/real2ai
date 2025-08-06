"""
Fresh Document Service - Basic Extraction and Persistence
Modern architecture focusing on document processing, page analysis, and metadata persistence
"""

import asyncio
import logging
import uuid
from typing import Dict, Any, Optional, List, BinaryIO
from datetime import datetime, UTC
from pathlib import Path
import mimetypes
import re

from fastapi import UploadFile, HTTPException
from PIL import Image
import pypdf
import pymupdf  # pymupdf

from app.core.config import get_settings
from app.models.document_models import (
    Document,
    DocumentPage,
    DocumentEntity,
    DocumentDiagram,
    ProcessingStatus,
    ContentType,
    DiagramType,
    EntityType,
)
from app.services.gemini_ocr_service import GeminiOCRService
from app.prompts.schema.ocr_extraction_schema import (
    OCRExtractionResult,
    QuickOCRResult,
)
from app.clients import get_supabase_client
from app.clients.base.exceptions import ClientError, ClientConnectionError

logger = logging.getLogger(__name__)


class FreshDocumentService:
    """
    Fresh Document Service with database persistence and page-level analysis

    Responsibilities:
    - Document upload and validation
    - Basic OCR and text extraction with page references
    - Page-level content analysis and summarization
    - Basic entity extraction (addresses, dates, amounts, parties)
    - Diagram detection and classification
    - Metadata persistence to database
    - Quality assessment and validation
    """

    def __init__(self):
        self.settings = get_settings()
        self.supabase_client = None
        self.ocr_service = None
        self.storage_bucket = "documents"

    async def initialize(self):
        """Initialize service with required clients"""
        try:
            # Initialize clients
            self.supabase_client = await get_supabase_client()
            self.ocr_service = GeminiOCRService()
            await self.ocr_service.initialize()

            logger.info("Fresh Document Service initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize document service: {e}")
            raise HTTPException(
                status_code=503, detail="Document service initialization failed"
            )

    async def process_document(
        self,
        file: UploadFile,
        user_id: str,
        australian_state: Optional[str] = None,
        contract_type: Optional[str] = None,
        document_type: Optional[str] = None,
        processing_options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Complete document processing pipeline

        Args:
            file: Uploaded file
            user_id: User identifier
            australian_state: Australian state for context
            contract_type: Type of contract
            document_type: Type of document
            processing_options: Additional processing options

        Returns:
            Complete processing results with database IDs
        """
        processing_start = datetime.now(UTC)
        processing_options = processing_options or {}

        try:
            # Step 1: Upload and create document record
            document_id = str(uuid.uuid4())
            upload_result = await self._upload_and_create_document(
                file,
                user_id,
                document_id,
                australian_state,
                contract_type,
                document_type,
            )

            # Step 2: Extract text and analyze pages
            extraction_result = await self._extract_text_with_pages(
                document_id, upload_result["storage_path"], upload_result["file_type"]
            )

            # Step 3: Detect and classify diagrams
            diagram_result = await self._detect_and_classify_diagrams(
                document_id, extraction_result
            )

            # Step 4: Extract basic entities
            entity_result = await self._extract_basic_entities(
                document_id, extraction_result
            )

            # Step 5: Update document with final metadata
            await self._finalize_document_processing(
                document_id,
                extraction_result,
                diagram_result,
                entity_result,
                processing_start,
            )

            # Step 6: Generate response
            final_result = await self._generate_processing_response(document_id)

            logger.info(f"Document {document_id} processed successfully")
            return final_result

        except Exception as e:
            logger.error(f"Document processing failed: {e}")
            # Update document status to failed if it exists
            if "document_id" in locals():
                await self._mark_document_failed(document_id, str(e))
            raise HTTPException(
                status_code=500, detail=f"Document processing failed: {str(e)}"
            )

    async def _upload_and_create_document(
        self,
        file: UploadFile,
        user_id: str,
        document_id: str,
        australian_state: Optional[str],
        contract_type: Optional[str],
        document_type: Optional[str],
    ) -> Dict[str, Any]:
        """Upload file and create initial document record"""

        # Read and validate file
        file_content = await file.read()
        self._validate_file(file_content, file.filename)

        # Generate storage path
        file_extension = Path(file.filename).suffix.lower()
        storage_path = f"{user_id}/{document_id}{file_extension}"

        # Upload to storage
        upload_result = await self.supabase_client.upload_file(
            bucket=self.storage_bucket,
            file_path=storage_path,
            content=file_content,
            content_type=file.content_type or mimetypes.guess_type(file.filename)[0],
        )

        # Create document record
        document = Document(
            id=document_id,
            user_id=user_id,
            original_filename=file.filename,
            file_type=file_extension.lstrip("."),
            storage_path=storage_path,
            file_size=len(file_content),
            processing_status=ProcessingStatus.PROCESSING.value,
            processing_started_at=datetime.now(UTC),
            document_type=document_type,
            australian_state=australian_state,
            contract_type=contract_type,
        )

        # Document will be persisted via Supabase client

        return {
            "document_id": document_id,
            "storage_path": storage_path,
            "file_type": file_extension.lstrip("."),
            "upload_url": upload_result.get("url"),
        }

    async def _extract_text_with_pages(
        self, document_id: str, storage_path: str, file_type: str
    ) -> Dict[str, Any]:
        """Extract text using structured OCR with page references"""

        try:
            # Get file content
            file_content = await self.supabase_client.download_file(
                bucket=self.storage_bucket, file_path=storage_path
            )

            # Use structured OCR extraction
            ocr_result = await self.ocr_service.extract_structured_ocr(
                file_content=file_content,
                file_type=file_type,
                filename=Path(storage_path).name,
                use_quick_mode=False,  # Use comprehensive mode for full analysis
            )

            if not ocr_result.get("parsing_success"):
                raise Exception("OCR parsing failed")

            extraction_data = ocr_result["ocr_extraction"]

            # Process page-level data
            await self._process_page_data(document_id, extraction_data)

            return {
                "extraction_successful": True,
                "full_text": extraction_data.get("full_text", ""),
                "total_pages": extraction_data.get("document_structure", {}).get(
                    "total_pages", 0
                ),
                "text_blocks": extraction_data.get("text_blocks", []),
                "extraction_confidence": extraction_data.get(
                    "extraction_confidence", 0.0
                ),
                "processing_notes": extraction_data.get("processing_notes", []),
            }

        except Exception as e:
            logger.error(f"Text extraction failed for document {document_id}: {e}")
            return {
                "extraction_successful": False,
                "error": str(e),
                "full_text": "",
                "total_pages": 0,
                "text_blocks": [],
            }

    async def _process_page_data(
        self, document_id: str, extraction_data: Dict[str, Any]
    ):
        """Process and store page-level data"""

        text_blocks = extraction_data.get("text_blocks", [])
        document_structure = extraction_data.get("document_structure", {})

        # Group text blocks by page
        pages_data = {}
        for block in text_blocks:
            page_num = block.get("page_number", 1)
            if page_num not in pages_data:
                pages_data[page_num] = {
                    "text_content": "",
                    "content_types": set(),
                    "has_signatures": False,
                    "has_handwriting": False,
                    "has_diagrams": False,
                    "has_tables": False,
                    "text_length": 0,
                    "confidence_scores": [],
                }

            # Accumulate page data
            page_data = pages_data[page_num]
            page_data["text_content"] += block.get("text", "") + "\n"
            page_data["content_types"].add(block.get("section_type", "text"))
            page_data["confidence_scores"].append(block.get("confidence", 0.0))

            # Check for special content
            section_type = block.get("section_type", "").lower()
            if "signature" in section_type:
                page_data["has_signatures"] = True
            elif "table" in section_type:
                page_data["has_tables"] = True
            elif "diagram" in section_type or "image" in section_type:
                page_data["has_diagrams"] = True

        # Check document structure for additional info
        has_signatures = document_structure.get("has_signatures", False)
        has_handwriting = document_structure.get("has_handwritten_notes", False)

        # Create page records
        for page_num, page_data in pages_data.items():
            content_types_list = list(page_data["content_types"])
            primary_content_type = self._determine_primary_content_type(
                content_types_list
            )

            # Calculate page-level metrics
            text_content = page_data["text_content"].strip()
            confidence_scores = page_data["confidence_scores"]
            avg_confidence = (
                sum(confidence_scores) / len(confidence_scores)
                if confidence_scores
                else 0.0
            )

            # Generate page summary
            page_summary = self._generate_page_summary(text_content, content_types_list)

            page_record = DocumentPage(
                document_id=document_id,
                page_number=page_num,
                content_summary=page_summary,
                text_content=text_content,
                text_length=len(text_content),
                word_count=len(text_content.split()) if text_content else 0,
                content_types=content_types_list,
                primary_content_type=primary_content_type,
                extraction_confidence=avg_confidence,
                content_quality_score=self._calculate_content_quality(
                    text_content, avg_confidence
                ),
                has_signatures=page_data["has_signatures"] or has_signatures,
                has_handwriting=has_handwriting,
                has_diagrams=page_data["has_diagrams"],
                has_tables=page_data["has_tables"],
                processing_method="structured_ocr",
            )

            # Note: Page records will be persisted via Supabase client
            pass

    def _determine_primary_content_type(self, content_types: List[str]) -> str:
        """Determine primary content type for a page"""

        # Priority order for content types
        priority = {
            "diagram": ContentType.DIAGRAM,
            "image": ContentType.DIAGRAM,
            "table": ContentType.TABLE,
            "signature": ContentType.SIGNATURE,
            "text": ContentType.TEXT,
            "body": ContentType.TEXT,
            "header": ContentType.TEXT,
            "footer": ContentType.TEXT,
        }

        for content_type in priority.keys():
            if content_type in content_types:
                return priority[content_type].value

        if content_types:
            return ContentType.MIXED.value
        else:
            return ContentType.EMPTY.value

    def _generate_page_summary(
        self, text_content: str, content_types: List[str]
    ) -> str:
        """Generate a summary of page content"""

        if not text_content.strip():
            if "diagram" in content_types or "image" in content_types:
                return "Page contains diagrams or images with minimal text"
            elif "signature" in content_types:
                return "Page contains signatures and minimal text"
            else:
                return "Page appears to be empty or contains no readable text"

        # Generate summary based on text length and content
        word_count = len(text_content.split())

        if word_count < 20:
            return f"Brief page with {word_count} words, contains: {', '.join(content_types)}"
        elif word_count < 100:
            return f"Short page with {word_count} words, appears to contain administrative or header information"
        elif word_count < 500:
            return f"Medium page with {word_count} words, likely contains contract terms or property details"
        else:
            return f"Long page with {word_count} words, contains substantial contract content and terms"

    def _calculate_content_quality(self, text_content: str, confidence: float) -> float:
        """Calculate content quality score for a page"""

        if not text_content.strip():
            return 0.0

        # Base quality from confidence
        quality = confidence * 0.6

        # Text length factor
        word_count = len(text_content.split())
        if word_count > 50:
            quality += 0.2
        elif word_count > 10:
            quality += 0.1

        # Check for contract-relevant content
        contract_indicators = [
            "agreement",
            "contract",
            "purchase",
            "sale",
            "property",
            "vendor",
            "purchaser",
            "settlement",
            "deposit",
            "clause",
        ]

        text_lower = text_content.lower()
        indicator_count = sum(
            1 for indicator in contract_indicators if indicator in text_lower
        )

        if indicator_count > 0:
            quality += min(0.2, indicator_count * 0.05)

        return min(1.0, quality)

    async def _detect_and_classify_diagrams(
        self, document_id: str, extraction_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Detect and classify diagrams in the document"""

        try:
            if not extraction_result.get("extraction_successful"):
                return {"diagrams_detected": 0, "classifications": []}

            text_blocks = extraction_result.get("text_blocks", [])
            diagram_blocks = [
                block
                for block in text_blocks
                if block.get("section_type", "").lower()
                in ["diagram", "image", "figure"]
            ]

            classifications = []

            for diagram_block in diagram_blocks:
                page_number = diagram_block.get("page_number", 1)

                # Basic diagram classification based on context
                diagram_type = self._classify_diagram_type(diagram_block)

                # Create diagram record
                diagram_record = DocumentDiagram(
                    document_id=document_id,
                    page_number=page_number,
                    diagram_type=diagram_type,
                    classification_confidence=diagram_block.get("confidence", 0.0),
                    basic_analysis_completed=True,
                    basic_analysis={
                        "detected_content": diagram_block.get("text", ""),
                        "context": diagram_block.get("position_hint", ""),
                        "classification_reason": f"Classified as {diagram_type} based on context analysis",
                    },
                    image_quality_score=diagram_block.get("confidence", 0.0),
                )

                # Note: Diagram records will be persisted via Supabase client

                classifications.append(
                    {
                        "page_number": page_number,
                        "diagram_type": diagram_type,
                        "confidence": diagram_block.get("confidence", 0.0),
                    }
                )

            # Note: Diagram persistence now handled via Supabase client

            return {
                "diagrams_detected": len(diagram_blocks),
                "classifications": classifications,
            }

        except Exception as e:
            logger.error(f"Diagram detection failed for document {document_id}: {e}")
            return {"diagrams_detected": 0, "error": str(e)}

    def _classify_diagram_type(self, diagram_block: Dict[str, Any]) -> str:
        """Classify diagram type based on content and context"""

        text_content = diagram_block.get("text", "").lower()

        # Simple keyword-based classification
        if any(keyword in text_content for keyword in ["sewer", "drainage", "service"]):
            return DiagramType.SEWER_DIAGRAM.value
        elif any(keyword in text_content for keyword in ["site", "plan", "layout"]):
            return DiagramType.SITE_PLAN.value
        elif any(
            keyword in text_content for keyword in ["flood", "water", "inundation"]
        ):
            return DiagramType.FLOOD_MAP.value
        elif any(keyword in text_content for keyword in ["fire", "bushfire", "hazard"]):
            return DiagramType.BUSHFIRE_MAP.value
        elif any(keyword in text_content for keyword in ["title", "lot", "survey"]):
            return DiagramType.TITLE_PLAN.value
        elif any(keyword in text_content for keyword in ["survey", "boundary"]):
            return DiagramType.SURVEY_DIAGRAM.value
        elif any(
            keyword in text_content for keyword in ["floor", "building", "elevation"]
        ):
            return DiagramType.FLOOR_PLAN.value
        else:
            return DiagramType.UNKNOWN.value

    async def _extract_basic_entities(
        self, document_id: str, extraction_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Extract basic entities from the document"""

        try:
            if not extraction_result.get("extraction_successful"):
                return {"entities_extracted": 0, "entities_by_type": {}}

            # Use structured extraction data
            full_text = extraction_result.get("full_text", "")
            text_blocks = extraction_result.get("text_blocks", [])

            entities_extracted = 0
            entities_by_type = {}

            # Extract entities by type
            for page_num in range(1, extraction_result.get("total_pages", 1) + 1):
                page_blocks = [
                    b for b in text_blocks if b.get("page_number") == page_num
                ]
                page_text = " ".join([b.get("text", "") for b in page_blocks])

                if page_text.strip():
                    # Extract different entity types
                    addresses = self._extract_addresses(page_text, page_num)
                    dates = self._extract_dates(page_text, page_num)
                    amounts = self._extract_financial_amounts(page_text, page_num)
                    parties = self._extract_party_names(page_text, page_num)

                    # Store entities
                    all_entities = addresses + dates + amounts + parties

                    for entity in all_entities:
                        entity_record = DocumentEntity(
                            document_id=document_id,
                            page_number=entity["page_number"],
                            entity_type=entity["type"],
                            entity_value=entity["value"],
                            normalized_value=entity.get("normalized", entity["value"]),
                            context=entity.get("context", ""),
                            confidence=entity.get("confidence", 0.7),
                            extraction_method="regex_pattern",
                        )

                        # Note: Entity records will be persisted via Supabase client
                        entities_extracted += 1

                        # Group by type for response
                        entity_type = entity["type"]
                        if entity_type not in entities_by_type:
                            entities_by_type[entity_type] = []
                        entities_by_type[entity_type].append(entity)

            # Note: Entity persistence now handled via Supabase client

            return {
                "entities_extracted": entities_extracted,
                "entities_by_type": entities_by_type,
            }

        except Exception as e:
            logger.error(f"Entity extraction failed for document {document_id}: {e}")
            return {"entities_extracted": 0, "error": str(e)}

    def _extract_addresses(self, text: str, page_number: int) -> List[Dict[str, Any]]:
        """Extract addresses using regex patterns"""

        addresses = []

        # Australian address patterns
        patterns = [
            r"\b\d+\s+[A-Za-z\s]+(?:Street|St|Road|Rd|Avenue|Ave|Drive|Dr|Lane|Ln|Place|Pl|Court|Ct|Crescent|Cres|Way|Highway|Hwy)\b[,\s]*[A-Za-z\s]*[,\s]*(?:NSW|VIC|QLD|WA|SA|TAS|ACT|NT)?\s*\d{4}?",
            r"\b(?:Lot|Unit)\s+\d+[A-Za-z]?\s*[,/]?\s*\d+\s+[A-Za-z\s]+(?:Street|St|Road|Rd|Avenue|Ave|Drive|Dr|Lane|Ln|Place|Pl|Court|Ct|Crescent|Cres|Way)\b",
        ]

        for pattern in patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                address_text = match.group().strip()
                addresses.append(
                    {
                        "type": EntityType.ADDRESS.value,
                        "value": address_text,
                        "normalized": address_text.title(),
                        "page_number": page_number,
                        "confidence": 0.8,
                        "context": self._get_context(text, match.start(), match.end()),
                    }
                )

        return addresses

    def _extract_dates(self, text: str, page_number: int) -> List[Dict[str, Any]]:
        """Extract dates using regex patterns"""

        dates = []

        # Date patterns
        patterns = [
            r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b",
            r"\b\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{2,4}\b",
            r"\b(?:January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2}[,\s]+\d{2,4}\b",
        ]

        for pattern in patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                date_text = match.group().strip()
                dates.append(
                    {
                        "type": EntityType.DATE.value,
                        "value": date_text,
                        "page_number": page_number,
                        "confidence": 0.7,
                        "context": self._get_context(text, match.start(), match.end()),
                    }
                )

        return dates

    def _extract_financial_amounts(
        self, text: str, page_number: int
    ) -> List[Dict[str, Any]]:
        """Extract financial amounts using regex patterns"""

        amounts = []

        # Financial amount patterns
        patterns = [
            r"\$[\d,]+(?:\.\d{2})?",
            r"\b\d{1,3}(?:,\d{3})*(?:\.\d{2})?\s*dollars?\b",
            r"\b(?:AUD|USD|AU\$|US\$)\s*[\d,]+(?:\.\d{2})?",
        ]

        for pattern in patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                amount_text = match.group().strip()
                amounts.append(
                    {
                        "type": EntityType.FINANCIAL_AMOUNT.value,
                        "value": amount_text,
                        "page_number": page_number,
                        "confidence": 0.8,
                        "context": self._get_context(text, match.start(), match.end()),
                    }
                )

        return amounts

    def _extract_party_names(self, text: str, page_number: int) -> List[Dict[str, Any]]:
        """Extract party names using patterns and keywords"""

        parties = []

        # Look for patterns indicating party names
        party_keywords = [
            r"(?:Vendor|Purchaser|Landlord|Tenant|Party)[:\s]+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)",
            r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(?:as|being)\s+(?:Vendor|Purchaser|Landlord|Tenant)",
            r"(?:Mr|Mrs|Ms|Dr|Professor|Prof)\.?\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)",
        ]

        for pattern in party_keywords:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                name = (
                    match.group(1).strip()
                    if len(match.groups()) > 0
                    else match.group().strip()
                )
                if len(name) > 2:  # Avoid single letters
                    parties.append(
                        {
                            "type": EntityType.PARTY_NAME.value,
                            "value": name,
                            "page_number": page_number,
                            "confidence": 0.6,
                            "context": self._get_context(
                                text, match.start(), match.end()
                            ),
                        }
                    )

        return parties

    def _get_context(
        self, text: str, start: int, end: int, context_length: int = 50
    ) -> str:
        """Get surrounding context for an entity"""

        context_start = max(0, start - context_length)
        context_end = min(len(text), end + context_length)
        context = text[context_start:context_end].strip()

        # Clean up context
        context = " ".join(context.split())  # Remove extra whitespace
        return context

    async def _finalize_document_processing(
        self,
        document_id: str,
        extraction_result: Dict[str, Any],
        diagram_result: Dict[str, Any],
        entity_result: Dict[str, Any],
        processing_start: datetime,
    ):
        """Update document with final processing results"""

        processing_time = (datetime.now(UTC) - processing_start).total_seconds()

        # Get document record via Supabase client
        # Note: Document queries now handled via Supabase client instead of SQLAlchemy
        document = None  # Placeholder - implement Supabase document retrieval
        if not document:
            raise Exception(f"Document {document_id} not found")

        # Update document metadata
        document.processing_status = ProcessingStatus.BASIC_COMPLETE.value
        document.processing_completed_at = datetime.now(UTC)
        document.total_pages = extraction_result.get("total_pages", 0)
        document.total_text_length = len(extraction_result.get("full_text", ""))
        document.total_word_count = len(extraction_result.get("full_text", "").split())
        document.extraction_confidence = extraction_result.get(
            "extraction_confidence", 0.0
        )
        document.text_extraction_method = "structured_ocr"
        document.has_diagrams = diagram_result.get("diagrams_detected", 0) > 0
        document.diagram_count = diagram_result.get("diagrams_detected", 0)

        # Calculate overall quality score
        document.overall_quality_score = self._calculate_overall_quality(
            extraction_result, diagram_result, entity_result
        )

        # Add processing notes
        notes = []
        if extraction_result.get("processing_notes"):
            notes.extend(extraction_result["processing_notes"])
        if diagram_result.get("error"):
            notes.append(f"Diagram detection error: {diagram_result['error']}")
        if entity_result.get("error"):
            notes.append(f"Entity extraction error: {entity_result['error']}")

        document.processing_notes = "\n".join(notes) if notes else None

        # Note: Document updates now handled via Supabase client

    def _calculate_overall_quality(
        self,
        extraction_result: Dict[str, Any],
        diagram_result: Dict[str, Any],
        entity_result: Dict[str, Any],
    ) -> float:
        """Calculate overall document quality score"""

        scores = []

        # Text extraction quality (40%)
        if extraction_result.get("extraction_successful"):
            extraction_confidence = extraction_result.get("extraction_confidence", 0.0)
            text_length = len(extraction_result.get("full_text", ""))

            text_score = extraction_confidence * 0.7
            if text_length > 1000:
                text_score += 0.3
            elif text_length > 100:
                text_score += 0.2
            elif text_length > 10:
                text_score += 0.1

            scores.append(text_score * 0.4)

        # Diagram detection quality (30%)
        diagrams_detected = diagram_result.get("diagrams_detected", 0)
        if diagrams_detected > 0:
            diagram_score = min(1.0, diagrams_detected / 3)  # Up to 3 diagrams expected
            scores.append(diagram_score * 0.3)
        else:
            scores.append(0.15)  # Neutral score for no diagrams

        # Entity extraction quality (30%)
        entities_extracted = entity_result.get("entities_extracted", 0)
        if entities_extracted > 0:
            entity_score = min(
                1.0, entities_extracted / 10
            )  # Up to 10 entities expected
            scores.append(entity_score * 0.3)
        else:
            scores.append(0.1)  # Low score for no entities

        return sum(scores) if scores else 0.0

    async def _mark_document_failed(self, document_id: str, error_message: str):
        """Mark document as failed in database"""

        try:
            # Get document via Supabase client
            document = None  # Placeholder - implement Supabase document retrieval
            if document:
                document.processing_status = ProcessingStatus.FAILED.value
                document.processing_errors = {
                    "error": error_message,
                    "timestamp": datetime.now(UTC).isoformat(),
                }
                # Note: Error status updates handled via Supabase client
        except Exception as e:
            logger.error(f"Failed to mark document as failed: {e}")

    async def _generate_processing_response(self, document_id: str) -> Dict[str, Any]:
        """Generate comprehensive processing response"""

        # Get document with all related data via Supabase client
        # Note: All database queries now handled via Supabase client instead of SQLAlchemy
        document = None  # Placeholder - implement Supabase document retrieval
        if not document:
            raise Exception(f"Document {document_id} not found")

        # Get related data via Supabase client
        pages = []  # Placeholder - implement Supabase page retrieval
        entities = []  # Placeholder - implement Supabase entity retrieval
        diagrams = []  # Placeholder - implement Supabase diagram retrieval

        # Organize entities by type
        entities_by_type = {}
        for entity in entities:
            entity_type = entity.entity_type
            if entity_type not in entities_by_type:
                entities_by_type[entity_type] = []
            entities_by_type[entity_type].append(
                {
                    "value": entity.entity_value,
                    "normalized_value": entity.normalized_value,
                    "page_number": entity.page_number,
                    "confidence": entity.confidence,
                    "context": entity.context,
                }
            )

        # Organize diagrams by page
        diagrams_by_page = {}
        for diagram in diagrams:
            page_num = diagram.page_number
            if page_num not in diagrams_by_page:
                diagrams_by_page[page_num] = []
            diagrams_by_page[page_num].append(
                {
                    "id": str(diagram.id),
                    "type": diagram.diagram_type,
                    "confidence": diagram.classification_confidence,
                    "basic_analysis": diagram.basic_analysis,
                }
            )

        # Generate page summaries
        page_summaries = [
            {
                "page_number": page.page_number,
                "summary": page.content_summary,
                "content_types": page.content_types,
                "primary_type": page.primary_content_type,
                "word_count": page.word_count,
                "quality_score": page.content_quality_score,
                "has_diagrams": page.has_diagrams,
                "has_tables": page.has_tables,
                "has_signatures": page.has_signatures,
            }
            for page in pages
        ]

        return {
            "document_id": str(document.id),
            "processing_status": document.processing_status,
            "processing_completed": document.processing_status
            == ProcessingStatus.BASIC_COMPLETE.value,
            # Document metadata
            "document_metadata": {
                "filename": document.original_filename,
                "file_type": document.file_type,
                "file_size": document.file_size,
                "total_pages": document.total_pages,
                "processing_time": (
                    (
                        document.processing_completed_at
                        - document.processing_started_at
                    ).total_seconds()
                    if document.processing_completed_at
                    else None
                ),
                "quality_score": document.overall_quality_score,
                "extraction_confidence": document.extraction_confidence,
            },
            # Content analysis
            "content_analysis": {
                "total_text_length": document.total_text_length,
                "total_word_count": document.total_word_count,
                "has_diagrams": document.has_diagrams,
                "diagram_count": document.diagram_count,
                "entities_extracted": len(entities),
                "pages_analyzed": len(pages),
            },
            # Page-level data
            "pages": page_summaries,
            "entities_by_type": entities_by_type,
            "diagrams_by_page": diagrams_by_page,
            # Processing metadata
            "processing_metadata": {
                "extraction_method": document.text_extraction_method,
                "processing_notes": document.processing_notes,
                "ready_for_analysis": document.processing_status
                == ProcessingStatus.BASIC_COMPLETE.value,
            },
        }

    def _validate_file(self, file_content: bytes, filename: str):
        """Validate uploaded file"""

        # Check file size
        if len(file_content) > self.settings.max_file_size:
            raise HTTPException(
                status_code=413,
                detail=f"File too large. Maximum size: {self.settings.max_file_size / 1024 / 1024}MB",
            )

        # Check file extension
        file_extension = Path(filename).suffix.lower().lstrip(".")
        if file_extension not in self.settings.allowed_file_types_list:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type. Allowed: {', '.join(self.settings.allowed_file_types_list)}",
            )

        # Check content
        if len(file_content) == 0:
            raise HTTPException(status_code=400, detail="Empty file not allowed")

    # Public API methods
    async def get_document_metadata(
        self, document_id: str, user_id: str
    ) -> Dict[str, Any]:
        """Get document metadata and processing status"""

        # Get document via Supabase client with user verification
        document = (
            None  # Placeholder - implement Supabase document retrieval with user filter
        )

        if not document:
            raise HTTPException(status_code=404, detail="Document not found")

        return await self._generate_processing_response(document_id)

    async def get_document_page_content(
        self, document_id: str, page_number: int, user_id: str
    ) -> Dict[str, Any]:
        """Get content for a specific page"""

        # Verify document ownership via Supabase client
        document = None  # Placeholder - implement Supabase document retrieval with user verification

        if not document:
            raise HTTPException(status_code=404, detail="Document not found")

        # Get page data via Supabase client
        page = None  # Placeholder - implement Supabase page retrieval

        if not page:
            raise HTTPException(status_code=404, detail="Page not found")

        # Get entities and diagrams for this page via Supabase client
        entities = []  # Placeholder - implement Supabase entity retrieval for page

        diagrams = []  # Placeholder - implement Supabase diagram retrieval for page

        return {
            "page_number": page.page_number,
            "content_summary": page.content_summary,
            "text_content": page.text_content,
            "content_types": page.content_types,
            "primary_content_type": page.primary_content_type,
            "quality_metrics": {
                "extraction_confidence": page.extraction_confidence,
                "content_quality_score": page.content_quality_score,
                "word_count": page.word_count,
                "text_length": page.text_length,
            },
            "page_features": {
                "has_diagrams": page.has_diagrams,
                "has_tables": page.has_tables,
                "has_signatures": page.has_signatures,
                "has_handwriting": page.has_handwriting,
            },
            "entities": [
                {
                    "type": entity.entity_type,
                    "value": entity.entity_value,
                    "confidence": entity.confidence,
                    "context": entity.context,
                }
                for entity in entities
            ],
            "diagrams": [
                {
                    "id": str(diagram.id),
                    "type": diagram.diagram_type,
                    "confidence": diagram.classification_confidence,
                    "basic_analysis": diagram.basic_analysis,
                }
                for diagram in diagrams
            ],
        }

    async def health_check(self) -> Dict[str, Any]:
        """Service health check"""

        health = {
            "service": "FreshDocumentService",
            "status": "healthy",
            "timestamp": datetime.now(UTC).isoformat(),
            "components": {},
        }

        # Check database via Supabase client
        try:
            # Note: Database health check now via Supabase client
            health["components"][
                "database"
            ] = "healthy"  # Placeholder - implement Supabase health check
        except Exception as e:
            health["components"]["database"] = f"error: {e}"
            health["status"] = "degraded"

        # Check storage
        try:
            if self.supabase_client:
                health["components"]["storage"] = "healthy"
            else:
                health["components"]["storage"] = "not_initialized"
                health["status"] = "degraded"
        except Exception as e:
            health["components"]["storage"] = f"error: {e}"
            health["status"] = "degraded"

        # Check OCR service
        try:
            if self.ocr_service:
                health["components"]["ocr_service"] = "healthy"
            else:
                health["components"]["ocr_service"] = "not_initialized"
                health["status"] = "degraded"
        except Exception as e:
            health["components"]["ocr_service"] = f"error: {e}"
            health["status"] = "degraded"

        return health
