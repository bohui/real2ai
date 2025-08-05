"""
Gemini OCR Service V3 - Enhanced with PromptManager Integration
Provides OCR capabilities for contract document processing using PromptManager system
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, UTC
from pathlib import Path

from fastapi import HTTPException

from app.core.config import get_settings
from app.core.prompts.service_mixin import PromptEnabledService
from app.models.contract_state import ProcessingStatus, AustralianState, ContractType
from app.prompts.template.image_semantics_schema import ImageSemantics, ImageType
from app.services.ocr_performance_service import (
    OCRPerformanceService,
    ProcessingPriority,
)
from app.clients import get_gemini_client
from app.clients.base.exceptions import (
    ClientError,
    ClientConnectionError,
    ClientQuotaExceededError,
)

logger = logging.getLogger(__name__)


class GeminiOCRService(PromptEnabledService):
    """Advanced OCR service using GeminiClient for contract document processing with PromptManager integration"""

    def __init__(self):
        # Initialize PromptEnabledService first
        super().__init__()
        
        self.settings = get_settings()
        self.gemini_client = None
        self.max_file_size = 50 * 1024 * 1024  # 50MB limit
        self.supported_formats = {
            "pdf",
            "png",
            "jpg",
            "jpeg",
            "webp",
            "gif",
            "bmp",
            "tiff",
        }

        # Performance optimization service
        self.performance_service = OCRPerformanceService()

        # Advanced processing options
        self.processing_profiles = {
            "fast": {
                "max_resolution": 1500,
                "enhancement_level": 1,
                "timeout_seconds": 30,
            },
            "balanced": {
                "max_resolution": 2000,
                "enhancement_level": 2,
                "timeout_seconds": 60,
            },
            "quality": {
                "max_resolution": 3000,
                "enhancement_level": 3,
                "timeout_seconds": 120,
            },
        }

    async def initialize(self):
        """Initialize Gemini OCR service using GeminiClient"""
        try:
            # Get initialized Gemini client from factory
            self.gemini_client = await get_gemini_client()

            # Check if OCR functionality is available
            if hasattr(self.gemini_client, "ocr") and self.gemini_client.ocr:
                logger.info(
                    "Gemini OCR service initialized successfully with GeminiClient"
                )

                # Initialize performance service
                await self.performance_service.initialize()
                logger.info("OCR Performance optimization enabled")

                return True
            else:
                logger.warning("GeminiClient does not have OCR capabilities")
                return False

        except ClientConnectionError as e:
            logger.error(f"Failed to connect to Gemini service: {e}")
            raise HTTPException(
                status_code=503,
                detail="Gemini OCR service unavailable - connection failed",
            )
        except Exception as e:
            logger.error(f"Failed to initialize Gemini OCR service: {str(e)}")
            raise HTTPException(
                status_code=503,
                detail=f"Gemini OCR service initialization failed: {str(e)}",
            )

    async def extract_text_from_document(
        self,
        file_content: bytes,
        file_type: str,
        filename: str,
        contract_context: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
        priority: ProcessingPriority = ProcessingPriority.STANDARD,
        enable_optimization: bool = True,
        use_prompt_templates: bool = True,
    ) -> Dict[str, Any]:
        """Extract text from document using GeminiClient's OCR capabilities with PromptManager

        Args:
            file_content: Raw file bytes
            file_type: File extension (pdf, jpg, png, etc.)
            filename: Original filename
            contract_context: Additional context for better extraction
            user_id: User ID for cost tracking and optimization
            priority: Processing priority level
            enable_optimization: Enable AI performance optimization
            use_prompt_templates: Use PromptManager for enhanced extraction

        Returns:
            Dict containing extracted text, confidence, and metadata
        """
        if not self.gemini_client:
            raise HTTPException(
                status_code=503, detail="Gemini OCR service not initialized"
            )

        try:
            # Validate file
            self._validate_file(file_content, file_type)

            # Select processing profile based on priority
            profile = self._select_processing_profile(priority, len(file_content))

            # Prepare context for OCR with enhanced prompt support
            ocr_context = await self._prepare_enhanced_ocr_context(
                contract_context, profile, use_prompt_templates
            )

            # Use GeminiClient's OCR functionality
            try:
                result = await self.gemini_client.extract_text(
                    content=file_content,
                    content_type=f"application/{file_type.lower()}",
                    contract_context=ocr_context,
                    processing_profile=profile,
                )

                # Add performance metrics if enabled
                if enable_optimization and self.performance_service:
                    await self._track_performance_metrics(
                        user_id=user_id,
                        file_size=len(file_content),
                        processing_time=result.get("processing_time", 0),
                        confidence=result.get("extraction_confidence", 0),
                        priority=priority,
                    )

                # Enhance result with service-level metadata
                result.update(
                    {
                        "service": "GeminiOCRService",
                        "processing_profile": profile,
                        "file_processed": filename,
                        "optimization_enabled": enable_optimization,
                    }
                )

                return result

            except ClientQuotaExceededError as e:
                logger.error(f"Gemini quota exceeded: {e}")
                raise HTTPException(
                    status_code=429,
                    detail="OCR quota exceeded. Please try again later.",
                )
            except ClientError as e:
                logger.error(f"Gemini client error during OCR: {e}")
                raise HTTPException(
                    status_code=500, detail=f"OCR processing failed: {str(e)}"
                )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Unexpected error during OCR extraction: {str(e)}")
            return {
                "extracted_text": "",
                "extraction_method": "gemini_ocr_failed",
                "extraction_confidence": 0.0,
                "error": str(e),
                "extraction_timestamp": datetime.now(UTC).isoformat(),
                "file_processed": filename,
                "processing_details": {
                    "file_size": len(file_content),
                    "file_type": file_type,
                    "error_type": type(e).__name__,
                },
            }

    async def analyze_document(
        self,
        file_content: bytes,
        file_type: str,
        filename: str,
        contract_context: Optional[Dict[str, Any]] = None,
        analysis_options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Analyze document content using GeminiClient's analysis capabilities

        Args:
            file_content: Raw file bytes
            file_type: File extension
            filename: Original filename
            contract_context: Additional context
            analysis_options: Analysis configuration options

        Returns:
            Dict containing analysis results
        """
        if not self.gemini_client:
            raise HTTPException(
                status_code=503, detail="Gemini OCR service not initialized"
            )

        try:
            # Validate file
            self._validate_file(file_content, file_type)

            # Enhance analysis context with prompt templates if available
            enhanced_context = contract_context
            enhanced_options = analysis_options or {}
            
            try:
                # Create context for analysis templates
                analysis_prompt_context = self.create_context(
                    document_type=enhanced_context.get("document_type", "contract") if enhanced_context else "contract",
                    file_type=file_type,
                    australian_state=enhanced_context.get("australian_state", AustralianState.NSW) if enhanced_context else AustralianState.NSW,
                    contract_type=enhanced_context.get("contract_type", ContractType.PURCHASE_AGREEMENT) if enhanced_context else ContractType.PURCHASE_AGREEMENT,
                    analysis_type="document_analysis",
                    filename=filename,
                    service_name=self._service_name
                )

                # Get analysis instructions from templates
                analysis_instructions = await self.render_prompt(
                    template_name="contract_analysis_base",
                    context=analysis_prompt_context,
                    validate=True,
                    use_cache=True
                )

                enhanced_options["enhanced_instructions"] = analysis_instructions
                enhanced_options["template_enhanced"] = True
                
            except Exception as e:
                logger.warning(f"Failed to enhance analysis context with templates: {e}")
                enhanced_options["template_enhanced"] = False

            # Use GeminiClient's document analysis with enhanced context
            result = await self.gemini_client.analyze_document(
                content=file_content,
                content_type=f"application/{file_type.lower()}",
                contract_context=enhanced_context,
                analysis_options=enhanced_options,
            )

            # Add service metadata
            result.update(
                {
                    "service": "GeminiOCRService",
                    "service_version": "v3_prompt_enhanced",
                    "file_processed": filename,
                    "analysis_timestamp": datetime.now(UTC).isoformat(),
                    "prompt_manager_enabled": True,
                }
            )

            return result

        except ClientError as e:
            logger.error(f"Document analysis failed: {e}")
            raise HTTPException(
                status_code=500, detail=f"Document analysis failed: {str(e)}"
            )

    async def extract_image_semantics(
        self,
        file_content: bytes,
        file_type: str,
        filename: str,
        image_type: Optional[ImageType] = None,
        contract_context: Optional[Dict[str, Any]] = None,
        analysis_focus: Optional[str] = None,
        risk_categories: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Extract semantic meaning from property diagrams and images
        
        This method analyzes images to identify infrastructure, boundaries, environmental 
        factors, and potential risks that impact property ownership and development.
        
        Args:
            file_content: Raw image bytes
            file_type: Image file extension (jpg, png, pdf, etc.)
            filename: Original filename
            image_type: Type of diagram/image being analyzed
            contract_context: Additional contract context for analysis
            analysis_focus: Primary focus area (infrastructure, environmental, boundaries, all)
            risk_categories: Specific risk categories to focus on
            
        Returns:
            Dict containing semantic analysis following ImageSemantics schema
            
        Example:
            For a sewer service diagram, this would extract:
            - Sewer pipe locations, depths, and specifications
            - Impact on building envelope and construction
            - Maintenance access requirements
            - Risk assessments for development
        """
        if not self.gemini_client:
            raise HTTPException(
                status_code=503, detail="Gemini OCR service not initialized"
            )

        try:
            # Validate file
            self._validate_file(file_content, file_type)
            
            # Auto-detect image type if not provided
            if image_type is None:
                image_type = await self._detect_image_type(filename, contract_context)
            
            # Prepare enhanced context for semantic analysis
            semantic_context = await self._prepare_semantic_analysis_context(
                image_type=image_type,
                contract_context=contract_context,
                analysis_focus=analysis_focus,
                risk_categories=risk_categories,
                filename=filename
            )
            
            # Use GeminiClient's vision capabilities for semantic analysis
            try:
                result = await self.gemini_client.analyze_image_semantics(
                    content=file_content,
                    content_type=f"image/{file_type.lower()}" if file_type.lower() != 'pdf' else "application/pdf",
                    analysis_context=semantic_context,
                )
                
                # Validate and structure result according to ImageSemantics schema
                try:
                    # Parse the structured response
                    if isinstance(result.get('semantic_analysis'), dict):
                        semantic_result = ImageSemantics(**result['semantic_analysis'])
                    else:
                        # Fallback: structure the response manually
                        semantic_result = self._structure_semantic_response(result, image_type)
                    
                    # Add service metadata
                    structured_result = {
                        "semantic_analysis": semantic_result.dict(),
                        "service": "GeminiOCRService",
                        "service_version": "v3_semantic_analysis",
                        "file_processed": filename,
                        "image_type_detected": image_type.value if image_type else "unknown",
                        "analysis_timestamp": datetime.now(UTC).isoformat(),
                        "prompt_template_used": True,
                        "analysis_focus": analysis_focus or "comprehensive",
                        "processing_metadata": result.get("processing_metadata", {})
                    }
                    
                    return structured_result
                    
                except Exception as schema_error:
                    logger.warning(f"Failed to structure semantic response: {schema_error}")
                    # Return raw result with error info
                    return {
                        "semantic_analysis": result,
                        "service": "GeminiOCRService", 
                        "service_version": "v3_semantic_analysis_fallback",
                        "file_processed": filename,
                        "schema_validation_error": str(schema_error),
                        "analysis_timestamp": datetime.now(UTC).isoformat(),
                    }
                
            except ClientQuotaExceededError as e:
                logger.error(f"Gemini quota exceeded during semantic analysis: {e}")
                raise HTTPException(
                    status_code=429,
                    detail="Semantic analysis quota exceeded. Please try again later.",
                )
            except ClientError as e:
                logger.error(f"Gemini client error during semantic analysis: {e}")
                raise HTTPException(
                    status_code=500, detail=f"Semantic analysis failed: {str(e)}"
                )
                
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Unexpected error during semantic analysis: {str(e)}")
            return {
                "semantic_analysis": None,
                "service": "GeminiOCRService",
                "service_version": "v3_semantic_analysis_error",
                "file_processed": filename,
                "error": str(e),
                "error_type": type(e).__name__,
                "analysis_timestamp": datetime.now(UTC).isoformat(),
                "processing_details": {
                    "file_size": len(file_content),
                    "file_type": file_type,
                    "image_type": image_type.value if image_type else "unknown",
                },
            }

    def _validate_file(self, file_content: bytes, file_type: str):
        """Validate file size and format"""
        # Check file size
        if len(file_content) > self.max_file_size:
            raise HTTPException(
                status_code=413,
                detail=f"File too large for OCR. Maximum size: {self.max_file_size / 1024 / 1024}MB",
            )

        # Check file format
        if file_type.lower() not in self.supported_formats:
            raise HTTPException(
                status_code=400, detail=f"Unsupported file format for OCR: {file_type}"
            )

        # Check if file is empty
        if len(file_content) == 0:
            raise HTTPException(
                status_code=400, detail="Empty file cannot be processed"
            )

    def _select_processing_profile(
        self, priority: ProcessingPriority, file_size: int
    ) -> str:
        """Select optimal processing profile based on priority and file characteristics"""

        # Base profile selection
        if priority in [ProcessingPriority.CRITICAL, ProcessingPriority.HIGH]:
            base_profile = "quality"
        elif priority == ProcessingPriority.STANDARD:
            base_profile = "balanced"
        else:
            base_profile = "fast"

        # Adjust based on file size
        file_size_mb = file_size / (1024 * 1024)

        if file_size_mb > 20:  # Large files
            if base_profile == "fast":
                base_profile = "balanced"
        elif file_size_mb < 1:  # Small files
            if base_profile == "quality":
                base_profile = "balanced"

        return base_profile

    async def _prepare_enhanced_ocr_context(
        self, 
        contract_context: Optional[Dict[str, Any]], 
        profile: str,
        use_prompt_templates: bool = True
    ) -> Dict[str, Any]:
        """Prepare enhanced context for OCR processing with PromptManager support"""
        ocr_context = contract_context or {}

        # Add profile-specific settings
        profile_config = self.processing_profiles.get(
            profile, self.processing_profiles["balanced"]
        )

        ocr_context.update(
            {
                "processing_profile": profile,
                "profile_config": profile_config,
                "service_version": "v3_prompt_enhanced",
            }
        )

        # Enhanced context using PromptManager if enabled
        if use_prompt_templates:
            try:
                # Create context for OCR extraction templates
                prompt_context = self.create_context(
                    document_type=ocr_context.get("document_type", "contract"),
                    file_type=ocr_context.get("file_type", "pdf"),
                    quality_requirements=profile,
                    australian_state=ocr_context.get("australian_state", AustralianState.NSW),
                    contract_type=ocr_context.get("contract_type", ContractType.PURCHASE_AGREEMENT),
                    processing_profile=profile,
                    filename=ocr_context.get("filename", "document"),
                    service_name=self._service_name
                )

                # Get OCR extraction instructions from templates
                ocr_instructions = await self.render_prompt(
                    template_name="ocr_extraction_base",  
                    context=prompt_context,
                    validate=True,
                    use_cache=True
                )

                # Add enhanced instructions to context
                ocr_context["enhanced_instructions"] = ocr_instructions
                ocr_context["template_enhanced"] = True
                
                logger.debug(f"Enhanced OCR context with prompt templates for {profile} profile")

            except Exception as e:
                # Fallback gracefully if template system fails
                logger.warning(f"Failed to enhance OCR context with templates: {e}")
                ocr_context["template_enhanced"] = False
                ocr_context["template_error"] = str(e)

        return ocr_context

    def _prepare_ocr_context(
        self, contract_context: Optional[Dict[str, Any]], profile: str
    ) -> Dict[str, Any]:
        """Legacy context preparation (maintained for backward compatibility)"""
        ocr_context = contract_context or {}

        # Add profile-specific settings
        profile_config = self.processing_profiles.get(
            profile, self.processing_profiles["balanced"]
        )

        ocr_context.update(
            {
                "processing_profile": profile,
                "profile_config": profile_config,
                "service_version": "v2_legacy",
            }
        )

        return ocr_context

    async def _track_performance_metrics(
        self,
        user_id: Optional[str],
        file_size: int,
        processing_time: float,
        confidence: float,
        priority: ProcessingPriority,
    ):
        """Track performance metrics for optimization"""
        try:
            if self.performance_service:
                await self.performance_service.track_processing(
                    user_id=user_id or "anonymous",
                    processing_time_ms=int(processing_time * 1000),
                    file_size_bytes=file_size,
                    confidence_score=confidence,
                    priority=priority,
                    extraction_method="gemini_client_ocr",
                )
        except Exception as e:
            logger.warning(f"Failed to track performance metrics: {e}")

    async def _detect_image_type(
        self, filename: str, contract_context: Optional[Dict[str, Any]] = None
    ) -> ImageType:
        """Auto-detect image type based on filename and context"""
        filename_lower = filename.lower()
        
        # Filename-based detection
        if "sewer" in filename_lower or "service" in filename_lower:
            return ImageType.SEWER_SERVICE_DIAGRAM
        elif "site" in filename_lower and "plan" in filename_lower:
            return ImageType.SITE_PLAN
        elif "survey" in filename_lower:
            return ImageType.SURVEY_DIAGRAM
        elif "flood" in filename_lower:
            return ImageType.FLOOD_MAP
        elif "bushfire" in filename_lower or "fire" in filename_lower:
            return ImageType.BUSHFIRE_MAP
        elif "zoning" in filename_lower:
            return ImageType.ZONING_MAP
        elif "drainage" in filename_lower:
            return ImageType.DRAINAGE_PLAN
        elif "utility" in filename_lower or "utilities" in filename_lower:
            return ImageType.UTILITY_PLAN
        elif "strata" in filename_lower:
            return ImageType.STRATA_PLAN
        elif "contour" in filename_lower:
            return ImageType.CONTOUR_MAP
        elif "envelope" in filename_lower:
            return ImageType.BUILDING_ENVELOPE_PLAN
        elif "parking" in filename_lower:
            return ImageType.PARKING_PLAN
        elif "landscape" in filename_lower:
            return ImageType.LANDSCAPE_PLAN
        elif "aerial" in filename_lower:
            return ImageType.AERIAL_VIEW
        elif "elevation" in filename_lower:
            return ImageType.ELEVATION_VIEW
        elif "section" in filename_lower:
            return ImageType.CROSS_SECTION
        elif "environmental" in filename_lower:
            return ImageType.ENVIRONMENTAL_OVERLAY
        else:
            return ImageType.UNKNOWN

    async def _prepare_semantic_analysis_context(
        self,
        image_type: ImageType,
        contract_context: Optional[Dict[str, Any]] = None,
        analysis_focus: Optional[str] = None,
        risk_categories: Optional[List[str]] = None,
        filename: str = "image"
    ) -> Dict[str, Any]:
        """Prepare enhanced context for semantic analysis using PromptManager"""
        
        # Base context
        semantic_context = {
            "image_type": image_type.value,
            "filename": filename,
            "analysis_focus": analysis_focus or "comprehensive",
            "risk_categories": risk_categories or [],
            "service_version": "v3_semantic_analysis",
        }
        
        # Add contract context if available
        if contract_context:
            semantic_context.update(contract_context)
        
        # Enhanced context using PromptManager
        try:
            # Create context for semantic analysis templates
            prompt_context = self.create_context(
                australian_state=semantic_context.get("australian_state", AustralianState.NSW),
                contract_type=semantic_context.get("contract_type", ContractType.PURCHASE_AGREEMENT),
                image_type=image_type.value,
                property_type=semantic_context.get("property_type", "residential"),
                analysis_focus=analysis_focus,
                risk_categories=risk_categories,
                filename=filename,
                service_name=self._service_name
            )

            # Get semantic analysis instructions from templates
            semantic_instructions = await self.render_prompt(
                template_name="image_semantics",
                context=prompt_context,
                validate=True,
                use_cache=True
            )

            # Add enhanced instructions to context
            semantic_context["enhanced_instructions"] = semantic_instructions
            semantic_context["template_enhanced"] = True
            
            logger.debug(f"Enhanced semantic analysis context for {image_type.value}")

        except Exception as e:
            # Fallback gracefully if template system fails
            logger.warning(f"Failed to enhance semantic analysis context with templates: {e}")
            semantic_context["template_enhanced"] = False
            semantic_context["template_error"] = str(e)
            
            # Add basic instructions as fallback
            semantic_context["basic_instructions"] = self._get_basic_semantic_instructions(image_type)

        return semantic_context

    def _get_basic_semantic_instructions(self, image_type: ImageType) -> str:
        """Get basic semantic analysis instructions as fallback"""
        base_instructions = """
        Analyze this property image/diagram and extract semantic meaning including:
        1. Infrastructure elements (pipes, utilities, services)
        2. Property boundaries and easements
        3. Environmental features and risks
        4. Building elements and development constraints
        5. Spatial relationships between elements
        6. Potential risks for property development
        
        Focus on elements that impact property ownership, development, and risk assessment.
        """
        
        if image_type == ImageType.SEWER_SERVICE_DIAGRAM:
            return base_instructions + """
            Special focus for sewer diagrams:
            - Sewer pipe locations, depths, diameters
            - Connection points and manholes
            - Impact on building envelope
            - Maintenance access requirements
            - Council vs private ownership
            """
        elif image_type == ImageType.FLOOD_MAP:
            return base_instructions + """
            Special focus for flood maps:
            - Flood zone boundaries and levels
            - Water flow directions
            - Infrastructure at risk
            - Building restriction areas
            - Insurance implications
            """
        
        return base_instructions

    def _structure_semantic_response(self, raw_result: Dict[str, Any], image_type: ImageType) -> ImageSemantics:
        """Structure raw AI response into ImageSemantics schema format"""
        from app.prompts.template.image_semantics_schema import (
            ConfidenceLevel, LocationReference, SemanticElement
        )
        
        # Extract basic metadata
        image_title = raw_result.get("image_title") or raw_result.get("title", "")
        semantic_summary = raw_result.get("semantic_summary") or raw_result.get("summary", "")
        
        # Create basic semantic structure
        semantic_result = ImageSemantics(
            image_type=image_type,
            image_title=image_title,
            semantic_summary=semantic_summary or f"Analysis of {image_type.value} image",
            property_impact_summary=raw_result.get("property_impact_summary", "Impact assessment not available"),
            key_findings=raw_result.get("key_findings", []),
            areas_of_concern=raw_result.get("areas_of_concern", []),
            analysis_confidence=ConfidenceLevel.MEDIUM,  # Default to medium confidence
            processing_notes=[f"Structured from raw AI response for {image_type.value}"],
            suggested_followup=raw_result.get("suggested_followup", [])
        )
        
        return semantic_result

    async def health_check(self) -> Dict[str, Any]:
        """Comprehensive health check for OCR service"""
        try:
            # Check if client is initialized
            if not self.gemini_client:
                return {
                    "service_status": "not_initialized",
                    "error": "GeminiClient not initialized",
                    "last_health_check": datetime.now(UTC).isoformat(),
                }

            # Get client health status
            client_health = await self.gemini_client.health_check()

            # Check OCR specific health
            ocr_available = (
                client_health.get("status") == "healthy"
                and client_health.get("ocr_status", "unknown") == "healthy"
            )

            # Performance service health
            performance_health = {"status": "disabled"}
            if hasattr(self, "performance_service"):
                performance_health = await self.performance_service.health_check()

            # Current capacity metrics
            capacity_metrics = {
                "max_file_size_mb": self.max_file_size / (1024 * 1024),
                "supported_formats": len(self.supported_formats),
                "processing_profiles": len(self.processing_profiles),
            }

            return {
                "service_status": "healthy" if ocr_available else "degraded",
                "gemini_client_status": client_health.get("status", "unknown"),
                "ocr_available": ocr_available,
                "authentication_method": client_health.get("authentication", {}).get(
                    "method", "unknown"
                ),
                "performance_optimization": performance_health.get(
                    "service_status", "unknown"
                ),
                "capacity_metrics": capacity_metrics,
                "features": [
                    "multi_page_pdf_processing",
                    "image_enhancement",
                    "contract_specific_ocr",
                    "confidence_scoring",
                    "service_role_authentication",
                    "ai_performance_optimization",
                    "prompt_manager_integration",
                    "template_based_extraction",
                    "enhanced_context_processing",
                    "image_semantic_analysis",
                    "property_diagram_analysis",
                    "risk_assessment_from_images",
                    "infrastructure_element_detection",
                ],
                "last_health_check": datetime.now(UTC).isoformat(),
            }

        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            return {
                "service_status": "error",
                "error_message": str(e),
                "last_health_check": datetime.now(UTC).isoformat(),
            }

    async def extract_text(
        self,
        content: bytes,
        content_type: str,
        filename: Optional[str] = None,
        contract_context: Optional[Dict[str, Any]] = None,
        options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Compatibility wrapper for DocumentService integration.
        Maps the simple extract_text interface to the advanced extract_text_from_document method.
        """
        if not filename:
            # Generate a default filename based on content type
            if content_type == "application/pdf":
                filename = "document.pdf"
            elif content_type.startswith("image/"):
                ext = content_type.split("/")[1]
                filename = f"image.{ext}"
            else:
                filename = "document"
        
        # Extract file type from content_type or filename
        if content_type == "application/pdf":
            file_type = "pdf"
        elif content_type.startswith("image/"):
            file_type = content_type.split("/")[1]
        else:
            # Fallback to filename extension
            file_type = Path(filename).suffix.lower().lstrip(".")
        
        # Map options to GeminiOCRService parameters
        options = options or {}
        priority = ProcessingPriority.HIGH if options.get("priority") else ProcessingPriority.STANDARD
        enable_optimization = options.get("enhancement_level", "standard") != "basic"
        
        # Call the advanced method
        return await self.extract_text_from_document(
            file_content=content,
            file_type=file_type,
            filename=filename,
            contract_context=contract_context,
            priority=priority,
            enable_optimization=enable_optimization,
            use_prompt_templates=True,
        )

    async def get_processing_capabilities(self) -> Dict[str, Any]:
        """Get comprehensive OCR service capabilities and status"""
        base_capabilities = {
            "service_available": self.gemini_client is not None,
            "supported_formats": list(self.supported_formats),
            "max_file_size_mb": self.max_file_size / (1024 * 1024),
            "processing_profiles": list(self.processing_profiles.keys()),
            "authentication_method": "unknown",
            "features": [
                "multi_page_pdf_processing",
                "image_enhancement",
                "contract_specific_ocr",
                "confidence_scoring",
                "service_role_authentication",
                "ai_performance_optimization",
                "prompt_manager_integration",
                "template_based_extraction",
                "enhanced_context_processing",
                "image_semantic_analysis",
                "property_diagram_analysis",
                "risk_assessment_from_images",
                "infrastructure_element_detection",
            ],
        }

        # Get authentication method from client
        if self.gemini_client:
            try:
                client_health = await self.gemini_client.health_check()
                base_capabilities["authentication_method"] = client_health.get(
                    "authentication", {}
                ).get("method", "unknown")
            except Exception as e:
                logger.warning(f"Could not get client health: {e}")

        # Add performance metrics if available
        if hasattr(self, "performance_service"):
            try:
                perf_analytics = (
                    await self.performance_service.get_performance_analytics(24)
                )
                base_capabilities["performance_metrics"] = {
                    "cache_hit_rate": perf_analytics.get("cache_hit_rate", 0.0),
                    "average_processing_time_ms": perf_analytics.get(
                        "average_processing_time_ms", 0
                    ),
                    "average_confidence_score": perf_analytics.get(
                        "average_confidence_score", 0.0
                    ),
                    "cost_efficiency": perf_analytics.get("cost_efficiency", {}),
                }
            except Exception as e:
                logger.warning(f"Could not fetch performance metrics: {str(e)}")

        return base_capabilities

    async def get_capabilities(self) -> Dict[str, Any]:
        """
        Compatibility wrapper for DocumentService integration.
        Maps get_capabilities to get_processing_capabilities with simplified format.
        """
        full_capabilities = await self.get_processing_capabilities()
        
        # Simplify the response format to match what DocumentService expects
        return {
            "service_available": full_capabilities.get("service_available", False),
            "providers": {
                "gemini": {
                    "status": "available" if full_capabilities.get("service_available") else "unavailable",
                    "model": "gemini-2.5-pro",
                    "supported_formats": full_capabilities.get("supported_formats", []),
                    "max_file_size_mb": full_capabilities.get("max_file_size_mb", 50),
                }
            },
            "supported_formats": full_capabilities.get("supported_formats", []),
            "confidence_threshold": 0.6,
            "max_file_size_mb": full_capabilities.get("max_file_size_mb", 50),
        }
