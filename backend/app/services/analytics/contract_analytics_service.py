"""
Contract Analytics Service for Contract Type Taxonomy

Provides analytics and tracking for the contract type taxonomy system:
- Contract type distribution and trends
- OCR inference accuracy tracking
- Purchase method and lease category analytics
- Confidence score analysis
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict

from app.services.repositories.contracts_repository import ContractsRepository
from app.database.connection import get_service_role_connection
from app.schema.enums import ContractType, PurchaseMethod, UseCategory, AustralianState


logger = logging.getLogger(__name__)


class ContractAnalyticsService:
    """Service for contract type taxonomy analytics and tracking"""

    def __init__(self):
        self.contracts_repo = ContractsRepository()

    async def get_taxonomy_analytics(
        self, 
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get comprehensive analytics for contract type taxonomy.
        
        Args:
            start_date: Optional start date for filtering
            end_date: Optional end date for filtering
            
        Returns:
            Dictionary with comprehensive taxonomy analytics
        """
        try:
            # Get basic contract stats (already includes taxonomy fields)
            basic_stats = await self.contracts_repo.get_contract_stats()
            
            # Get OCR inference analytics
            ocr_analytics = await self._get_ocr_inference_analytics(start_date, end_date)
            
            # Get confidence score analytics
            confidence_analytics = await self._get_confidence_analytics()
            
            # Get trend analytics
            trend_analytics = await self._get_trend_analytics(start_date, end_date)
            
            # Get geographic distribution
            geographic_analytics = await self._get_geographic_distribution()
            
            return {
                "basic_stats": basic_stats,
                "ocr_inference": ocr_analytics,
                "confidence_metrics": confidence_analytics,
                "trends": trend_analytics,
                "geographic_distribution": geographic_analytics,
                "generated_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to generate taxonomy analytics: {e}")
            raise

    async def _get_ocr_inference_analytics(
        self, 
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get analytics on OCR inference accuracy and usage"""
        async with get_service_role_connection() as conn:
            date_filter = ""
            params = []
            
            if start_date and end_date:
                date_filter = "WHERE created_at >= $1 AND created_at <= $2"
                params = [start_date, end_date]
            
            # OCR inference success rates
            result = await conn.fetch(f"""
                SELECT 
                    contract_type,
                    COUNT(*) as total_contracts,
                    COUNT(purchase_method) as with_purchase_method,
                    COUNT(use_category) as with_use_category,
                    COUNT(CASE WHEN ocr_confidence IS NOT NULL AND ocr_confidence != '{{}}'::jsonb 
                          THEN 1 END) as with_confidence_scores
                FROM contracts 
                {date_filter}
                GROUP BY contract_type
                ORDER BY total_contracts DESC
            """, *params)
            
            inference_stats = {}
            for row in result:
                contract_type = row['contract_type']
                total = row['total_contracts']
                
                if contract_type == 'purchase_agreement':
                    inference_rate = row['with_purchase_method'] / total if total > 0 else 0
                elif contract_type == 'lease_agreement':
                    inference_rate = row['with_use_category'] / total if total > 0 else 0
                else:
                    inference_rate = 0
                
                inference_stats[contract_type] = {
                    'total_contracts': total,
                    'with_inference': row['with_purchase_method'] if contract_type == 'purchase_agreement' else row['with_use_category'],
                    'inference_success_rate': inference_rate,
                    'with_confidence_scores': row['with_confidence_scores'],
                    'confidence_rate': row['with_confidence_scores'] / total if total > 0 else 0
                }
            
            return {
                "by_contract_type": inference_stats,
                "overall_inference_success_rate": await self._calculate_overall_inference_rate(),
                "low_confidence_alerts": await self._get_low_confidence_contracts()
            }

    async def _get_confidence_analytics(self) -> Dict[str, Any]:
        """Get analytics on OCR confidence scores"""
        async with get_service_role_connection() as conn:
            # Confidence score distribution for purchase methods
            purchase_confidence = await conn.fetch("""
                SELECT 
                    purchase_method,
                    AVG((ocr_confidence->>'purchase_method')::float) as avg_confidence,
                    MIN((ocr_confidence->>'purchase_method')::float) as min_confidence,
                    MAX((ocr_confidence->>'purchase_method')::float) as max_confidence,
                    COUNT(*) as count
                FROM contracts 
                WHERE contract_type = 'purchase_agreement' 
                AND purchase_method IS NOT NULL
                AND ocr_confidence ? 'purchase_method'
                GROUP BY purchase_method
                ORDER BY avg_confidence DESC
            """)
            
            # Confidence score distribution for lease categories
            lease_confidence = await conn.fetch("""
                SELECT 
                    use_category,
                    AVG((ocr_confidence->>'use_category')::float) as avg_confidence,
                    MIN((ocr_confidence->>'use_category')::float) as min_confidence,
                    MAX((ocr_confidence->>'use_category')::float) as max_confidence,
                    COUNT(*) as count
                FROM contracts 
                WHERE contract_type = 'lease_agreement' 
                AND use_category IS NOT NULL
                AND ocr_confidence ? 'use_category'
                GROUP BY use_category
                ORDER BY avg_confidence DESC
            """)
            
            return {
                "purchase_method_confidence": [
                    {
                        "method": row['purchase_method'],
                        "avg_confidence": float(row['avg_confidence']),
                        "min_confidence": float(row['min_confidence']),
                        "max_confidence": float(row['max_confidence']),
                        "sample_count": row['count']
                    }
                    for row in purchase_confidence
                ],
                "use_category_confidence": [
                    {
                        "category": row['use_category'],
                        "avg_confidence": float(row['avg_confidence']),
                        "min_confidence": float(row['min_confidence']),
                        "max_confidence": float(row['max_confidence']),
                        "sample_count": row['count']
                    }
                    for row in lease_confidence
                ]
            }

    async def _get_trend_analytics(
        self, 
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get trend analytics for contract types over time"""
        async with get_service_role_connection() as conn:
            # Default to last 30 days if no dates provided
            if not start_date:
                start_date = datetime.utcnow() - timedelta(days=30)
            if not end_date:
                end_date = datetime.utcnow()
            
            # Daily contract type trends
            daily_trends = await conn.fetch("""
                SELECT 
                    DATE(created_at) as date,
                    contract_type,
                    purchase_method,
                    use_category,
                    COUNT(*) as count
                FROM contracts 
                WHERE created_at >= $1 AND created_at <= $2
                GROUP BY DATE(created_at), contract_type, purchase_method, use_category
                ORDER BY date DESC, count DESC
            """, start_date, end_date)
            
            # Organize trends by date
            trends_by_date = defaultdict(lambda: defaultdict(int))
            for row in daily_trends:
                date_str = row['date'].isoformat()
                trends_by_date[date_str]['total'] += row['count']
                trends_by_date[date_str][row['contract_type']] += row['count']
                
                if row['purchase_method']:
                    trends_by_date[date_str][f"purchase_{row['purchase_method']}"] += row['count']
                if row['use_category']:
                    trends_by_date[date_str][f"lease_{row['use_category']}"] += row['count']
            
            return {
                "daily_trends": dict(trends_by_date),
                "period": {
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                    "days": (end_date - start_date).days
                }
            }

    async def _get_geographic_distribution(self) -> Dict[str, Any]:
        """Get geographic distribution of contract types"""
        async with get_service_role_connection() as conn:
            geo_distribution = await conn.fetch("""
                SELECT 
                    australian_state,
                    contract_type,
                    purchase_method,
                    use_category,
                    COUNT(*) as count
                FROM contracts 
                GROUP BY australian_state, contract_type, purchase_method, use_category
                ORDER BY australian_state, count DESC
            """)
            
            # Organize by state
            by_state = defaultdict(lambda: defaultdict(int))
            for row in geo_distribution:
                state = row['australian_state']
                by_state[state]['total'] += row['count']
                by_state[state][row['contract_type']] += row['count']
                
                if row['purchase_method']:
                    by_state[state][f"purchase_{row['purchase_method']}"] += row['count']
                if row['use_category']:
                    by_state[state][f"lease_{row['use_category']}"] += row['count']
            
            return dict(by_state)

    async def _calculate_overall_inference_rate(self) -> float:
        """Calculate overall OCR inference success rate"""
        async with get_service_role_connection() as conn:
            result = await conn.fetchrow("""
                SELECT 
                    COUNT(*) as total,
                    COUNT(CASE WHEN contract_type = 'purchase_agreement' AND purchase_method IS NOT NULL 
                              THEN 1 END) as purchase_with_method,
                    COUNT(CASE WHEN contract_type = 'lease_agreement' AND use_category IS NOT NULL 
                              THEN 1 END) as lease_with_category,
                    COUNT(CASE WHEN contract_type = 'purchase_agreement' THEN 1 END) as total_purchase,
                    COUNT(CASE WHEN contract_type = 'lease_agreement' THEN 1 END) as total_lease
                FROM contracts
            """)
            
            if result['total_purchase'] + result['total_lease'] == 0:
                return 0.0
            
            successful_inferences = result['purchase_with_method'] + result['lease_with_category']
            total_requiring_inference = result['total_purchase'] + result['total_lease']
            
            return successful_inferences / total_requiring_inference if total_requiring_inference > 0 else 0.0

    async def _get_low_confidence_contracts(self, threshold: float = 0.7) -> List[Dict[str, Any]]:
        """Get contracts with low OCR confidence scores"""
        async with get_service_role_connection() as conn:
            low_confidence = await conn.fetch("""
                SELECT 
                    id,
                    content_hash,
                    contract_type,
                    purchase_method,
                    use_category,
                    ocr_confidence,
                    created_at
                FROM contracts 
                WHERE (
                    (contract_type = 'purchase_agreement' 
                     AND (ocr_confidence->>'purchase_method')::float < $1)
                    OR 
                    (contract_type = 'lease_agreement' 
                     AND (ocr_confidence->>'use_category')::float < $1)
                )
                ORDER BY created_at DESC
                LIMIT 100
            """, threshold)
            
            return [
                {
                    "contract_id": str(row['id']),
                    "content_hash": row['content_hash'],
                    "contract_type": row['contract_type'],
                    "purchase_method": row['purchase_method'],
                    "use_category": row['use_category'],
                    "confidence_score": (
                        row['ocr_confidence'].get('purchase_method') if row['contract_type'] == 'purchase_agreement'
                        else row['ocr_confidence'].get('use_category')
                    ),
                    "created_at": row['created_at'].isoformat()
                }
                for row in low_confidence
            ]

    async def track_inference_performance(
        self, 
        contract_id: str, 
        inference_result: Dict[str, Any],
        manual_validation: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Track OCR inference performance for continuous improvement.
        
        Args:
            contract_id: Contract ID
            inference_result: OCR inference results
            manual_validation: Optional manual validation results for accuracy tracking
        """
        try:
            # This could be extended to store performance metrics in a dedicated table
            # For now, we'll log the performance data
            
            performance_data = {
                "contract_id": contract_id,
                "inference_timestamp": datetime.utcnow().isoformat(),
                "contract_type": inference_result.get("contract_type"),
                "inferred_purchase_method": inference_result.get("purchase_method"),
                "inferred_use_category": inference_result.get("use_category"),
                "confidence_scores": inference_result.get("confidence_scores", {}),
                "evidence": inference_result.get("inference_evidence", {})
            }
            
            if manual_validation:
                performance_data["manual_validation"] = manual_validation
                performance_data["accuracy_check"] = self._calculate_accuracy(
                    inference_result, manual_validation
                )
            
            logger.info(
                "OCR inference performance tracked",
                extra={"performance_data": performance_data}
            )
            
        except Exception as e:
            logger.error(f"Failed to track inference performance: {e}")

    def _calculate_accuracy(
        self, 
        inference_result: Dict[str, Any], 
        manual_validation: Dict[str, Any]
    ) -> Dict[str, float]:
        """Calculate accuracy of OCR inference against manual validation"""
        accuracy = {}
        
        # Check purchase method accuracy
        if inference_result.get("purchase_method") and manual_validation.get("purchase_method"):
            accuracy["purchase_method"] = (
                1.0 if inference_result["purchase_method"] == manual_validation["purchase_method"]
                else 0.0
            )
        
        # Check lease category accuracy
        if inference_result.get("use_category") and manual_validation.get("use_category"):
            accuracy["use_category"] = (
                1.0 if inference_result["use_category"] == manual_validation["use_category"]
                else 0.0
            )
        
        return accuracy

    async def get_performance_insights(self) -> Dict[str, Any]:
        """Get insights for improving OCR inference performance"""
        confidence_analytics = await self._get_confidence_analytics()
        low_confidence = await self._get_low_confidence_contracts(threshold=0.8)
        
        insights = {
            "improvement_opportunities": [],
            "high_performing_categories": [],
            "low_confidence_patterns": []
        }
        
        # Analyze purchase method performance
        for method_data in confidence_analytics["purchase_method_confidence"]:
            if method_data["avg_confidence"] < 0.8:
                insights["improvement_opportunities"].append({
                    "category": "purchase_method",
                    "value": method_data["method"],
                    "avg_confidence": method_data["avg_confidence"],
                    "sample_count": method_data["sample_count"],
                    "recommendation": f"Improve OCR patterns for {method_data['method']} detection"
                })
            elif method_data["avg_confidence"] > 0.9:
                insights["high_performing_categories"].append({
                    "category": "purchase_method",
                    "value": method_data["method"],
                    "avg_confidence": method_data["avg_confidence"]
                })
        
        # Analyze lease category performance
        for category_data in confidence_analytics["use_category_confidence"]:
            if category_data["avg_confidence"] < 0.8:
                insights["improvement_opportunities"].append({
                    "category": "use_category",
                    "value": category_data["category"],
                    "avg_confidence": category_data["avg_confidence"],
                    "sample_count": category_data["sample_count"],
                    "recommendation": f"Improve OCR patterns for {category_data['category']} detection"
                })
            elif category_data["avg_confidence"] > 0.9:
                insights["high_performing_categories"].append({
                    "category": "use_category",
                    "value": category_data["category"],
                    "avg_confidence": category_data["avg_confidence"]
                })
        
        # Analyze low confidence patterns
        if low_confidence:
            contract_types = defaultdict(int)
            for contract in low_confidence:
                contract_types[contract["contract_type"]] += 1
            
            insights["low_confidence_patterns"] = [
                {
                    "contract_type": contract_type,
                    "count": count,
                    "percentage": count / len(low_confidence) * 100
                }
                for contract_type, count in contract_types.items()
            ]
        
        return insights