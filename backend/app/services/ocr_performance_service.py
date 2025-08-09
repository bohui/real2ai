"""
Advanced OCR Performance Optimization Service for Real2.AI
Intelligent caching, quality assessment, and performance monitoring for Gemini OCR
"""

import asyncio
import hashlib
import logging
import time
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta, UTC
from dataclasses import dataclass, asdict
from enum import Enum
import json

from app.core.config import get_settings
from app.clients.factory import get_supabase_client

logger = logging.getLogger(__name__)


class ProcessingPriority(Enum):
    LOW = "low"
    STANDARD = "standard"
    HIGH = "high"
    CRITICAL = "critical"


class QualityTier(Enum):
    BASIC = "basic"
    ENHANCED = "enhanced"
    PREMIUM = "premium"
    ENTERPRISE = "enterprise"


@dataclass
class OCRPerformanceMetrics:
    """Performance metrics for OCR operations"""

    processing_time_ms: float
    confidence_score: float
    character_count: int
    word_count: int
    pages_processed: int
    cache_hit: bool
    quality_tier: QualityTier
    gemini_model_used: str
    enhancement_applied: List[str]
    cost_estimate_usd: float
    timestamp: datetime


@dataclass
class OCRCacheEntry:
    """Cached OCR result entry"""

    document_hash: str
    extraction_result: Dict[str, Any]
    processing_metrics: OCRPerformanceMetrics
    contract_context_hash: str
    expiry_time: datetime
    usage_count: int
    last_accessed: datetime


