"""
Semantic Analysis Service - Orchestrates image semantic analysis workflows
Integrates extract_image_semantics into the document analysis pipeline
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, UTC
from pathlib import Path

from fastapi import HTTPException

from app.core.config import get_settings
from app.core.prompts.service_mixin import PromptEnabledService
from app.model.enums import AustralianState, ContractType
from app.prompts.template.image_semantics_schema import ImageSemantics, ImageType, RiskIndicator
from app.prompts.template.diagram_risk_schema import DiagramRiskAssessment, RiskExtractor
from app.services.gemini_ocr_service import GeminiOCRService
# Circular import removed - DocumentService will be passed as parameter if needed
from app.clients.base.exceptions import ClientError

logger = logging.getLogger(__name__)

class SemanticAnalysisWorkflow:
    """Workflow orchestrator for semantic image analysis"""
    
    def __init__(self):
        self.ocr_service = None
        self.document_service = None
        self.settings = get_settings()
        
    async def initialize(self):
        """Initialize all required services"""
        try:
            self.ocr_service = GeminiOCRService()
            await self.ocr_service.initialize()
            
            self.document_service = DocumentService()
            await self.document_service.initialize()
            
            
            logger.info("Semantic analysis workflow initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize semantic analysis workflow: {str(e)}")
            raise

class SemanticAnalysisService(PromptEnabledService):
    """Service for semantic analysis of property diagrams and images"""
    
    def __init__(self):
        super().__init__()
        self.workflow = SemanticAnalysisWorkflow()
        
    async def initialize(self):
        """Initialize the semantic analysis service"""
        await self.workflow.initialize()
        
    async def analyze_document_semantics(
        self,
        storage_path: str,
        file_type: str,
        filename: str,
        contract_context: Optional[Dict[str, Any]] = None,
        analysis_options: Optional[Dict[str, Any]] = None,
        document_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Comprehensive semantic analysis of property documents with images/diagrams
        
        Args:
            storage_path: Path to document in storage
            file_type: File extension (pdf, jpg, png, etc.)
            filename: Original filename
            contract_context: Contract context for analysis
            analysis_options: Analysis configuration options
            document_id: Document ID for progress tracking
            
        Returns:
            Complete semantic analysis results
        """
        if not self.workflow.ocr_service:
            raise HTTPException(status_code=503, detail="Semantic analysis service not initialized")
            
        analysis_results = {
            "document_metadata": {
                "storage_path": storage_path,
                "filename": filename,
                "file_type": file_type,
                "analysis_timestamp": datetime.now(UTC).isoformat(),
                "document_id": document_id
            },
            "semantic_analysis": None,
            "risk_assessment": None,
            "processing_stages": [],
            "errors": [],
            "warnings": []
        }
        
        try:
            # Stage 1: Document Processing and OCR
            if document_id:
                await self._track_progress(document_id, "semantic_processing", 10, "Starting semantic analysis")
            
            file_content = await self.workflow.document_service.get_file_content(storage_path)
            
            # Stage 2: Image Semantic Extraction
            if document_id:
                await self._track_progress(document_id, "extracting_semantics", 30, "Extracting semantic meaning from images")
            
            # Auto-detect image type
            image_type = self._detect_image_type_from_context(filename, contract_context)
            
            # Determine analysis focus from options
            analysis_focus = analysis_options.get("analysis_focus", "comprehensive") if analysis_options else "comprehensive"
            risk_categories = analysis_options.get("risk_categories", []) if analysis_options else []
            
            # Extract image semantics using GeminiOCRService
            semantic_result = await self.workflow.ocr_service.extract_image_semantics(
                file_content=file_content,
                file_type=file_type,
                filename=filename,
                image_type=image_type,
                contract_context=contract_context,
                analysis_focus=analysis_focus,
                risk_categories=risk_categories
            )
            
            analysis_results["semantic_analysis"] = semantic_result.get("semantic_analysis")
            analysis_results["processing_stages"].append({
                "stage": "semantic_extraction",
                "status": "completed",
                "timestamp": datetime.now(UTC).isoformat(),
                "details": {
                    "image_type_detected": semantic_result.get("image_type_detected"),
                    "analysis_focus": analysis_focus,
                    "template_used": semantic_result.get("prompt_template_used", False)
                }
            })
            
            # Stage 3: Risk Assessment Integration
            if document_id:
                await self._track_progress(document_id, "assessing_risks", 60, "Analyzing property risks from semantic data")
            
            # Convert semantic analysis to risk assessment using diagram risk schema
            risk_assessment = await self._convert_to_risk_assessment(
                semantic_result.get("semantic_analysis"),
                contract_context
            )
            
            analysis_results["risk_assessment"] = risk_assessment
            analysis_results["processing_stages"].append({
                "stage": "risk_assessment",
                "status": "completed", 
                "timestamp": datetime.now(UTC).isoformat(),
                "details": {
                    "total_risks_identified": risk_assessment.get("total_risks_identified", 0),
                    "high_priority_risks": len(risk_assessment.get("high_priority_risks", [])),
                    "overall_risk_score": risk_assessment.get("overall_risk_score", "unknown")
                }
            })
            
            # Stage 4: Enhanced Analysis with Prompt Engineering
            if document_id:
                await self._track_progress(document_id, "enhancing_analysis", 80, "Enhancing analysis with domain expertise")
            
            enhanced_analysis = await self._enhance_with_prompt_engineering(
                semantic_result.get("semantic_analysis"),
                contract_context,
                analysis_options
            )
            
            if enhanced_analysis:
                analysis_results["enhanced_analysis"] = enhanced_analysis
                analysis_results["processing_stages"].append({
                    "stage": "enhanced_analysis",
                    "status": "completed",
                    "timestamp": datetime.now(UTC).isoformat()
                })
            
            # Stage 5: Final Consolidation
            if document_id:
                await self._track_progress(document_id, "consolidating_results", 95, "Consolidating analysis results")
            
            # Consolidate all analysis results
            consolidated_results = self._consolidate_analysis_results(
                analysis_results,
                contract_context
            )
            
            analysis_results.update(consolidated_results)
            
            # Final progress update
            if document_id:
                await self._track_progress(document_id, "completed", 100, "Semantic analysis completed successfully")
            
            analysis_results["processing_stages"].append({
                "stage": "consolidation",
                "status": "completed",
                "timestamp": datetime.now(UTC).isoformat(),
                "details": {
                    "total_stages": len(analysis_results["processing_stages"]) + 1,
                    "success": True
                }
            })
            
            return analysis_results
            
        except Exception as e:
            logger.error(f"Semantic analysis failed for {storage_path}: {str(e)}")
            
            # Error progress update
            if document_id:
                await self._track_progress(
                    document_id, "failed", 0, f"Semantic analysis failed: {str(e)}"
                )
            
            analysis_results["errors"].append({
                "error": str(e),
                "stage": "semantic_analysis",
                "timestamp": datetime.now(UTC).isoformat()
            })
            
            # Return partial results if any stages succeeded
            return analysis_results

    async def analyze_contract_diagrams(
        self,
        storage_paths: List[str],
        contract_context: Dict[str, Any],
        document_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analyze multiple diagrams from a contract document
        
        Args:
            storage_paths: List of paths to diagram images
            contract_context: Contract context for analysis
            document_id: Document ID for progress tracking
            
        Returns:
            Consolidated analysis of all diagrams
        """
        if not storage_paths:
            raise HTTPException(status_code=400, detail="No diagrams provided for analysis")
            
        consolidated_results = {
            "contract_context": contract_context,
            "total_diagrams": len(storage_paths),
            "diagram_analyses": [],
            "consolidated_risks": [],
            "overall_assessment": {},
            "recommendations": [],
            "analysis_timestamp": datetime.now(UTC).isoformat()
        }
        
        try:
            # Analyze each diagram individually
            for i, storage_path in enumerate(storage_paths):
                if document_id:
                    progress = int(20 + (i * 60 / len(storage_paths)))
                    await self._track_progress(
                        document_id, "analyzing_diagrams", progress, 
                        f"Analyzing diagram {i+1} of {len(storage_paths)}"
                    )
                
                filename = Path(storage_path).name
                file_type = Path(storage_path).suffix.lower().lstrip('.')
                
                diagram_analysis = await self.analyze_document_semantics(
                    storage_path=storage_path,
                    file_type=file_type,
                    filename=filename,
                    contract_context=contract_context,
                    analysis_options={"analysis_focus": "comprehensive"}
                )
                
                consolidated_results["diagram_analyses"].append({
                    "diagram_index": i,
                    "storage_path": storage_path,
                    "filename": filename,
                    "analysis": diagram_analysis
                })
            
            # Consolidate risks across all diagrams
            if document_id:
                await self._track_progress(document_id, "consolidating_risks", 85, "Consolidating risks across all diagrams")
            
            consolidated_results["consolidated_risks"] = self._consolidate_diagram_risks(
                consolidated_results["diagram_analyses"]
            )
            
            # Generate overall assessment
            consolidated_results["overall_assessment"] = self._generate_overall_assessment(
                consolidated_results
            )
            
            # Generate consolidated recommendations
            consolidated_results["recommendations"] = self._generate_consolidated_recommendations(
                consolidated_results,
                contract_context
            )
            
            if document_id:
                await self._track_progress(document_id, "completed", 100, "Contract diagram analysis completed")
            
            return consolidated_results
            
        except Exception as e:
            logger.error(f"Contract diagram analysis failed: {str(e)}")
            
            if document_id:
                await self._track_progress(document_id, "failed", 0, f"Analysis failed: {str(e)}")
            
            consolidated_results["error"] = str(e)
            return consolidated_results

    def _detect_image_type_from_context(
        self, 
        filename: str, 
        contract_context: Optional[Dict[str, Any]] = None
    ) -> ImageType:
        """Detect image type from filename and context"""
        filename_lower = filename.lower()
        
        # Check contract context for hints
        if contract_context:
            document_type = contract_context.get("document_type", "").lower()
            if "sewer" in document_type:
                return ImageType.SEWER_SERVICE_DIAGRAM
            elif "flood" in document_type:
                return ImageType.FLOOD_MAP
            elif "survey" in document_type:
                return ImageType.SURVEY_DIAGRAM
        
        # Filename-based detection (similar to GeminiOCRService)
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
        else:
            return ImageType.UNKNOWN

    async def _convert_to_risk_assessment(
        self,
        semantic_analysis: Optional[Dict[str, Any]],
        contract_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Convert semantic analysis to risk assessment using diagram risk schema"""
        
        if not semantic_analysis:
            return {
                "overall_risk_score": "low",
                "total_risks_identified": 0,
                "high_priority_risks": [],
                "recommended_actions": []
            }
        
        try:
            # Extract risk indicators from semantic analysis
            risk_indicators = semantic_analysis.get("risk_indicators", [])
            infrastructure_elements = semantic_analysis.get("infrastructure_elements", [])
            environmental_elements = semantic_analysis.get("environmental_elements", [])
            boundary_elements = semantic_analysis.get("boundary_elements", [])
            
            # Create risk assessment using RiskExtractor
            risks = []
            
            # Process infrastructure risks
            for element in infrastructure_elements:
                if element.get("risk_relevance"):
                    risks.append({
                        "risk_type": f"Infrastructure: {element.get('element_type', 'Unknown')}",
                        "description": element.get("description", ""),
                        "severity": self._determine_risk_severity(element),
                        "evidence": f"{element.get('location', {}).get('description', 'Location not specified')}",
                        "category": "infrastructure"
                    })
            
            # Process environmental risks
            for element in environmental_elements:
                risks.append({
                    "risk_type": f"Environmental: {element.get('environmental_type', 'Unknown')}",
                    "description": element.get("description", ""),
                    "severity": element.get("risk_level", "medium"),
                    "evidence": f"{element.get('location', {}).get('description', 'Location not specified')}",
                    "category": "environmental"
                })
            
            # Process boundary risks
            for element in boundary_elements:
                if element.get("encroachments") or element.get("easements"):
                    risks.append({
                        "risk_type": f"Boundary: {element.get('boundary_type', 'Unknown')}",
                        "description": element.get("description", ""),
                        "severity": "medium",
                        "evidence": f"Encroachments: {element.get('encroachments', [])}, Easements: {element.get('easements', [])}",
                        "category": "boundary"
                    })
            
            # Calculate overall risk score
            overall_risk_score = self._calculate_overall_risk_score(risks)
            
            # Generate high priority risks
            high_priority_risks = [
                risk["description"] for risk in risks 
                if risk.get("severity") in ["high", "critical"]
            ]
            
            # Generate recommended actions
            recommended_actions = self._generate_risk_actions(risks, contract_context)
            
            return {
                "overall_risk_score": overall_risk_score,
                "total_risks_identified": len(risks),
                "identified_risks": risks,
                "high_priority_risks": high_priority_risks,
                "recommended_actions": recommended_actions,
                "risk_categories": {
                    "infrastructure": len([r for r in risks if r.get("category") == "infrastructure"]),
                    "environmental": len([r for r in risks if r.get("category") == "environmental"]),
                    "boundary": len([r for r in risks if r.get("category") == "boundary"])
                }
            }
            
        except Exception as e:
            logger.error(f"Risk assessment conversion failed: {str(e)}")
            return {
                "overall_risk_score": "unknown",
                "total_risks_identified": 0,
                "high_priority_risks": [],
                "recommended_actions": [],
                "error": str(e)
            }

    def _determine_risk_severity(self, element: Dict[str, Any]) -> str:
        """Determine risk severity from semantic element"""
        confidence = element.get("confidence", "medium")
        risk_relevance = element.get("risk_relevance", "").lower()
        
        if confidence == "high" and "critical" in risk_relevance:
            return "critical"
        elif confidence == "high" and ("high" in risk_relevance or "significant" in risk_relevance):
            return "high"
        elif "medium" in risk_relevance or confidence == "medium":
            return "medium"
        else:
            return "low"

    def _calculate_overall_risk_score(self, risks: List[Dict[str, Any]]) -> str:
        """Calculate overall risk score from individual risks"""
        if not risks:
            return "low"
        
        severity_weights = {"critical": 4, "high": 3, "medium": 2, "low": 1}
        
        total_weight = sum(severity_weights.get(risk.get("severity", "low"), 1) for risk in risks)
        average_weight = total_weight / len(risks)
        
        if average_weight >= 3.5:
            return "critical"
        elif average_weight >= 2.5:
            return "high"
        elif average_weight >= 1.5:
            return "medium"
        else:
            return "low"

    def _generate_risk_actions(
        self, 
        risks: List[Dict[str, Any]], 
        contract_context: Optional[Dict[str, Any]] = None
    ) -> List[str]:
        """Generate recommended actions based on identified risks"""
        actions = []
        
        # Infrastructure risks
        infrastructure_risks = [r for r in risks if r.get("category") == "infrastructure"]
        if infrastructure_risks:
            actions.append("Consult with structural engineer regarding foundation design around infrastructure")
            actions.append("Verify utility easement boundaries and access requirements with local council")
        
        # Environmental risks
        environmental_risks = [r for r in risks if r.get("category") == "environmental"]
        if environmental_risks:
            actions.append("Obtain detailed environmental assessment and flood/bushfire risk reports")
            actions.append("Check insurance implications for environmental risks")
        
        # Boundary risks
        boundary_risks = [r for r in risks if r.get("category") == "boundary"]
        if boundary_risks:
            actions.append("Engage licensed surveyor to verify boundary locations and resolve encroachments")
            actions.append("Review easement documentation and maintenance obligations")
        
        # High severity risks
        high_severity_risks = [r for r in risks if r.get("severity") in ["high", "critical"]]
        if high_severity_risks:
            actions.append("Seek immediate legal advice regarding high-risk issues before proceeding")
        
        return actions

    async def _enhance_with_prompt_engineering(
        self,
        semantic_analysis: Optional[Dict[str, Any]],
        contract_context: Optional[Dict[str, Any]] = None,
        analysis_options: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """Enhance semantic analysis using prompt engineering service"""
        
        if not semantic_analysis:
            return None
        
        try:
            # Create prompt context
            australian_state = AustralianState.NSW  # Default
            contract_type = ContractType.PURCHASE_AGREEMENT  # Default
            
            if contract_context:
                australian_state = contract_context.get("australian_state", AustralianState.NSW)
                contract_type = contract_context.get("contract_type", ContractType.PURCHASE_AGREEMENT)
            
            from app.core.prompts.context import PromptContext, ContextType
            
            prompt_context = PromptContext(
                context_type=ContextType.USER,
                variables={
                    "australian_state": australian_state,
                    "contract_type": contract_type,
                    "user_type": contract_context.get("user_type", "buyer") if contract_context else "buyer",
                    "focus_areas": analysis_options.get("risk_categories", []) if analysis_options else [],
                    "user_experience_level": contract_context.get("user_experience_level", "novice") if contract_context else "novice",
                    "structured_data": semantic_analysis
                }
            )
            
            # Create enhanced risk assessment prompt using PromptManager
            risk_prompt = await self.render_prompt(
                template_name="risk_assessment_base",
                context=prompt_context,
                validate=True,
                use_cache=True
            )
            
            # Enhanced analysis structure with PromptManager integration
            return {
                "enhanced_risk_analysis": "Enhanced analysis using PromptManager templates",
                "prompt_template_used": "risk_assessment_base",
                "prompt_length": len(risk_prompt),
                "context_applied": {
                    "state": australian_state.value if hasattr(australian_state, 'value') else str(australian_state),
                    "contract_type": contract_type.value if hasattr(contract_type, 'value') else str(contract_type),
                    "focus_areas": prompt_context.variables.get("focus_areas", [])
                }
            }
            
        except Exception as e:
            logger.warning(f"Prompt engineering enhancement failed: {str(e)}")
            return None

    def _consolidate_analysis_results(
        self,
        analysis_results: Dict[str, Any],
        contract_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Consolidate all analysis results into final format"""
        
        semantic_analysis = analysis_results.get("semantic_analysis")
        risk_assessment = analysis_results.get("risk_assessment")
        
        consolidation = {
            "analysis_summary": {
                "semantic_elements_found": 0,
                "risks_identified": risk_assessment.get("total_risks_identified", 0) if risk_assessment else 0,
                "high_priority_items": len(risk_assessment.get("high_priority_risks", [])) if risk_assessment else 0,
                "overall_confidence": "medium"
            },
            "key_findings": [],
            "critical_actions": [],
            "professional_consultations_required": []
        }
        
        if semantic_analysis:
            # Count semantic elements
            element_count = (
                len(semantic_analysis.get("infrastructure_elements", [])) +
                len(semantic_analysis.get("boundary_elements", [])) +
                len(semantic_analysis.get("environmental_elements", [])) +
                len(semantic_analysis.get("building_elements", []))
            )
            consolidation["analysis_summary"]["semantic_elements_found"] = element_count
            
            # Extract key findings
            consolidation["key_findings"] = semantic_analysis.get("key_findings", [])
            
            # Determine overall confidence
            consolidation["analysis_summary"]["overall_confidence"] = semantic_analysis.get("analysis_confidence", "medium")
        
        if risk_assessment:
            # Extract critical actions from recommended actions
            consolidation["critical_actions"] = risk_assessment.get("recommended_actions", [])
            
            # Determine required professional consultations
            risks = risk_assessment.get("identified_risks", [])
            if any(r.get("category") == "infrastructure" for r in risks):
                consolidation["professional_consultations_required"].append("Structural Engineer")
            if any(r.get("category") == "environmental" for r in risks):
                consolidation["professional_consultations_required"].append("Environmental Consultant")
            if any(r.get("category") == "boundary" for r in risks):
                consolidation["professional_consultations_required"].append("Licensed Surveyor")
            if any(r.get("severity") in ["high", "critical"] for r in risks):
                consolidation["professional_consultations_required"].append("Property Lawyer")
        
        return consolidation

    def _consolidate_diagram_risks(self, diagram_analyses: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Consolidate risks across multiple diagram analyses"""
        all_risks = []
        risk_map = {}  # To avoid duplicates
        
        for diagram in diagram_analyses:
            analysis = diagram.get("analysis", {})
            risk_assessment = analysis.get("risk_assessment", {})
            risks = risk_assessment.get("identified_risks", [])
            
            for risk in risks:
                risk_key = f"{risk.get('risk_type', '')}-{risk.get('category', '')}"
                if risk_key not in risk_map:
                    risk_map[risk_key] = risk.copy()
                    risk_map[risk_key]["source_diagrams"] = [diagram.get("filename", "unknown")]
                else:
                    # Merge evidence from multiple diagrams
                    existing_risk = risk_map[risk_key]
                    existing_risk["source_diagrams"].append(diagram.get("filename", "unknown"))
                    existing_risk["evidence"] += f"; {risk.get('evidence', '')}"
                    
                    # Upgrade severity if higher
                    severity_order = {"low": 1, "medium": 2, "high": 3, "critical": 4}
                    if severity_order.get(risk.get("severity", "low"), 1) > severity_order.get(existing_risk.get("severity", "low"), 1):
                        existing_risk["severity"] = risk.get("severity", "low")
        
        return list(risk_map.values())

    def _generate_overall_assessment(self, consolidated_results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate overall assessment of contract diagrams"""
        consolidated_risks = consolidated_results.get("consolidated_risks", [])
        total_diagrams = consolidated_results.get("total_diagrams", 0)
        
        # Count risks by severity
        severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        for risk in consolidated_risks:
            severity = risk.get("severity", "low")
            severity_counts[severity] += 1
        
        # Determine overall risk level
        if severity_counts["critical"] > 0:
            overall_risk = "critical"
        elif severity_counts["high"] > 2:
            overall_risk = "high"
        elif severity_counts["high"] > 0 or severity_counts["medium"] > 3:
            overall_risk = "medium"
        else:
            overall_risk = "low"
        
        # Generate assessment
        return {
            "overall_risk_level": overall_risk,
            "total_risks": len(consolidated_risks),
            "risk_distribution": severity_counts,
            "diagrams_analyzed": total_diagrams,
            "proceed_recommendation": "proceed_with_caution" if overall_risk in ["high", "critical"] else "proceed",
            "confidence_level": 0.8 if total_diagrams >= 3 else 0.6,
            "analysis_completeness": min(1.0, total_diagrams / 5.0)  # Assume 5 diagrams is comprehensive
        }

    def _generate_consolidated_recommendations(
        self, 
        consolidated_results: Dict[str, Any],
        contract_context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate consolidated recommendations across all diagrams"""
        recommendations = []
        consolidated_risks = consolidated_results.get("consolidated_risks", [])
        overall_assessment = consolidated_results.get("overall_assessment", {})
        
        # High-level recommendations based on overall risk
        overall_risk = overall_assessment.get("overall_risk_level", "low")
        
        if overall_risk == "critical":
            recommendations.append({
                "type": "urgent_action",
                "priority": "critical",
                "recommendation": "Do not proceed with purchase until critical risks are resolved",
                "timeline": "immediate",
                "professional_required": "property_lawyer"
            })
        elif overall_risk == "high":
            recommendations.append({
                "type": "caution_required",
                "priority": "high", 
                "recommendation": "Proceed with extreme caution and obtain comprehensive professional advice",
                "timeline": "before_exchange",
                "professional_required": "multiple_consultants"
            })
        
        # Risk-specific recommendations
        risk_categories = {}
        for risk in consolidated_risks:
            category = risk.get("category", "general")
            if category not in risk_categories:
                risk_categories[category] = []
            risk_categories[category].append(risk)
        
        # Infrastructure recommendations
        if "infrastructure" in risk_categories:
            recommendations.append({
                "type": "infrastructure_assessment",
                "priority": "high",
                "recommendation": "Engage structural engineer to assess building implications of infrastructure elements",
                "timeline": "before_building_approval",
                "professional_required": "structural_engineer",
                "affected_diagrams": list(set([
                    diagram for risk in risk_categories["infrastructure"] 
                    for diagram in risk.get("source_diagrams", [])
                ]))
            })
        
        # Environmental recommendations
        if "environmental" in risk_categories:
            recommendations.append({
                "type": "environmental_assessment",
                "priority": "high",
                "recommendation": "Obtain comprehensive environmental risk assessment and insurance review",
                "timeline": "before_settlement",
                "professional_required": "environmental_consultant",
                "affected_diagrams": list(set([
                    diagram for risk in risk_categories["environmental"]
                    for diagram in risk.get("source_diagrams", [])
                ]))
            })
        
        # Boundary recommendations
        if "boundary" in risk_categories:
            recommendations.append({
                "type": "boundary_verification",
                "priority": "medium",
                "recommendation": "Engage licensed surveyor to verify boundaries and resolve any encroachments",
                "timeline": "before_settlement",
                "professional_required": "licensed_surveyor",
                "affected_diagrams": list(set([
                    diagram for risk in risk_categories["boundary"]
                    for diagram in risk.get("source_diagrams", [])
                ]))
            })
        
        return recommendations

    async def _track_progress(
        self, 
        document_id: str, 
        stage: str, 
        progress: int, 
        message: str
    ):
        """Track processing progress through document service"""
        try:
            if self.workflow.document_service:
                await self.workflow.document_service.track_processing_progress(
                    document_id=document_id,
                    stage=f"semantic_{stage}",
                    progress_percent=progress,
                    message=message,
                    metadata={"service": "SemanticAnalysisService"}
                )
        except Exception as e:
            logger.warning(f"Failed to track progress: {str(e)}")

    async def health_check(self) -> Dict[str, Any]:
        """Health check for semantic analysis service"""
        health_status = {
            "service": "SemanticAnalysisService",
            "status": "healthy",
            "dependencies": {},
            "capabilities": [
                "image_semantic_analysis",
                "multi_diagram_analysis", 
                "risk_assessment_integration",
                "prompt_engineering_enhancement",
                "progress_tracking"
            ],
            "timestamp": datetime.now(UTC).isoformat()
        }
        
        # Check OCR service
        if self.workflow.ocr_service:
            try:
                ocr_health = await self.workflow.ocr_service.health_check()
                health_status["dependencies"]["ocr_service"] = ocr_health.get("service_status", "unknown")
            except Exception as e:
                health_status["dependencies"]["ocr_service"] = "error"
                health_status["status"] = "degraded"
        else:
            health_status["dependencies"]["ocr_service"] = "not_initialized"
            health_status["status"] = "degraded"
        
        # Check document service
        if self.workflow.document_service:
            try:
                doc_health = await self.workflow.document_service.health_check()
                health_status["dependencies"]["document_service"] = doc_health.get("status", "unknown")
            except Exception as e:
                health_status["dependencies"]["document_service"] = "error"
                health_status["status"] = "degraded"
        else:
            health_status["dependencies"]["document_service"] = "not_initialized"
            health_status["status"] = "degraded"
        
        return health_status

    async def get_analysis_capabilities(self) -> Dict[str, Any]:
        """Get semantic analysis capabilities"""
        capabilities = {
            "supported_image_types": [image_type.value for image_type in ImageType],
            "analysis_focus_options": ["infrastructure", "environmental", "boundaries", "comprehensive"],
            "risk_categories": ["infrastructure", "environmental", "boundary", "development", "compliance"],
            "supported_file_types": ["jpg", "jpeg", "png", "pdf", "tiff", "webp"],
            "max_diagrams_per_analysis": 10,
            "features": [
                "automatic_image_type_detection",
                "multi_diagram_consolidation",
                "risk_severity_assessment",
                "professional_consultation_recommendations",
                "progress_tracking",
                "prompt_engineering_integration"
            ]
        }
        
        # Add OCR service capabilities if available
        if self.workflow.ocr_service:
            try:
                ocr_capabilities = await self.workflow.ocr_service.get_processing_capabilities()
                capabilities["ocr_capabilities"] = ocr_capabilities
            except Exception as e:
                logger.warning(f"Could not get OCR capabilities: {str(e)}")
        
        return capabilities