"""Contract analysis router with cache-first strategy and enhanced error handling."""

import hashlib
from typing import Dict, List, Optional, Union, TypedDict, Any
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Body
from fastapi.responses import JSONResponse, Response
import logging
from datetime import datetime
from uuid import UUID

from app.core.auth import get_current_user, User
from app.core.auth_context import AuthContext
from app.services.document_service import DocumentService
from app.services.cache_service import get_cache_service, CacheService
from app.core.error_handler import handle_api_error, create_error_context, ErrorCategory
from app.core.retry_manager import retry_database_operation, retry_api_call
from app.core.notification_system import (
    notification_system,
    notify_user_error,
    notify_user_success,
)
from app.schema.contract import (
    ContractAnalysisResponse,
)
from app.models.supabase_models import Document, Contract, ContractAnalysis, Profile
from app.clients.base.interfaces import DatabaseOperations, AuthOperations
from app.clients.supabase.client import SupabaseClient


# Database Result Types
class DatabaseSelectResult(TypedDict):
    """Result from database select operations."""

    data: List[
        Dict[str, Union[str, int, float, bool, datetime, UUID, None, Dict, List]]
    ]
    count: int


class DatabaseMutationResult(TypedDict):
    """Result from database insert/update/delete operations."""

    success: bool
    data: Optional[
        Dict[str, Union[str, int, float, bool, datetime, UUID, None, Dict, List]]
    ]
    error: Optional[str]


# Domain Record Types (database row representations)
class DocumentRecord(TypedDict):
    """Document database record."""

    id: str
    user_id: str
    original_filename: str
    storage_path: str
    file_type: str
    file_size: int
    processing_status: str
    processing_results: Dict[str, Union[str, Dict, List]]
    created_at: str
    updated_at: str
    # Additional optional fields
    document_type: Optional[str]
    contract_type: Optional[str]
    australian_state: Optional[str]


class ContractRecord(TypedDict):
    """Contract database record."""

    id: str
    document_id: str
    user_id: str
    contract_type: str
    australian_state: str
    contract_terms: Dict[str, Union[str, int, float, bool, List, Dict]]
    created_at: str
    updated_at: str


class AnalysisRecord(TypedDict):
    """Contract analysis database record."""

    id: str
    contract_id: str
    user_id: str
    status: str
    agent_version: str
    analysis_result: Dict[str, Union[str, int, float, bool, List, Dict]]
    risk_score: Optional[float]
    processing_time: Optional[float]
    error_message: Optional[str]
    created_at: str
    updated_at: str


class UserNotificationData(TypedDict):
    """User notification structure."""

    id: str
    user_id: str
    title: str
    message: str
    type: str
    acknowledged: bool
    created_at: str


# API Response Types
class AnalysisStatusResponse(TypedDict):
    """Response for analysis status endpoint."""

    contract_id: str
    analysis_id: str
    status: str
    progress: int
    processing_time: float
    created_at: str
    updated_at: str
    estimated_completion: Optional[str]
    status_message: str
    next_update_in_seconds: Optional[int]
    cached: Optional[bool]
    cache_source: Optional[str]


class AnalysisProgressInfo(TypedDict):
    """Analysis progress calculation result."""

    progress: int
    status_message: str
    estimated_completion: Optional[str]
    next_update_in_seconds: Optional[int]


class ContractAnalysisResultResponse(TypedDict):
    """Response for contract analysis results."""

    contract_id: str
    analysis_status: str
    analysis_result: Dict[str, Union[str, int, float, bool, List, Dict]]
    risk_score: Optional[float]
    processing_time: Optional[float]
    created_at: str
    cached: Optional[bool]
    cache_source: Optional[str]


class NotificationsResponse(TypedDict):
    """Response for user notifications."""

    notifications: List[UserNotificationData]
    total_count: int
    unread_count: int


class DeleteContractResponse(TypedDict):
    """Response for contract deletion."""

    message: str
    contract_id: str
    analyses_deleted: int


class NotificationDismissResponse(TypedDict):
    """Response for notification dismissal."""

    message: str


# Background Task Types
class CeleryTaskResult:
    """Celery task result wrapper."""

    id: str

    def __init__(self, id: str):
        self.id = id


# Client Type Aliases
UserAuthenticatedClient = SupabaseClient
SystemClient = SupabaseClient

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/contracts", tags=["contracts"])


