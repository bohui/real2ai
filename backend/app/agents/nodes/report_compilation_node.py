"""
Report Compilation Node for Contract Analysis Workflow

This module contains the node responsible for compiling the final analysis report.
"""

import logging
from datetime import datetime, UTC
from typing import (
    Any,
    Dict,
    List,
    Optional,
    TypedDict,
    NotRequired,
    Literal,
    TYPE_CHECKING,
    Union,
    cast,
)

from app.models.contract_state import RealEstateAgentState
from app.schema.enums import ProcessingStatus
from .base import BaseNode

logger = logging.getLogger(__name__)


# ===== Strongly typed structures for compiled report and related data =====

ConfidenceScores = Dict[str, float]


class ReportMetadata(TypedDict):
    generated_at: str
    workflow_version: str
    session_id: Optional[str]
    document_id: Optional[str]
    processing_time: str
    final_confidence: float


class ExecutiveSummary(TypedDict):
    overview: str
    key_findings: List[str]
    critical_issues: List[str]
    recommendations_summary: str
    # Risk label synthesized in this node
    overall_assessment: str


class DocumentProcessingMetrics(TypedDict):
    text_quality_score: float
    completeness_score: float
    extraction_confidence: float


class TermsExtractionMetrics(TypedDict):
    extraction_confidence: float
    terms_completeness: float


class AnalysisQualityMetrics(TypedDict):
    average_confidence: float
    low_confidence_steps: List[str]
    confidence_range: Dict[str, float]


class QualityMetrics(TypedDict, total=False):
    document_processing: DocumentProcessingMetrics
    terms_extraction: TermsExtractionMetrics
    analysis_quality: AnalysisQualityMetrics
    overall_quality: float


class DocumentValidation(TypedDict):
    quality_passed: bool
    issues: List[str]
    suggestions: List[str]


class TermsValidation(TypedDict):
    completeness_passed: bool
    missing_fields: List[str]
    validation_confidence: float


class FinalValidation(TypedDict, total=False):
    validation_passed: NotRequired[bool]
    validation_issues: NotRequired[List[str]]


class ValidationResults(TypedDict, total=False):
    final_validation: FinalValidation
    document_validation: DocumentValidation
    terms_validation: TermsValidation
    validation_summary: str


class TechnicalDetails(TypedDict, total=False):
    document_processing: Dict[str, Any]
    diagram_analysis: Dict[str, Any]
    processing_notes: List[str]


class RecommendationsSection(TypedDict, total=False):
    priority_actions: List[Dict[str, Any]]
    recommendations: List[Dict[str, Any]]


class CompiledReport(TypedDict):
    report_metadata: ReportMetadata
    executive_summary: ExecutiveSummary
    contract_analysis: Dict[str, Any]
    compliance_assessment: Dict[str, Any]
    risk_evaluation: Dict[str, Any]
    recommendations: Union[RecommendationsSection, Dict[str, Any]]
    quality_metrics: QualityMetrics
    confidence_scores: ConfidenceScores
    validation_results: ValidationResults
    technical_details: TechnicalDetails


class CompilationData(TypedDict):
    compiled_report: CompiledReport
    report_sections: int
    compilation_timestamp: str
    processing_completed: bool
    # Intentionally propagated as empty string on success to clear previous error
    error_state: str
    parsing_status: ProcessingStatus


class ReportDataAggregate(TypedDict, total=False):
    contract_terms: Dict[str, Any]
    compliance_analysis: Dict[str, Any]
    risk_assessment: Dict[str, Any]
    recommendations: Dict[str, Any]
    diagram_analysis: Dict[str, Any]
    document_metadata: Dict[str, Any]
    document_quality_metrics: Dict[str, Any]
    terms_validation_result: Dict[str, Any]


class AnalysisResultsAggregate(TypedDict, total=False):
    overall_confidence: float
    compliance_check: Dict[str, Any]
    risk_assessment: Dict[str, Any]
    recommendations: Dict[str, Any]


if TYPE_CHECKING:
    from app.agents.contract_workflow import ContractAnalysisWorkflow