class OCRPerformanceService:
    """Advanced OCR performance optimization and monitoring service"""

    def __init__(self):
        self.settings = get_settings()
        # Database client will be initialized lazily when needed

        # Performance tracking
        self.metrics_history: List[OCRPerformanceMetrics] = []
        self.cache_storage: Dict[str, OCRCacheEntry] = {}

        # Cost tracking
        self.daily_cost_tracker = 0.0
        self.user_cost_tracker: Dict[str, float] = {}

        # Quality assessment weights
        self.quality_weights = {
            "extraction_confidence": 0.4,
            "contract_terms_detected": 0.3,
            "text_coherence": 0.2,
            "processing_efficiency": 0.1,
        }

        # Performance thresholds
        self.performance_thresholds = {
            "excellent": {"confidence": 0.95, "processing_time_ms": 5000},
            "good": {"confidence": 0.85, "processing_time_ms": 10000},
            "acceptable": {"confidence": 0.70, "processing_time_ms": 20000},
            "poor": {"confidence": 0.50, "processing_time_ms": 30000},
        }

    async def initialize(self):
        """Initialize performance service"""
        try:
            # Load historical metrics from database
            await self._load_historical_metrics()

            # Load cache entries
            await self._load_cache_entries()

            # Initialize cost tracking
            await self._initialize_cost_tracking()

            logger.info("OCR Performance Service initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize OCR Performance Service: {str(e)}")
            raise

    async def optimize_ocr_request(
        self,
        file_content: bytes,
        file_type: str,
        filename: str,
        contract_context: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
        priority: ProcessingPriority = ProcessingPriority.STANDARD,
    ) -> Tuple[Dict[str, Any], bool]:
        """
        Optimize OCR request with intelligent caching and quality selection

        Returns:
            Tuple[OCR Result, Cache Hit]
        """

        # Generate content hash for caching
        document_hash = self._generate_document_hash(file_content, file_type)
        context_hash = self._generate_context_hash(contract_context)
        cache_key = f"{document_hash}_{context_hash}"

        # Check cache first
        cache_result = await self._check_cache(cache_key)
        if cache_result:
            logger.info(f"Cache hit for document hash {document_hash[:8]}...")
            await self._update_cache_usage(cache_key)
            return cache_result.extraction_result, True

        # Check cost limits
        if not await self._check_cost_limits(user_id):
            raise Exception("OCR cost limit exceeded")

        # Determine optimal quality tier
        quality_tier = await self._determine_quality_tier(
            file_content, file_type, priority, user_id
        )

        # Track processing start
        start_time = time.time()

        # Perform OCR (this would call the actual Gemini OCR service)
        ocr_result = await self._perform_optimized_ocr(
            file_content, file_type, filename, contract_context, quality_tier
        )

        # Calculate metrics
        processing_time_ms = (time.time() - start_time) * 1000
        metrics = await self._calculate_metrics(
            ocr_result, processing_time_ms, quality_tier, False
        )

        # Store in cache
        await self._store_in_cache(cache_key, ocr_result, metrics, contract_context)

        # Update cost tracking
        await self._update_cost_tracking(user_id, metrics.cost_estimate_usd)

        # Store metrics for analysis
        await self._store_metrics(metrics)

        return ocr_result, False

    async def assess_extraction_quality(
        self,
        extraction_result: Dict[str, Any],
        contract_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Comprehensive quality assessment of OCR extraction"""

        extracted_text = extraction_result.get("extracted_text", "")
        confidence = extraction_result.get("extraction_confidence", 0.0)

        # Base quality metrics
        quality_scores = {
            "extraction_confidence": confidence,
            "text_length_score": self._assess_text_length(extracted_text),
            "contract_relevance_score": self._assess_contract_relevance(extracted_text),
            "text_coherence_score": self._assess_text_coherence(extracted_text),
            "formatting_preservation_score": self._assess_formatting_preservation(
                extracted_text
            ),
        }

        # Contract-specific quality assessment
        if contract_context:
            quality_scores.update(
                await self._assess_contract_specific_quality(
                    extracted_text, contract_context
                )
            )

        # Calculate overall quality score
        overall_score = sum(
            score * self.quality_weights.get(metric, 0.1)
            for metric, score in quality_scores.items()
        )

        # Determine quality tier
        quality_tier = self._determine_quality_tier_from_score(overall_score)

        # Generate improvement recommendations
        recommendations = await self._generate_quality_recommendations(
            quality_scores, extraction_result
        )

        return {
            "overall_quality_score": min(1.0, overall_score),
            "quality_tier": quality_tier.value,
            "quality_breakdown": quality_scores,
            "improvement_recommendations": recommendations,
            "meets_minimum_threshold": overall_score
            >= self.settings.ocr_minimum_confidence,
            "processing_assessment": self._assess_processing_performance(
                extraction_result
            ),
        }

    async def get_performance_analytics(
        self, time_range_hours: int = 24, user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get comprehensive performance analytics"""

        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=time_range_hours)

        # Filter metrics by time range and user
        relevant_metrics = [
            m
            for m in self.metrics_history
            if m.timestamp >= cutoff_time and (not user_id or user_id in str(m))
        ]

        if not relevant_metrics:
            return {"message": "No metrics available for the specified time range"}

        # Calculate analytics
        total_requests = len(relevant_metrics)
        cache_hits = sum(1 for m in relevant_metrics if m.cache_hit)
        avg_processing_time = (
            sum(m.processing_time_ms for m in relevant_metrics) / total_requests
        )
        avg_confidence = (
            sum(m.confidence_score for m in relevant_metrics) / total_requests
        )
        total_cost = sum(m.cost_estimate_usd for m in relevant_metrics)

        # Performance distribution
        performance_distribution = {
            "excellent": 0,
            "good": 0,
            "acceptable": 0,
            "poor": 0,
        }

        for metric in relevant_metrics:
            if metric.confidence_score >= 0.95 and metric.processing_time_ms <= 5000:
                performance_distribution["excellent"] += 1
            elif metric.confidence_score >= 0.85 and metric.processing_time_ms <= 10000:
                performance_distribution["good"] += 1
            elif metric.confidence_score >= 0.70 and metric.processing_time_ms <= 20000:
                performance_distribution["acceptable"] += 1
            else:
                performance_distribution["poor"] += 1

        # Quality tier distribution
        quality_tier_distribution = {}
        for metric in relevant_metrics:
            tier = metric.quality_tier.value
            quality_tier_distribution[tier] = quality_tier_distribution.get(tier, 0) + 1

        return {
            "time_range_hours": time_range_hours,
            "total_requests": total_requests,
            "cache_hit_rate": cache_hits / total_requests if total_requests > 0 else 0,
            "average_processing_time_ms": avg_processing_time,
            "average_confidence_score": avg_confidence,
            "total_cost_usd": total_cost,
            "performance_distribution": performance_distribution,
            "quality_tier_distribution": quality_tier_distribution,
            "cost_efficiency": {
                "cost_per_document": (
                    total_cost / total_requests if total_requests > 0 else 0
                ),
                "cost_per_confidence_point": (
                    total_cost / (avg_confidence * total_requests)
                    if avg_confidence > 0 and total_requests > 0
                    else 0
                ),
            },
            "trend_analysis": await self._analyze_performance_trends(relevant_metrics),
        }

    async def optimize_batch_processing(
        self,
        document_batch: List[Dict[str, Any]],
        user_id: str,
        batch_context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Optimize batch OCR processing with intelligent scheduling"""

        total_docs = len(document_batch)

        # Analyze batch characteristics
        batch_analysis = await self._analyze_batch_characteristics(document_batch)

        # Determine optimal processing strategy
        processing_strategy = await self._determine_batch_strategy(
            batch_analysis, user_id, batch_context
        )

        # Estimate costs and timing
        cost_estimate = await self._estimate_batch_costs(
            document_batch, processing_strategy
        )
        time_estimate = await self._estimate_batch_timing(
            document_batch, processing_strategy
        )

        # Check if batch processing is cost-effective
        cost_effective = (
            cost_estimate["total_cost"] <= self.settings.ocr_user_cost_limit_usd
        )

        return {
            "batch_analysis": batch_analysis,
            "recommended_strategy": processing_strategy,
            "cost_estimate": cost_estimate,
            "time_estimate": time_estimate,
            "cost_effective": cost_effective,
            "optimization_recommendations": await self._generate_batch_recommendations(
                batch_analysis, processing_strategy, cost_estimate
            ),
            "cache_opportunities": await self._identify_cache_opportunities(
                document_batch
            ),
        }

    async def health_check(self) -> Dict[str, Any]:
        """Comprehensive health check of OCR service"""

        try:
            # Check service availability
            service_available = True  # Would check actual Gemini API

            # Check cache performance
            cache_stats = await self._get_cache_statistics()

            # Check cost tracking
            cost_status = await self._get_cost_status()

            # Check performance trends
            recent_performance = await self._get_recent_performance_summary()

            return {
                "service_status": "healthy" if service_available else "unhealthy",
                "cache_performance": cache_stats,
                "cost_tracking": cost_status,
                "recent_performance": recent_performance,
                "recommendations": await self._generate_health_recommendations(),
                "last_updated": datetime.now(timezone.utc).isoformat(),
            }

        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            return {
                "service_status": "error",
                "error_message": str(e),
                "last_updated": datetime.now(timezone.utc).isoformat(),
            }

    # Private helper methods

    def _generate_document_hash(self, file_content: bytes, file_type: str) -> str:
        """Generate hash for document content"""
        content_hash = hashlib.sha256(file_content).hexdigest()
        return f"{file_type}_{content_hash[:16]}"

    def _generate_context_hash(self, contract_context: Optional[Dict[str, Any]]) -> str:
        """Generate hash for contract context"""
        if not contract_context:
            return "no_context"

        context_str = json.dumps(contract_context, sort_keys=True)
        return hashlib.md5(context_str.encode()).hexdigest()[:8]

    async def _check_cache(self, cache_key: str) -> Optional[OCRCacheEntry]:
        """Check if result exists in cache"""
        entry = self.cache_storage.get(cache_key)
        if entry and entry.expiry_time > datetime.now(timezone.utc):
            return entry
        elif entry:  # Expired entry
            del self.cache_storage[cache_key]
        return None

    async def _check_cost_limits(self, user_id: Optional[str]) -> bool:
        """Check if cost limits are exceeded"""
        if not self.settings.ocr_cost_tracking_enabled:
            return True

        # Check daily limit
        if self.daily_cost_tracker >= self.settings.ocr_daily_cost_limit_usd:
            return False

        # Check user limit
        if user_id:
            user_cost = self.user_cost_tracker.get(user_id, 0.0)
            if user_cost >= self.settings.ocr_user_cost_limit_usd:
                return False

        return True

    async def _determine_quality_tier(
        self,
        file_content: bytes,
        file_type: str,
        priority: ProcessingPriority,
        user_id: Optional[str],
    ) -> QualityTier:
        """Determine optimal quality tier for processing"""

        # Base tier on priority
        if priority == ProcessingPriority.CRITICAL:
            base_tier = QualityTier.ENTERPRISE
        elif priority == ProcessingPriority.HIGH:
            base_tier = QualityTier.PREMIUM
        elif priority == ProcessingPriority.STANDARD:
            base_tier = QualityTier.ENHANCED
        else:
            base_tier = QualityTier.BASIC

        # Adjust based on file characteristics
        file_size_mb = len(file_content) / (1024 * 1024)
        if file_size_mb > 10:  # Large files need better processing
            if base_tier == QualityTier.BASIC:
                base_tier = QualityTier.ENHANCED
            elif base_tier == QualityTier.ENHANCED:
                base_tier = QualityTier.PREMIUM

        # Check if user has sufficient credits/subscription for tier
        # This would integrate with user subscription system

        return base_tier

    def _determine_quality_tier_from_score(self, quality_score: float) -> QualityTier:
        """Determine quality tier from overall score"""
        if quality_score >= 0.9:
            return QualityTier.ENTERPRISE
        elif quality_score >= 0.8:
            return QualityTier.PREMIUM
        elif quality_score >= 0.6:
            return QualityTier.ENHANCED
        else:
            return QualityTier.BASIC

    async def _perform_optimized_ocr(
        self,
        file_content: bytes,
        file_type: str,
        filename: str,
        contract_context: Optional[Dict[str, Any]],
        quality_tier: QualityTier,
    ) -> Dict[str, Any]:
        """Perform OCR with quality tier optimizations"""

        # This would call the actual Gemini OCR service with optimizations
        # For now, return a simulated result with quality tier adjustments

        base_confidence = 0.75
        quality_multiplier = {
            QualityTier.BASIC: 1.0,
            QualityTier.ENHANCED: 1.1,
            QualityTier.PREMIUM: 1.2,
            QualityTier.ENTERPRISE: 1.3,
        }

        adjusted_confidence = min(
            0.98, base_confidence * quality_multiplier[quality_tier]
        )

        return {
            "extracted_text": f"Sample contract text from {filename}...",
            "extraction_method": f"gemini-2.5-flash-{quality_tier.value}",
            "extraction_confidence": adjusted_confidence,
            "character_count": 2500,
            "word_count": 450,
            "quality_tier_used": quality_tier.value,
            "processing_details": {
                "pages_processed": 1,
                "enhancement_applied": [f"{quality_tier.value}_processing"],
                "contract_terms_found": 12,
            },
        }

    async def _calculate_metrics(
        self,
        ocr_result: Dict[str, Any],
        processing_time_ms: float,
        quality_tier: QualityTier,
        cache_hit: bool,
    ) -> OCRPerformanceMetrics:
        """Calculate comprehensive performance metrics"""

        # Estimate cost based on quality tier and processing
        cost_estimates = {
            QualityTier.BASIC: 0.01,
            QualityTier.ENHANCED: 0.02,
            QualityTier.PREMIUM: 0.04,
            QualityTier.ENTERPRISE: 0.08,
        }

        return OCRPerformanceMetrics(
            processing_time_ms=processing_time_ms,
            confidence_score=ocr_result.get("extraction_confidence", 0.0),
            character_count=ocr_result.get("character_count", 0),
            word_count=ocr_result.get("word_count", 0),
            pages_processed=ocr_result.get("processing_details", {}).get(
                "pages_processed", 1
            ),
            cache_hit=cache_hit,
            quality_tier=quality_tier,
            gemini_model_used="gemini-2.5-flash",
            enhancement_applied=ocr_result.get("processing_details", {}).get(
                "enhancement_applied", []
            ),
            cost_estimate_usd=cost_estimates[quality_tier],
            timestamp=datetime.now(timezone.utc),
        )

    # Placeholder methods for complex analysis functions
    async def _load_historical_metrics(self):
        pass

    async def _load_cache_entries(self):
        pass

    async def _initialize_cost_tracking(self):
        pass

    async def _update_cache_usage(self, cache_key: str):
        pass

    async def _store_in_cache(
        self,
        cache_key: str,
        result: Dict,
        metrics: OCRPerformanceMetrics,
        context: Optional[Dict],
    ):
        pass

    async def _update_cost_tracking(self, user_id: Optional[str], cost: float):
        pass

    async def _store_metrics(self, metrics: OCRPerformanceMetrics):
        pass

    def _assess_text_length(self, text: str) -> float:
        return min(1.0, len(text) / 1000)

    def _assess_contract_relevance(self, text: str) -> float:
        return 0.8  # Placeholder

    def _assess_text_coherence(self, text: str) -> float:
        return 0.85  # Placeholder

    def _assess_formatting_preservation(self, text: str) -> float:
        return 0.75  # Placeholder

    async def _assess_contract_specific_quality(
        self, text: str, context: Dict
    ) -> Dict[str, float]:
        return {"contract_completeness": 0.9, "legal_terms_accuracy": 0.85}

    async def _generate_quality_recommendations(
        self, scores: Dict, result: Dict
    ) -> List[str]:
        return ["Consider higher quality tier for better results"]

    def _assess_processing_performance(self, result: Dict) -> Dict[str, Any]:
        return {"efficiency_score": 0.8, "resource_usage": "optimal"}

    async def _analyze_performance_trends(self, metrics: List) -> Dict[str, Any]:
        return {"trend": "improving", "confidence_trend": "stable"}

    async def _analyze_batch_characteristics(self, batch: List) -> Dict[str, Any]:
        return {"total_documents": len(batch), "estimated_complexity": "medium"}

    async def _determine_batch_strategy(
        self, analysis: Dict, user_id: str, context: Dict
    ) -> Dict[str, Any]:
        return {"strategy": "parallel", "max_concurrent": 3}

    async def _estimate_batch_costs(
        self, batch: List, strategy: Dict
    ) -> Dict[str, Any]:
        return {"total_cost": len(batch) * 0.02, "cost_per_document": 0.02}

    async def _estimate_batch_timing(
        self, batch: List, strategy: Dict
    ) -> Dict[str, Any]:
        return {"estimated_minutes": len(batch) * 2, "parallel_processing": True}

    async def _generate_batch_recommendations(
        self, analysis: Dict, strategy: Dict, cost: Dict
    ) -> List[str]:
        return ["Use parallel processing for better efficiency"]

    async def _identify_cache_opportunities(self, batch: List) -> Dict[str, Any]:
        return {"cacheable_documents": 0, "potential_savings": 0.0}

    async def _get_cache_statistics(self) -> Dict[str, Any]:
        return {"cache_size": len(self.cache_storage), "hit_rate": 0.75}

    async def _get_cost_status(self) -> Dict[str, Any]:
        return {
            "daily_spent": self.daily_cost_tracker,
            "daily_limit": self.settings.ocr_daily_cost_limit_usd,
        }

    async def _get_recent_performance_summary(self) -> Dict[str, Any]:
        return {"avg_confidence": 0.85, "avg_processing_time_ms": 8000}

    async def _generate_health_recommendations(self) -> List[str]:
        return ["OCR service operating normally"]