# Dependency function to get user-aware document service
async def get_user_document_service(
    user: User = Depends(get_current_user),
) -> DocumentService:
    """Get document service with user authentication context"""
    user_client = await AuthContext.get_authenticated_client(require_auth=True)
    service = DocumentService(user_client=user_client)
    await service.initialize()
    return service


@router.post("/analyze", response_model=ContractAnalysisResponse)
async def start_contract_analysis(
    background_tasks: BackgroundTasks,
    request: Dict[str, Any] = Body(...),
    user: User = Depends(get_current_user),
    document_service: DocumentService = Depends(get_user_document_service),
    cache_service: CacheService = Depends(get_cache_service),
) -> ContractAnalysisResponse:
    """
    Start contract analysis with cache-first strategy.

    Body:
        - document_id: Document ID to analyze
        - check_cache: Whether to check cache first (default: true)
        - content_hash: Optional pre-computed content hash
        - analysis_options: Analysis configuration options
    """

    # Enhanced request validation
    document_id = request.get("document_id")
    check_cache = request.get("check_cache", True)
    content_hash = request.get("content_hash")
    analysis_options = request.get("analysis_options", {})

    # Create error context for better error reporting
    context = create_error_context(
        user_id=str(user.id),
        operation="start_contract_analysis",
        document_id=document_id,
    )

    try:
        # Enhanced request validation with detailed logging
        logger.info(
            f"Contract analysis request from user {user.id}: "
            f"document_id={document_id}, check_cache={check_cache}"
        )

        if not document_id:
            logger.warning(f"Missing document_id in request from user {user.id}")
            raise ValueError("Document ID is required")

        if not user.australian_state:
            logger.warning(f"User {user.id} has no australian_state configured")
            raise ValueError(
                "Australian state is required for accurate contract analysis"
            )

        # Check user credits with detailed logging
        logger.debug(
            f"User {user.id} credits: {user.credits_remaining}, subscription: {user.subscription_status}"
        )
        if user.credits_remaining <= 0 and user.subscription_status == "free":
            logger.warning(
                f"User {user.id} has insufficient credits: {user.credits_remaining}"
            )
            raise ValueError("You don't have enough credits to analyze this contract")

        # Get user-authenticated client through document service
        try:
            user_client = await document_service.get_user_client()
            logger.debug(f"Successfully obtained user client for user {user.id}")
        except Exception as e:
            logger.error(f"Failed to get user client for user {user.id}: {str(e)}")
            raise ValueError("Authentication failed - please try logging in again")

        # Get document with user context (RLS enforced)
        try:
            document = await _get_user_document(user_client, document_id, str(user.id))
            logger.debug(
                f"Successfully retrieved document {document_id} for user {user.id}"
            )
        except ValueError as e:
            error_msg = str(e)
            if "Document not found or you don't have access to it" in error_msg:
                logger.error(
                    f"Document access denied: {document_id} for user {user.id}. "
                    f"This could mean: 1) Document doesn't exist, 2) Document belongs to another user, "
                    f"3) User session has expired. Use /api/contracts/debug/document/{document_id} to troubleshoot."
                )
                raise ValueError(
                    f"Document access denied. Document {document_id} either doesn't exist or doesn't belong to your account. "
                    f"Please verify the document ID or upload the document again."
                )
            else:
                logger.error(
                    f"Failed to retrieve document {document_id} for user {user.id}: {error_msg}"
                )
                raise
        except Exception as e:
            logger.error(
                f"Failed to retrieve document {document_id} for user {user.id}: {str(e)}"
            )
            raise

        # Validate document is suitable for analysis
        if not _is_valid_contract_document(document):
            raise ValueError("This file doesn't appear to be a property contract")

        # Generate content hash if not provided and cache is enabled
        if not content_hash and check_cache:
            content_hash = await _generate_document_content_hash(document)

        # CACHE-FIRST STRATEGY
        if check_cache and content_hash:
            logger.info(f"Checking cache for content_hash: {content_hash}")

            cached_result = await cache_service.check_contract_cache(content_hash)

            if cached_result:
                logger.info(f"Cache HIT for content_hash: {content_hash}")

                # Create user records from cache hit
                try:
                    document_id_new, contract_id, analysis_id = (
                        await cache_service.create_user_contract_from_cache(
                            user_id=str(user.id),
                            content_hash=content_hash,
                            cached_analysis=cached_result,
                            original_filename=document.get(
                                "original_filename", "Cached Document"
                            ),
                            file_size=document.get("file_size", 0),
                            mime_type=document.get("file_type", "application/pdf"),
                            property_address=cached_result.get("property_address"),
                        )
                    )

                    # Send success notification
                    await notification_system.send_notification(
                        template_name="analysis_completed",
                        user_id=str(user.id),
                        contract_id=contract_id,
                        session_id=context.session_id or f"contract_{contract_id}",
                        additional_data={"cached": True, "processing_time": 0.1},
                    )

                    return ContractAnalysisResponse(
                        contract_id=contract_id,
                        analysis_id=analysis_id,
                        status="completed",  # Cache hit = instant completion
                        task_id=f"cache_hit_{analysis_id}",
                        estimated_completion_minutes=0,
                        cached=True,
                        cache_hit=True,
                    )

                except Exception as cache_error:
                    logger.error(f"Error processing cache hit: {str(cache_error)}")
                    # Continue with normal processing if cache processing fails
                    pass
            else:
                logger.info(f"Cache MISS for content_hash: {content_hash}")

        # NORMAL PROCESSING PATH (Cache miss or cache disabled)

        # Create contract record with user context (RLS enforced)
        contract_id = await _create_contract_record_with_cache(
            user_client, document_id, document, user, content_hash
        )

        # Create analysis record with user context (RLS enforced)
        analysis_id = await _create_analysis_record_with_cache(
            user_client, contract_id, str(user.id), content_hash
        )

        # Start background analysis with cache integration
        task_id = await _start_background_analysis_with_cache(
            contract_id,
            analysis_id,
            str(user.id),
            document,
            analysis_options,
            content_hash,
            cache_service,
        )

        # Send success notification to user
        await notification_system.send_notification(
            template_name="analysis_started",
            user_id=str(user.id),
            contract_id=contract_id,
            session_id=context.session_id or f"contract_{contract_id}",
        )

        return ContractAnalysisResponse(
            contract_id=contract_id,
            analysis_id=analysis_id,
            status="queued",
            task_id=task_id,
            estimated_completion_minutes=3,  # Comprehensive processing takes slightly longer
            cached=False,
            cache_hit=False,
        )

    except HTTPException:
        # Re-raise HTTPExceptions without modification
        raise
    except Exception as e:
        # Send error notification to user
        await notify_user_error(
            user_id=str(user.id),
            title="Analysis Failed",
            message=str(e),
            session_id=context.session_id or f"contract_error_{user.id}",
            contract_id=context.contract_id,
        )

        # Use enhanced error handler
        raise handle_api_error(e, context, ErrorCategory.CONTRACT_ANALYSIS)


