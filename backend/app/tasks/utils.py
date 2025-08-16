"""Utility functions for background tasks."""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

from app.core.auth_context import AuthContext
from app.services.repositories.analysis_progress_repository import (
    AnalysisProgressRepository,
)
from app.services.repositories.documents_repository import DocumentsRepository

logger = logging.getLogger(__name__)

# Progress tracking constants
PROGRESS_STAGES = {
    "document_processing": {
        "text_extraction": 25,
        "page_analysis": 50,
        "diagram_detection": 60,
        "entity_extraction": 70,
        "document_complete": 75,
    },
    "contract_analysis": {
        "analysis_start": 80,
        "workflow_processing": 90,
        "results_caching": 95,
        "analysis_complete": 100,
    },
}


def _extract_root_cause(exception: Exception) -> Exception:
    """
    Extract the root cause from an exception chain.

    Args:
        exception: The exception to analyze

    Returns:
        The root cause exception (the original exception that started the chain)
    """
    current = exception
    while hasattr(current, "__cause__") and current.__cause__ is not None:
        current = current.__cause__

    # Also check for __context__ which is used for implicit exception chaining
    while hasattr(current, "__context__") and current.__context__ is not None:
        if not hasattr(current, "__cause__") or current.__cause__ is None:
            # Only follow __context__ if there's no explicit __cause__
            current = current.__context__
        else:
            break

    return current


def _format_exception_chain(exception: Exception) -> List[str]:
    """
    Format the full exception chain as a list of strings for logging.

    Args:
        exception: The exception to format

    Returns:
        List of formatted exception strings showing the full chain
    """
    chain = []
    current = exception
    seen = set()  # Prevent infinite loops in circular references

    while current is not None:
        # Prevent infinite loops
        exception_id = id(current)
        if exception_id in seen:
            break
        seen.add(exception_id)

        # Format current exception
        exc_info = {
            "type": type(current).__name__,
            "message": str(current),
            "module": getattr(type(current), "__module__", "unknown"),
        }

        # Add file and line info if available
        if hasattr(current, "__traceback__") and current.__traceback__:
            tb = current.__traceback__
            while tb.tb_next:
                tb = tb.tb_next  # Get the deepest traceback
            exc_info["file"] = tb.tb_frame.f_code.co_filename
            exc_info["line"] = tb.tb_lineno
            exc_info["function"] = tb.tb_frame.f_code.co_name

        chain.append(
            f"{exc_info['type']}: {exc_info['message']} (in {exc_info.get('function', 'unknown')} at {exc_info.get('file', 'unknown')}:{exc_info.get('line', 'unknown')})"
        )

        # Move to the next exception in the chain
        if hasattr(current, "__cause__") and current.__cause__ is not None:
            current = current.__cause__
        elif hasattr(current, "__context__") and current.__context__ is not None:
            current = current.__context__
        else:
            break

    return chain


async def update_analysis_progress(
    user_id: str,
    content_hash: str,
    progress_percent: int,
    current_step: str,
    step_description: str,
    estimated_completion_minutes: Optional[int] = None,
    error_message: Optional[str] = None,
):
    """Update analysis progress with detailed tracking"""
    try:
        # Determine status based on step and progress
        # Only mark as completed if we have confirmation of successful processing
        if current_step.endswith("_failed") or current_step == "failed":
            status = "failed"
        elif progress_percent >= 100 and current_step == "analysis_complete":
            # Additional validation: only mark as completed for analysis_complete step
            # This prevents premature completion marking
            status = "completed"
        else:
            status = "in_progress"

        progress_data = {
            "content_hash": content_hash,
            "user_id": user_id,
            "current_step": current_step,
            "progress_percent": progress_percent,
            "step_description": step_description,
            # Pass a datetime object for DB insertion (asyncpg expects datetime, not string)
            "step_started_at": datetime.now(timezone.utc),
            "estimated_completion_minutes": estimated_completion_minutes,
            "status": status,
            "error_message": error_message,
        }

        # Upsert progress record using repository
        logger.debug(
            "[update_analysis_progress] Prepared progress_data",
            extra={
                "content_hash": content_hash,
                "user_id": user_id,
                "current_step": current_step,
                "progress_percent": progress_percent,
                "status": status,
                "step_started_at_type": type(progress_data["step_started_at"]).__name__,
            },
        )
        # Pass user_id explicitly to avoid auth context dependency in isolated execution
        from uuid import UUID
        user_uuid = UUID(user_id) if isinstance(user_id, str) else user_id
        progress_repo = AnalysisProgressRepository(user_id=user_uuid)
        result = await progress_repo.upsert_progress(
            content_hash, user_id, progress_data
        )
        logger.debug(
            "[update_analysis_progress] Upsert result",
            extra={"content_hash": content_hash, "user_id": user_id, "result": result},
        )

        # IMPORTANT: Do not emit per-step analysis_progress over the document WebSocket channel.
        # The unified ContractAnalysisService already emits ordered progress over the contract/session channel.
        # Emitting here causes duplicate, out-of-order updates interleaving across channels which regresses the UI.
        # We still persist to DB and publish to Redis below for internal consumers.
        try:
            # We intentionally skip WebSocket fan-out on the document channel to prevent UI regressions.
            # Pass user_id explicitly to avoid auth context dependency in isolated execution  
            docs_repo = DocumentsRepository(user_id=user_uuid)
            documents = await docs_repo.get_documents_by_content_hash(
                content_hash, user_id, columns="id"
            )
            logger.debug(
                "[update_analysis_progress] Skipping WS broadcast on document channel",
                extra={
                    "content_hash": content_hash,
                    "user_id": user_id,
                    "doc_count": len(documents) if documents is not None else 0,
                    "broadcast_skipped": True,
                },
            )
        except Exception as ws_error:
            logger.warning(f"WS progress routing introspection failed: {ws_error}")

        # Do not publish progress to Redis here to avoid duplicate/out-of-order UI updates.
        # The ContractAnalysisService is the single source of truth for real-time progress
        # and will publish progress via Redis/WebSocket. We only persist to DB in this path.

        logger.info(
            f"Progress updated: {current_step} ({progress_percent}%) for content_hash {content_hash}"
        )

    except Exception as e:
        logger.error(
            f"Failed to update progress for content_hash {content_hash}: {str(e)}"
        )


