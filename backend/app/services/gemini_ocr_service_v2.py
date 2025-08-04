"""
Gemini OCR Service V2 - Refactored to use GeminiClient
Provides OCR capabilities for contract document processing using proper client architecture
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path

from fastapi import HTTPException

from app.core.config import get_settings
from app.models.contract_state import ProcessingStatus
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


class GeminiOCRServiceV2:
    """Advanced OCR service using GeminiClient for contract document processing"""

    def __init__(self):
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
            if hasattr(self.gemini_client, 'ocr') and self.gemini_client.ocr:
                logger.info("Gemini OCR service initialized successfully with GeminiClient")
                
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
                detail="Gemini OCR service unavailable - connection failed"
            )
        except Exception as e:
            logger.error(f"Failed to initialize Gemini OCR service: {str(e)}")
            raise HTTPException(
                status_code=503,
                detail=f"Gemini OCR service initialization failed: {str(e)}"
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
    ) -> Dict[str, Any]:
        """Extract text from document using GeminiClient's OCR capabilities
        
        Args:
            file_content: Raw file bytes
            file_type: File extension (pdf, jpg, png, etc.)
            filename: Original filename
            contract_context: Additional context for better extraction
            user_id: User ID for cost tracking and optimization
            priority: Processing priority level
            enable_optimization: Enable AI performance optimization
            
        Returns:
            Dict containing extracted text, confidence, and metadata
        """
        if not self.gemini_client:
            raise HTTPException(
                status_code=503,
                detail="Gemini OCR service not initialized"
            )

        try:
            # Validate file
            self._validate_file(file_content, file_type)

            # Select processing profile based on priority
            profile = self._select_processing_profile(priority, len(file_content))
            
            # Prepare contract context for OCR
            ocr_context = self._prepare_ocr_context(contract_context, profile)

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
                result.update({
                    "service": "GeminiOCRServiceV2",
                    "processing_profile": profile,
                    "file_processed": filename,
                    "optimization_enabled": enable_optimization,
                })
                
                return result
                
            except ClientQuotaExceededError as e:
                logger.error(f"Gemini quota exceeded: {e}")
                raise HTTPException(
                    status_code=429,
                    detail="OCR quota exceeded. Please try again later."
                )
            except ClientError as e:
                logger.error(f"Gemini client error during OCR: {e}")
                raise HTTPException(
                    status_code=500,
                    detail=f"OCR processing failed: {str(e)}"
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
                "extraction_timestamp": datetime.utcnow().isoformat(),
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
                status_code=503,
                detail="Gemini OCR service not initialized"
            )

        try:
            # Validate file
            self._validate_file(file_content, file_type)

            # Use GeminiClient's document analysis
            result = await self.gemini_client.analyze_document(
                content=file_content,
                content_type=f"application/{file_type.lower()}",
                contract_context=contract_context,
                analysis_options=analysis_options,
            )
            
            # Add service metadata
            result.update({
                "service": "GeminiOCRServiceV2",
                "file_processed": filename,
                "analysis_timestamp": datetime.utcnow().isoformat(),
            })
            
            return result
            
        except ClientError as e:
            logger.error(f"Document analysis failed: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Document analysis failed: {str(e)}"
            )

    def _validate_file(self, file_content: bytes, file_type: str):
        """Validate file size and format"""
        # Check file size
        if len(file_content) > self.max_file_size:
            raise HTTPException(
                status_code=413,
                detail=f"File too large for OCR. Maximum size: {self.max_file_size / 1024 / 1024}MB"
            )

        # Check file format
        if file_type.lower() not in self.supported_formats:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file format for OCR: {file_type}"
            )

        # Check if file is empty
        if len(file_content) == 0:
            raise HTTPException(
                status_code=400,
                detail="Empty file cannot be processed"
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

    def _prepare_ocr_context(
        self, 
        contract_context: Optional[Dict[str, Any]], 
        profile: str
    ) -> Dict[str, Any]:
        """Prepare context for OCR processing"""
        ocr_context = contract_context or {}
        
        # Add profile-specific settings
        profile_config = self.processing_profiles.get(
            profile, self.processing_profiles["balanced"]
        )
        
        ocr_context.update({
            "processing_profile": profile,
            "profile_config": profile_config,
            "service_version": "v2",
        })
        
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

    async def health_check(self) -> Dict[str, Any]:
        """Comprehensive health check for OCR service"""
        try:
            # Check if client is initialized
            if not self.gemini_client:
                return {
                    "service_status": "not_initialized",
                    "error": "GeminiClient not initialized",
                    "last_health_check": datetime.utcnow().isoformat(),
                }

            # Get client health status
            client_health = await self.gemini_client.health_check()
            
            # Check OCR specific health
            ocr_available = (
                client_health.get("status") == "healthy" and
                client_health.get("ocr_status", "unknown") == "healthy"
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
                "authentication_method": client_health.get("authentication", {}).get("method", "unknown"),
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
                ],
                "last_health_check": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            return {
                "service_status": "error",
                "error_message": str(e),
                "last_health_check": datetime.utcnow().isoformat(),
            }

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
            ],
        }

        # Get authentication method from client
        if self.gemini_client:
            try:
                client_health = await self.gemini_client.health_check()
                base_capabilities["authentication_method"] = (
                    client_health.get("authentication", {}).get("method", "unknown")
                )
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