@router.post("/bulk-analyze")
async def bulk_contract_analysis(
    background_tasks: BackgroundTasks,
    requests: List[Dict[str, Any]] = Body(...),
    user: User = Depends(get_current_user),
    cache_service: CacheService = Depends(get_cache_service),
) -> JSONResponse:
    """
    Analyze multiple contracts with intelligent cache utilization.

    Body: List of analysis requests, each containing:
        - document_id: Document ID to analyze
        - analysis_options: Optional analysis configuration
    """

    context = create_error_context(
        user_id=str(user.id), operation="bulk_contract_analysis"
    )

    try:
        if not requests:
            raise ValueError("At least one analysis request is required")

        if len(requests) > 10:  # Reasonable limit
            raise ValueError("Maximum 10 contracts can be analyzed at once")

        # Check user has sufficient credits
        required_credits = len(requests)
        if (
            user.credits_remaining < required_credits
            and user.subscription_status == "free"
        ):
            raise ValueError(
                f"You need {required_credits} credits to analyze {len(requests)} contracts"
            )

        results = []
        cache_hits = 0
        cache_misses = 0

        for i, request_data in enumerate(requests):
            try:
                document_id = request_data.get("document_id")
                if not document_id:
                    results.append(
                        {
                            "index": i,
                            "document_id": document_id,
                            "status": "error",
                            "error": "Document ID is required",
                        }
                    )
                    continue

                # Process each request with cache-first strategy
                enhanced_request = {
                    "document_id": document_id,
                    "check_cache": True,
                    "analysis_options": request_data.get("analysis_options", {}),
                }

                response = await start_contract_analysis(
                    background_tasks,
                    enhanced_request,
                    user,
                    await get_user_document_service(user),
                    cache_service,
                )

                if response.get("cache_hit"):
                    cache_hits += 1
                else:
                    cache_misses += 1

                results.append(
                    {
                        "index": i,
                        "document_id": document_id,
                        "contract_id": response["contract_id"],
                        "analysis_id": response["analysis_id"],
                        "status": response["status"],
                        "cached": response.get("cached", False),
                        "cache_hit": response.get("cache_hit", False),
                    }
                )

            except Exception as req_error:
                logger.error(f"Error processing bulk request {i}: {str(req_error)}")
                results.append(
                    {
                        "index": i,
                        "document_id": request_data.get("document_id"),
                        "status": "error",
                        "error": str(req_error),
                    }
                )

        return JSONResponse(
            content={
                "status": "success",
                "data": {
                    "results": results,
                    "summary": {
                        "total_requests": len(requests),
                        "cache_hits": cache_hits,
                        "cache_misses": cache_misses,
                        "success_count": len(
                            [r for r in results if r.get("status") != "error"]
                        ),
                        "error_count": len(
                            [r for r in results if r.get("status") == "error"]
                        ),
                        "cache_efficiency": (
                            f"{(cache_hits / len(requests)) * 100:.1f}%"
                            if requests
                            else "0%"
                        ),
                    },
                },
            }
        )

    except Exception as e:
        raise handle_api_error(e, context, ErrorCategory.CONTRACT_ANALYSIS)