def _validate_analysis_results(analysis_result: Dict[str, Any]) -> bool:
    """
    Validate that analysis results contain meaningful data indicating successful processing.

    Args:
        analysis_result: The analysis result dictionary

    Returns:
        bool: True if analysis contains meaningful results, False otherwise
    """
    try:
        if not analysis_result or not isinstance(analysis_result, dict):
            return False

        # 1) Contract terms present with any meaningful content
        contract_terms = analysis_result.get("contract_terms")
        if isinstance(contract_terms, dict) and contract_terms:
            meaningful_fields = [
                "purchase_price",
                "settlement_date",
                "property_address",
                "vendor_name",
                "purchaser_name",
                # Accept alternate/common keys as well
                "address",
                "price",
                "buyer_name",
                "seller_name",
            ]
            extracted_fields = 0
            for field in meaningful_fields:
                value = contract_terms.get(field)
                if (
                    value
                    and str(value).strip()
                    and str(value).strip() != "Not specified"
                ):
                    extracted_fields += 1
            if extracted_fields >= 1:
                return True

        # 2) Risk assessment present with score or level
        risk_assessment = analysis_result.get("risk_assessment")
        if isinstance(risk_assessment, dict) and risk_assessment:
            overall_risk_level = risk_assessment.get("overall_risk_level")
            overall_risk_score = risk_assessment.get("overall_risk_score")
            if (overall_risk_level and overall_risk_level != "unknown") or (
                isinstance(overall_risk_score, (int, float)) and overall_risk_score > 0
            ):
                return True

        # 3) Compliance present under either key used by the service
        compliance = analysis_result.get("compliance_check") or analysis_result.get(
            "compliance_analysis"
        )
        if isinstance(compliance, dict) and compliance:
            if compliance.get("state_compliance") is not None:
                return True
            # Also accept presence of specific checks/issues
            if compliance.get("issues") or compliance.get("warnings"):
                return True

        # 4) Recommendations present (list or object with list)
        recommendations = analysis_result.get("recommendations")
        if isinstance(recommendations, list) and len(recommendations) > 0:
            return True
        if isinstance(recommendations, dict):
            rec_list = recommendations.get("recommendations", [])
            if isinstance(rec_list, list) and len(rec_list) > 0:
                return True

        # 5) Final validation status indicates a good result
        final_validation = analysis_result.get("final_validation_result")
        if isinstance(final_validation, dict) and final_validation.get(
            "validation_passed"
        ):
            return True

        # 6) Confidence signals
        overall_confidence = analysis_result.get("overall_confidence")
        final_workflow_confidence = analysis_result.get("final_workflow_confidence")
        if (
            isinstance(overall_confidence, (int, float)) and overall_confidence >= 0.5
        ) or (
            isinstance(final_workflow_confidence, (int, float))
            and final_workflow_confidence >= 0.5
        ):
            return True

        return False

    except Exception as e:
        logger.warning(f"Error validating analysis results: {e}")
        return False