class ReportCompilationNode(BaseNode):
    """
    Node responsible for compiling the final analysis report.

    This node performs:
    - Aggregation of all analysis results
    - Report structure generation
    - Summary compilation
    - Output formatting and organization
    """

    def __init__(self, workflow: "ContractAnalysisWorkflow") -> None:
        super().__init__(workflow, "report_compilation")

    async def execute(self, state: RealEstateAgentState) -> RealEstateAgentState:
        """
        Compile final analysis report from all workflow results.

        Args:
            state: Current workflow state with all analysis results

        Returns:
            Updated state with compiled report
        """
        # Update progress to final step
        if "progress" in state and state["progress"]:
            state["progress"]["current_step"] = state["progress"]["total_steps"]
            state["progress"]["percentage"] = 100

        try:
            self._log_step_debug("Starting report compilation", state)

            # Gather all analysis results
            report_data: ReportDataAggregate = self._gather_analysis_results(state)

            # Compile comprehensive report
            compiled_report: CompiledReport = {
                "report_metadata": {
                    "generated_at": datetime.now(UTC).isoformat(),
                    "workflow_version": state.get("workflow_metadata", {}).get(
                        "workflow_version", "2.0"
                    ),
                    "session_id": state.get("session_id"),
                    "document_id": state.get("document_data", {}).get("document_id"),
                    "processing_time": self._calculate_processing_time(state),
                    "final_confidence": state.get("final_workflow_confidence", 0.5),
                },
                "executive_summary": self._generate_executive_summary(report_data),
                "contract_analysis": report_data.get("contract_terms", {}),
                "compliance_assessment": report_data.get("compliance_analysis", {}),
                "risk_evaluation": report_data.get("risk_assessment", {}),
                "recommendations": report_data.get("recommendations", {}),
                "quality_metrics": self._compile_quality_metrics(state),
                "confidence_scores": cast(
                    ConfidenceScores, state.get("confidence_scores", {})
                ),
                "validation_results": self._compile_validation_results(state),
                "technical_details": {
                    "document_processing": report_data.get("document_metadata", {}),
                    "diagram_analysis": report_data.get("diagram_analysis", {}),
                    "processing_notes": self._generate_processing_notes(state),
                },
            }

            # Update state with compiled report and mark overall success
            state["compiled_report"] = compiled_report
            # Service expects report data here
            state["report_data"] = compiled_report
            # Clear any previous error when we successfully compile a report
            state["error_state"] = None
            # Use the canonical state key expected by the service layer
            state["parsing_status"] = ProcessingStatus.COMPLETED

            # Ensure analysis_results has minimal required aggregates for response builders
            analysis_results: AnalysisResultsAggregate = cast(
                AnalysisResultsAggregate, state.get("analysis_results") or {}
            )
            if "overall_confidence" not in analysis_results:
                analysis_results["overall_confidence"] = compiled_report[
                    "report_metadata"
                ].get("final_confidence", 0.5)
            if "compliance_check" not in analysis_results and state.get(
                "compliance_analysis"
            ):
                analysis_results["compliance_check"] = state.get("compliance_analysis")
            if "risk_assessment" not in analysis_results and state.get(
                "risk_assessment"
            ):
                analysis_results["risk_assessment"] = state.get("risk_assessment")
            if "recommendations" not in analysis_results and state.get(
                "recommendations"
            ):
                analysis_results["recommendations"] = state.get("recommendations")
            state["analysis_results"] = analysis_results

            compilation_data: CompilationData = {
                "compiled_report": compiled_report,
                "report_sections": len([k for k, v in compiled_report.items() if v]),
                "compilation_timestamp": datetime.now(UTC).isoformat(),
                "processing_completed": True,
                # Clear any previous error in the aggregated state by setting to empty string
                # (update_state_step ignores None, but propagates non-None values)
                "error_state": "",
                # Explicitly propagate success status in the delta
                "parsing_status": ProcessingStatus.COMPLETED,
            }

            self._log_step_debug(
                f"Report compilation completed ({len(compiled_report)} sections)",
                state,
                {
                    "final_confidence": compiled_report["report_metadata"][
                        "final_confidence"
                    ]
                },
            )

            return self.update_state_step(
                state, "report_compilation_completed", data=compilation_data
            )

        except Exception as e:
            return self._handle_node_error(
                state,
                e,
                f"Report compilation failed: {str(e)}",
                {
                    "available_data": (
                        list(state.keys()) if isinstance(state, dict) else []
                    )
                },
            )

    def _gather_analysis_results(
        self, state: RealEstateAgentState
    ) -> ReportDataAggregate:
        """Gather all analysis results from the workflow state."""
        analysis_keys: List[str] = [
            "contract_terms",
            "compliance_analysis",
            "risk_assessment",
            "recommendations",
            "diagram_analysis",
            "document_metadata",
            "document_quality_metrics",
            "terms_validation_result",
        ]

        return cast(
            ReportDataAggregate,
            {key: state.get(key, {}) for key in analysis_keys if state.get(key)},
        )

    def _generate_executive_summary(
        self, report_data: ReportDataAggregate
    ) -> ExecutiveSummary:
        """Generate executive summary of the analysis."""
        summary: ExecutiveSummary = {
            "overview": "Contract analysis completed with comprehensive evaluation of terms, compliance, and risks.",
            "key_findings": [],
            "critical_issues": [],
            "recommendations_summary": "",
            "overall_assessment": "medium_risk",  # Default
        }

        # Extract key findings from different analysis sections
        contract_terms = report_data.get("contract_terms", {})
        if contract_terms:
            if contract_terms.get("purchase_price"):
                summary["key_findings"].append(
                    f"Purchase price: {contract_terms['purchase_price']}"
                )
            if contract_terms.get("settlement_date"):
                summary["key_findings"].append(
                    f"Settlement date: {contract_terms['settlement_date']}"
                )

        # Critical issues from compliance and risk analysis
        compliance_analysis = report_data.get("compliance_analysis", {})
        if compliance_analysis and compliance_analysis.get("issues"):
            summary["critical_issues"].extend(compliance_analysis["issues"])

        risk_assessment = report_data.get("risk_assessment", {})
        if risk_assessment:
            risk_level = risk_assessment.get("overall_risk_level", "medium")
            summary["overall_assessment"] = f"{risk_level}_risk"

            priority_risks = risk_assessment.get("priority_risks", [])
            for risk in priority_risks[:2]:  # Top 2 risks
                summary["critical_issues"].append(
                    risk.get("description", "Priority risk identified")
                )

        # Recommendations summary
        recommendations = report_data.get("recommendations", {})
        if recommendations:
            priority_actions = recommendations.get("priority_actions", [])
            total_recommendations = len(recommendations.get("recommendations", []))

            if priority_actions:
                summary["recommendations_summary"] = (
                    f"{len(priority_actions)} immediate action(s) required, {total_recommendations} total recommendations"
                )
            else:
                summary["recommendations_summary"] = (
                    f"{total_recommendations} recommendations provided for review"
                )

        return summary

    def _compile_quality_metrics(self, state: RealEstateAgentState) -> QualityMetrics:
        """Compile quality metrics from various workflow steps."""
        quality_metrics: QualityMetrics = {
            "document_processing": {},
            "terms_extraction": {},
            "analysis_quality": {},
            "overall_quality": 0.5,
        }

        # Document quality metrics
        doc_quality = state.get("document_quality_metrics", {})
        if doc_quality:
            quality_metrics["document_processing"] = {
                "text_quality_score": doc_quality.get("text_quality_score", 0.5),
                "completeness_score": doc_quality.get("completeness_score", 0.5),
                "extraction_confidence": doc_quality.get("extraction_confidence", 0.5),
            }

        # Terms extraction quality
        contract_terms: Dict[str, Any] = state.get("contract_terms", {}) or {}
        if contract_terms:
            extraction_confidence = cast(
                ConfidenceScores, state.get("confidence_scores", {})
            ).get("contract_extraction", 0.5)
            quality_metrics["terms_extraction"] = {
                "extraction_confidence": extraction_confidence,
                "terms_completeness": len(contract_terms)
                / 10,  # Rough completeness metric
            }

        # Overall analysis quality
        confidence_scores: ConfidenceScores = cast(
            ConfidenceScores, state.get("confidence_scores", {})
        )
        if confidence_scores:
            avg_confidence = sum(confidence_scores.values()) / len(confidence_scores)
            quality_metrics["overall_quality"] = avg_confidence
            quality_metrics["analysis_quality"] = {
                "average_confidence": avg_confidence,
                "low_confidence_steps": [
                    step for step, score in confidence_scores.items() if score < 0.5
                ],
                "confidence_range": {
                    "min": min(confidence_scores.values()),
                    "max": max(confidence_scores.values()),
                },
            }

        return quality_metrics

    def _compile_validation_results(
        self, state: RealEstateAgentState
    ) -> ValidationResults:
        """Compile validation results from workflow steps."""
        validation_results: ValidationResults = {
            "final_validation": cast(
                FinalValidation, state.get("final_validation_result", {}) or {}
            ),
            "document_validation": {},
            "terms_validation": {},
            "validation_summary": "No validation performed",
        }

        if not self.enable_validation:
            validation_results["validation_summary"] = "Validation disabled"
            return validation_results

        # Document quality validation
        doc_quality: Dict[str, Any] = state.get("document_quality_metrics", {}) or {}
        if doc_quality:
            validation_results["document_validation"] = {
                "quality_passed": doc_quality.get("text_quality_score", 0) > 0.6,
                "issues": doc_quality.get("issues_identified", []),
                "suggestions": doc_quality.get("improvement_suggestions", []),
            }

        # Terms validation
        terms_validation: Dict[str, Any] = (
            state.get("terms_validation_result", {}) or {}
        )
        if terms_validation:
            validation_results["terms_validation"] = {
                "completeness_passed": terms_validation.get("completeness_score", 0)
                > 0.6,
                "missing_fields": terms_validation.get("missing_fields", []),
                "validation_confidence": terms_validation.get(
                    "overall_confidence", 0.5
                ),
            }

        # Generate summary
        final_validation: FinalValidation = cast(
            FinalValidation, validation_results.get("final_validation", {})
        )
        if final_validation:
            validation_passed = bool(final_validation.get("validation_passed", False))
            issues_count = len(
                cast(List[str], final_validation.get("validation_issues", []))
            )

            if validation_passed:
                validation_results["validation_summary"] = "All validations passed"
            else:
                validation_results["validation_summary"] = (
                    f"Validation completed with {issues_count} issue(s)"
                )

        return validation_results

    def _generate_processing_notes(self, state: RealEstateAgentState) -> List[str]:
        """Generate processing notes and observations."""
        notes: List[str] = []

        # Document processing notes
        doc_metadata: Dict[str, Any] = state.get("document_metadata", {}) or {}
        if doc_metadata:
            extraction_method = doc_metadata.get("extraction_method", "unknown")
            if extraction_method != "unknown":
                notes.append(f"Document processed using {extraction_method} method")

            if doc_metadata.get("llm_used"):
                notes.append("LLM assistance used for document processing")

        # Analysis method notes
        config_notes: List[str] = []
        if not self.use_llm_config.get("contract_analysis", True):
            config_notes.append("contract analysis")
        if not self.use_llm_config.get("compliance_analysis", True):
            config_notes.append("compliance analysis")
        if not self.use_llm_config.get("risk_assessment", True):
            config_notes.append("risk assessment")

        if config_notes:
            notes.append(f"Rule-based methods used for: {', '.join(config_notes)}")

        # Confidence-based notes
        confidence_scores: ConfidenceScores = cast(
            ConfidenceScores, state.get("confidence_scores", {})
        )
        low_confidence_steps: List[str] = [
            step for step, score in confidence_scores.items() if score < 0.5
        ]
        if low_confidence_steps:
            notes.append(
                f"Low confidence detected in: {', '.join(low_confidence_steps)}"
            )

        return notes

    def _calculate_processing_time(self, state: RealEstateAgentState) -> str:
        """Calculate total processing time."""
        try:
            workflow_metadata = state.get("workflow_metadata", {})
            start_time_str = workflow_metadata.get("start_time")

            if start_time_str:
                start_time = datetime.fromisoformat(
                    start_time_str.replace("Z", "+00:00")
                )
                end_time = datetime.now(UTC)
                processing_time = end_time - start_time

                total_seconds = int(processing_time.total_seconds())
                minutes = total_seconds // 60
                seconds = total_seconds % 60

                if minutes > 0:
                    return f"{minutes}m {seconds}s"
                else:
                    return f"{seconds}s"

            return "Unknown"

        except Exception as e:
            self._log_exception(e, context={"calculation": "processing_time"})
            return "Unknown"