@retry_database_operation(max_attempts=3)
async def _initialize_database_client(db_client: SupabaseClient) -> None:
    """Initialize database client with retry logic"""
    if not hasattr(db_client, "_client") or db_client._client is None:
        await db_client.initialize()


@retry_database_operation(max_attempts=3)
async def _get_user_document(
    user_client: UserAuthenticatedClient, document_id: str, user_id: str
) -> DocumentRecord:
    """Get user document with user context (RLS enforced)"""
    try:
        doc_result = await user_client.database.select(
            "documents", columns="*", filters={"id": document_id, "user_id": user_id}
        )

        logger.debug(
            f"Document query result for {document_id}: {doc_result is not None}"
        )

        if not doc_result.get("data"):
            logger.warning(f"Document {document_id} not found for user {user_id}")
            raise ValueError(f"Document not found or you don't have access to it")

        document = doc_result["data"][0]
        logger.debug(
            f"Retrieved document: id={document.get('id')}, status={document.get('processing_status')}"
        )
        return document

    except Exception as e:
        logger.error(
            f"Database error retrieving document {document_id} for user {user_id}: {str(e)}"
        )
        raise ValueError(f"Failed to retrieve document: {str(e)}")


def _is_valid_contract_document(document: DocumentRecord) -> bool:
    """Validate that document is suitable for contract analysis"""
    # Check file size (basic validation)
    if document.get("file_size", 0) > 10 * 1024 * 1024:  # 10MB limit
        raise ValueError("File is too large. Please use a file smaller than 10MB")

    # Check if document has content - either extracted text in processing_results or storage_path
    processing_results = document.get("processing_results", {})
    text_extraction = processing_results.get("text_extraction", {})
    full_text = text_extraction.get("full_text", "")
    storage_path = document.get("storage_path", "")

    if not full_text and not storage_path:
        raise ValueError("The document appears to be empty or corrupted")

    return True


@retry_database_operation(max_attempts=3)
async def _create_contract_record_with_cache(
    db_client: SupabaseClient,
    document_id: str,
    document: DocumentRecord,
    user: User,
    content_hash: Optional[str] = None,
) -> str:
    """Create contract record with cache integration."""
    contract_data = {
        "document_id": document_id,
        "contract_type": document.get("contract_type", "purchase_agreement"),
        "australian_state": user.australian_state,
        "user_id": str(user.id),
        "content_hash": content_hash,  # Same as content_hash for contracts
    }

    contract_result = await db_client.database.insert("contracts", contract_data)

    if not contract_result.get("success") or not contract_result.get("data"):
        raise ValueError("Failed to create contract record")

    return contract_result["data"]["id"]


@retry_database_operation(max_attempts=3)
async def _create_analysis_record_with_cache(
    db_client: SupabaseClient,
    contract_id: str,
    user_id: str,
    content_hash: Optional[str] = None,
) -> str:
    """Create analysis record with cache integration."""
    analysis_data = {
        "contract_id": contract_id,
        "user_id": user_id,
        "agent_version": "1.0",
        "status": "pending",
        "content_hash": content_hash,  # Same as content_hash for contracts
    }

    analysis_result = await db_client.database.insert(
        "contract_analyses", analysis_data
    )

    if not analysis_result.get("success") or not analysis_result.get("data"):
        raise ValueError("Failed to create analysis record")

    return analysis_result["data"]["id"]


@retry_api_call(max_attempts=2)
async def _start_background_analysis_with_cache(
    contract_id: str,
    analysis_id: str,
    user_id: str,
    document: DocumentRecord,
    analysis_options: Dict[str, Any],
    content_hash: Optional[str],
    cache_service: CacheService,
) -> str:
    """Start comprehensive background analysis with progress tracking and cache integration."""
    try:
        from app.tasks.background_tasks import comprehensive_document_analysis

        # Enhanced task parameters with comprehensive processing and progress tracking
        task_params = {
            "document_id": document["id"],
            "analysis_id": analysis_id,
            "contract_id": contract_id,
            "user_id": user_id,
            "analysis_options": {
                **analysis_options,
                "content_hash": content_hash,
                "enable_caching": True,
                "progress_tracking": True,
                "comprehensive_processing": True,
            },
        }

        logger.info(
            f"Starting comprehensive analysis task for contract {contract_id} with progress tracking"
        )

        task = comprehensive_document_analysis.delay(**task_params)

        if not task or not task.id:
            raise ValueError("Failed to queue comprehensive analysis")

        logger.info(f"Comprehensive analysis task queued with ID: {task.id}")
        return task.id

    except Exception as e:
        logger.error(f"Comprehensive analysis task creation failed: {str(e)}")
        raise ValueError(
            "Our AI service is temporarily busy. Please try again in a few minutes"
        )


async def _generate_document_content_hash(document: DocumentRecord) -> Optional[str]:
    """Generate content hash for document."""
    try:
        # Try to get hash from document record first
        if document.get("content_hash"):
            return document["content_hash"]

        # If document has processing results with text, hash that
        processing_results = document.get("processing_results", {})
        text_extraction = processing_results.get("text_extraction", {})
        full_text = text_extraction.get("full_text", "")

        if full_text:
            # Hash the extracted text content
            content_bytes = full_text.encode("utf-8")
            return hashlib.sha256(content_bytes).hexdigest()

        # Fallback: create hash from document metadata
        metadata = f"{document.get('original_filename', '')}{document.get('file_size', 0)}{document.get('created_at', '')}"
        return hashlib.sha256(metadata.encode("utf-8")).hexdigest()

    except Exception as e:
        logger.error(f"Error generating content hash: {str(e)}")
        return None


@router.get("/{contract_id}/status")
async def get_analysis_status(
    contract_id: str,
    user: User = Depends(get_current_user),
    cache_service: CacheService = Depends(get_cache_service),
) -> AnalysisStatusResponse:
    """Get contract analysis status with cache information."""

    context = create_error_context(
        user_id=str(user.id), contract_id=contract_id, operation="get_analysis_status"
    )

    try:
        # Validate contract ID format
        if not contract_id or not contract_id.strip():
            raise ValueError("Contract ID is required")

        # Get authenticated client
        db_client = await AuthContext.get_authenticated_client(require_auth=True)

        # Initialize database client with retry
        await _initialize_database_client(db_client)

        # Get analysis status with retry and validation
        analysis = await _get_analysis_status_with_validation(
            db_client, contract_id, user.id
        )

        # Calculate progress with enhanced information
        progress_info = _calculate_analysis_progress(analysis)

        # Check if this was a cached analysis
        cached_indicator = analysis.get("analysis_metadata", {}).get("cached_from")

        response = {
            "contract_id": contract_id,
            "analysis_id": analysis["id"],
            "status": analysis["status"],
            "progress": progress_info["progress"],
            "processing_time": analysis.get("processing_time", 0),
            "created_at": analysis["created_at"],
            "updated_at": analysis["updated_at"],
            "estimated_completion": progress_info["estimated_completion"],
            "status_message": progress_info["status_message"],
            "next_update_in_seconds": progress_info.get("next_update_in_seconds"),
        }

        # Add cache information if available
        if cached_indicator:
            response["cached"] = True
            response["cache_source"] = cached_indicator

        return response

    except HTTPException:
        raise
    except Exception as e:
        raise handle_api_error(e, context, ErrorCategory.DATABASE)


@retry_database_operation(max_attempts=3)
async def _get_analysis_status_with_validation(
    db_client: UserAuthenticatedClient, contract_id: str, user_id: str
) -> AnalysisRecord:
    """Get analysis status with validation and retry logic"""

    # First verify the contract belongs to the user
    contract_result = (
        db_client.table("contracts")
        .select("id, user_id")
        .eq("id", contract_id)
        .execute()
    )

    if not contract_result.data:
        raise ValueError("Contract not found")

    contract = contract_result.data[0]
    if contract["user_id"] != user_id:
        raise ValueError("You don't have access to this contract")

    # Get analysis status
    result = (
        db_client.table("contract_analyses")
        .select(
            "id, status, created_at, updated_at, processing_time, error_message, analysis_metadata"
        )
        .eq("contract_id", contract_id)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )

    if not result.data:
        raise ValueError("Analysis not found for this contract")

    return result.data[0]


def _calculate_analysis_progress(analysis: AnalysisRecord) -> AnalysisProgressInfo:
    """Calculate detailed progress information"""

    status = analysis["status"]

    # Enhanced progress mapping with more granular updates
    progress_mapping = {
        "pending": {
            "progress": 0,
            "status_message": "Your contract analysis is queued and will start shortly",
            "estimated_completion": "2-5 minutes",
            "next_update_in_seconds": 30,
        },
        "queued": {
            "progress": 5,
            "status_message": "Analysis has been queued and will begin processing soon",
            "estimated_completion": "2-5 minutes",
            "next_update_in_seconds": 15,
        },
        "processing": {
            "progress": 50,
            "status_message": "Our AI is analyzing your contract - this may take a few minutes",
            "estimated_completion": "1-3 minutes",
            "next_update_in_seconds": 10,
        },
        "completed": {
            "progress": 100,
            "status_message": "Analysis complete! You can now view your results",
            "estimated_completion": None,
            "next_update_in_seconds": None,
        },
        "failed": {
            "progress": 0,
            "status_message": "Analysis failed. Please try again or contact support",
            "estimated_completion": None,
            "next_update_in_seconds": None,
        },
        "cancelled": {
            "progress": 0,
            "status_message": "Analysis was cancelled",
            "estimated_completion": None,
            "next_update_in_seconds": None,
        },
    }

    return progress_mapping.get(
        status,
        {
            "progress": 0,
            "status_message": "Analysis status unknown",
            "estimated_completion": None,
            "next_update_in_seconds": 30,
        },
    )


@router.get("/{contract_id}/progress")
async def get_analysis_progress(
    contract_id: str,
    user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Get detailed analysis progress with real-time updates.

    This endpoint provides granular progress information including:
    - Current processing step
    - Progress percentage
    - Step description
    - Estimated completion time
    - Error messages (if any)
    """

    context = create_error_context(
        user_id=str(user.id), contract_id=contract_id, operation="get_analysis_progress"
    )

    try:
        # Get authenticated client
        db_client = await AuthContext.get_authenticated_client(require_auth=True)

        # Get progress record from analysis_progress table
        progress_result = await db_client.database.select(
            "analysis_progress",
            columns="*",
            filters={"contract_id": contract_id, "user_id": str(user.id)},
        )

        # Get analysis status as fallback
        analysis_result = await db_client.database.select(
            "contract_analyses",
            columns="id, status, created_at, updated_at, processing_time",
            filters={"contract_id": contract_id},
        )

        if not analysis_result.get("data"):
            raise HTTPException(status_code=404, detail="Analysis not found")

        analysis = analysis_result["data"][0]

        # If we have detailed progress, use that
        if progress_result.get("data"):
            progress = progress_result["data"][0]
            return {
                "contract_id": contract_id,
                "analysis_id": progress["analysis_id"],
                "progress": progress["progress_percent"],
                "current_step": progress["current_step"],
                "step_description": progress["step_description"],
                "status": progress["status"],
                "estimated_completion_minutes": progress.get(
                    "estimated_completion_minutes"
                ),
                "step_started_at": progress["step_started_at"],
                "total_elapsed_seconds": progress.get("total_elapsed_seconds", 0),
                "error_message": progress.get("error_message"),
                "last_updated": progress.get("updated_at"),
                "has_detailed_progress": True,
            }

        # Fallback to basic progress calculation from analysis status
        else:
            progress_info = _calculate_analysis_progress(analysis)
            return {
                "contract_id": contract_id,
                "analysis_id": analysis["id"],
                "progress": progress_info["progress"],
                "current_step": analysis["status"],
                "step_description": progress_info["status_message"],
                "status": analysis["status"],
                "estimated_completion_minutes": None,
                "step_started_at": analysis["created_at"],
                "total_elapsed_seconds": 0,
                "error_message": None,
                "last_updated": analysis["updated_at"],
                "has_detailed_progress": False,
            }

    except HTTPException:
        raise
    except Exception as e:
        raise handle_api_error(e, context, ErrorCategory.DATABASE)


@router.get("/{contract_id}/analysis")
async def get_contract_analysis(
    contract_id: str,
    user: User = Depends(get_current_user),
) -> ContractAnalysisResultResponse:
    """Get contract analysis results with cache information."""

    try:
        # Get authenticated client
        db_client = await AuthContext.get_authenticated_client(require_auth=True)

        # Ensure database client is initialized
        if not hasattr(db_client, "_client") or db_client._client is None:
            await db_client.initialize()

        # Get analysis results
        result = (
            db_client.table("contract_analyses")
            .select("*")
            .eq("contract_id", contract_id)
            .execute()
        )

        if not result.data:
            raise HTTPException(status_code=404, detail="Analysis not found")

        analysis = result.data[0]

        # Verify user owns this contract
        contract_result = (
            db_client.table("contracts").select("*").eq("id", contract_id).execute()
        )
        if not contract_result.data:
            raise HTTPException(status_code=404, detail="Contract not found")

        contract = contract_result.data[0]
        doc_result = (
            db_client.table("documents")
            .select("*")
            .eq("id", contract["document_id"])
            .eq("user_id", user.id)
            .execute()
        )

        if not doc_result.data:
            raise HTTPException(status_code=403, detail="Access denied")

        # Enhanced response with cache information
        response = {
            "contract_id": contract_id,
            "analysis_status": analysis["status"],
            "analysis_result": analysis.get("analysis_result", {}),
            "risk_score": analysis.get("risk_score"),
            "processing_time": analysis.get("processing_time"),
            "created_at": analysis["created_at"],
        }

        # Add cache information if available
        metadata = analysis.get("analysis_metadata", {})
        if metadata.get("cached_from"):
            response["cached"] = True
            response["cache_source"] = metadata["cached_from"]

        return response

    except HTTPException:
        # Re-raise HTTPExceptions (validation errors) without modification
        raise
    except Exception as e:
        logger.error(f"Get analysis error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{contract_id}/report", response_model=ContractAnalysisResultResponse)
async def get_contract_analysis_report(
    contract_id: str,
    user: User = Depends(get_current_user),
) -> ContractAnalysisResultResponse:
    """Get contract analysis report data"""
    return await get_contract_analysis(contract_id, user)


@router.get("/{contract_id}/report/pdf")
async def download_contract_pdf_report(
    contract_id: str,
    user: User = Depends(get_current_user),
):
    """Download contract analysis report as PDF"""

    try:
        # Get authenticated client
        db_client = await AuthContext.get_authenticated_client(require_auth=True)

        # Get analysis data
        analysis_data = await get_contract_analysis(contract_id, user)

        # Generate PDF report (would implement with reportlab or similar)
        from app.tasks.background_tasks import generate_pdf_report

        pdf_content = await generate_pdf_report(analysis_data)

        # Return the actual PDF content
        return Response(
            content=pdf_content,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=contract_{contract_id}_report.pdf"
            },
        )

    except Exception as e:
        logger.error(f"PDF report download error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{contract_id}")
async def delete_contract_analysis(
    contract_id: str,
    user: User = Depends(get_current_user),
) -> DeleteContractResponse:
    """Delete contract analysis and related data"""

    try:
        # Get authenticated client
        db_client = await AuthContext.get_authenticated_client(require_auth=True)

        # Ensure database client is initialized
        if not hasattr(db_client, "_client") or db_client._client is None:
            await db_client.initialize()

        # Verify user owns this contract
        contract_result = (
            db_client.table("contracts").select("*").eq("id", contract_id).execute()
        )

        if not contract_result.data:
            raise HTTPException(status_code=404, detail="Contract not found")

        contract = contract_result.data[0]

        # Verify ownership through document
        doc_result = (
            db_client.table("documents")
            .select("user_id")
            .eq("id", contract["document_id"])
            .execute()
        )

        if not doc_result.data or doc_result.data[0]["user_id"] != user.id:
            raise HTTPException(status_code=403, detail="Access denied")

        # Delete contract analyses first (foreign key constraint)
        analyses_result = (
            db_client.table("contract_analyses")
            .delete()
            .eq("contract_id", contract_id)
            .execute()
        )

        # Delete the contract
        contract_delete_result = (
            db_client.table("contracts").delete().eq("id", contract_id).execute()
        )

        if not contract_delete_result.data:
            raise HTTPException(
                status_code=404, detail="Contract not found or already deleted"
            )

        return {
            "message": "Contract analysis deleted successfully",
            "contract_id": contract_id,
            "analyses_deleted": (
                len(analyses_result.data) if analyses_result.data else 0
            ),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete contract error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/notifications")
async def get_user_notifications(
    user: User = Depends(get_current_user), include_acknowledged: bool = False
) -> NotificationsResponse:
    """Get user notifications with enhanced feedback"""

    try:
        notifications = await notification_system.get_user_notifications(
            user_id=str(user.id), include_acknowledged=include_acknowledged
        )

        return {
            "notifications": [n.to_dict() for n in notifications],
            "total_count": len(notifications),
            "unread_count": len([n for n in notifications if not n.acknowledged]),
        }

    except Exception as e:
        logger.error(f"Error getting notifications for user {user.id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get notifications")


@router.post("/notifications/{notification_id}/dismiss")
async def dismiss_notification(
    notification_id: str, user: User = Depends(get_current_user)
) -> NotificationDismissResponse:
    """Dismiss a user notification"""

    try:
        await notification_system.dismiss_notification(
            user_id=str(user.id), notification_id=notification_id
        )

        return {"message": "Notification dismissed successfully"}

    except Exception as e:
        logger.error(f"Error dismissing notification {notification_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to dismiss notification")


@router.get("/debug/document/{document_id}")
async def debug_document_access(
    document_id: str,
    user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Debug endpoint to check document access and ownership"""
    try:
        # Get user-authenticated client
        user_client = await AuthContext.get_authenticated_client()

        # Try to get the document with RLS enforcement
        doc_result = await user_client.database.select(
            "documents",
            columns="*",
            filters={"id": document_id, "user_id": str(user.id)},
        )

        if doc_result.get("data"):
            document = doc_result["data"][0]
            return {
                "document_exists": True,
                "user_has_access": True,
                "document_id": document_id,
                "document_owner": document.get("user_id"),
                "current_user": str(user.id),
                "document_status": document.get("processing_status"),
                "filename": document.get("original_filename"),
                "created_at": document.get("created_at"),
                "updated_at": document.get("updated_at"),
            }
        else:
            # Document not found or user doesn't have access
            return {
                "document_exists": False,
                "user_has_access": False,
                "document_id": document_id,
                "current_user": str(user.id),
                "error": "Document not found or you don't have access to it",
                "possible_causes": [
                    "Document doesn't exist in the database",
                    "Document belongs to a different user",
                    "User session has expired",
                    "Document was deleted",
                ],
                "suggestions": [
                    "Verify the document ID is correct",
                    "Re-upload the document if needed",
                    "Check if you're logged in with the correct account",
                    "Contact support if the issue persists",
                ],
            }

    except Exception as e:
        logger.error(f"Debug endpoint error: {str(e)}")
        return {
            "document_exists": "error",
            "user_has_access": False,
            "document_id": document_id,
            "current_user": str(user.id),
            "error": f"Debug endpoint failed: {str(e)}",
        }
