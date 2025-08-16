"""Contract analysis router with cache-first strategy and enhanced error handling."""

import hashlib
from typing import Dict, List, Optional, Union, TypedDict, Any
from uuid import UUID
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Body, Query
from fastapi.responses import JSONResponse
import logging
from datetime import datetime
from uuid import UUID

from app.core.auth import get_current_user, User
from app.core.auth_context import AuthContext
from app.services.document_service import DocumentService
from app.services.cache.cache_service import get_cache_service, CacheService
from app.core.error_handler import handle_api_error, create_error_context, ErrorCategory
from app.core.retry_manager import retry_database_operation, retry_api_call
from app.core.notification_system import (
    notification_system,
    notify_user_error,
)
from app.schema.contract import (
    ContractAnalysisResponse,
)
from app.clients.supabase.client import SupabaseClient
from app.services.repositories.analyses_repository import AnalysesRepository
from app.services.repositories.documents_repository import DocumentsRepository
from app.services.repositories.contracts_repository import ContractsRepository
from app.services.repositories.user_contract_views_repository import UserContractViewsRepository

logger = logging.getLogger(__name__)


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


# API Response Types
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


class DeleteContractResponse(TypedDict):
    """Response for contract deletion."""

    message: str
    contract_id: str
    analyses_deleted: int


# Background Task Types
"""
DEPRECATED: Unused placeholder class commented out.
Original name: CeleryTaskResult
Reason: No references in codebase; Celery tasks return ids directly.
Date: 2025-08-10
"""
# class CeleryTaskResult:
#     """Celery task result wrapper."""
#
#     id: str
#
#     def __init__(self, id: str):
#         self.id = id


# Client Type Aliases
UserAuthenticatedClient = SupabaseClient
SystemClient = SupabaseClient

router = APIRouter(prefix="/api/contracts", tags=["contracts"])


# Dependency function to get user-aware document service
async def get_user_document_service(
    user: User = Depends(get_current_user),
) -> DocumentService:
    """Get document service with user authentication context"""
    user_client = await AuthContext.get_authenticated_client(require_auth=True)
    service = DocumentService(user_client=user_client, use_llm_document_processing=True)
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
                    f"3) User session has expired."
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

        # Ensure we have a content_hash for downstream records
        if not content_hash:
            content_hash = await _generate_document_content_hash(document)

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


@router.post("/analyze-enhanced", response_model=ContractAnalysisResponse)
async def start_contract_analysis_enhanced(
    background_tasks: BackgroundTasks,
    request: Dict[str, Any] = Body(...),
    user: User = Depends(get_current_user),
    document_service: DocumentService = Depends(get_user_document_service),
    cache_service: CacheService = Depends(get_cache_service),
) -> ContractAnalysisResponse:
    """
    Enhanced contract analysis endpoint (alias for backward compatibility).

    This is a thin alias that calls start_contract_analysis with the same arguments.
    Added for compatibility with frontend cacheService.startEnhancedContractAnalysis.
    """
    return await start_contract_analysis(
        background_tasks, request, user, document_service, cache_service
    )


@router.get("/history")
async def get_contract_history(
    limit: int = Query(
        50,
        ge=1,
        le=100,
        description="Number of records to return (minimum 1, maximum 100)",
    ),
    offset: int = Query(0, ge=0, description="Number of records to skip"),
    user: User = Depends(get_current_user),
    cache_service: CacheService = Depends(get_cache_service),
) -> Dict[str, Any]:
    """
    Get user's contract analysis history.

    Returns:
        Contract history with pagination support
    """
    context = create_error_context(
        user_id=str(user.id),
        operation="get_contract_history",
        limit=limit,
        offset=offset,
    )

    try:
        history = await cache_service.get_user_contract_history(
            user_id=str(user.id), limit=limit, offset=offset
        )

        return {
            "status": "success",
            "data": {
                "history": history,
                "total_count": len(history),
                "has_more": len(history) == limit,
            },
        }

    except Exception as e:
        logger.error(f"Error getting contract history: {str(e)}")
        raise handle_api_error(e, context, ErrorCategory.DATABASE)


@router.post("/check-cache")
async def check_contract_cache(
    request: Dict[str, Any] = Body(...),
    user: User = Depends(get_current_user),
    cache_service: CacheService = Depends(get_cache_service),
) -> Dict[str, Any]:
    """
    Check if contract analysis exists in cache.

    Body:
        - file_content: Base64 encoded file content
    """
    context = create_error_context(
        user_id=str(user.id), operation="check_contract_cache"
    )

    try:
        # Either accept pre-computed content_hash or file_content to compute it
        content_hash = request.get("content_hash")
        file_content = request.get("file_content")

        if not content_hash:
            if not file_content:
                raise HTTPException(
                    status_code=400,
                    detail="content_hash or file_content is required",
                )
            # Generate content hash from file content
            import base64

            content_bytes = base64.b64decode(file_content)
            content_hash = cache_service.generate_content_hash(content_bytes)

        # Check cache
        cached_result = await cache_service.check_contract_cache(content_hash)

        return {
            "status": "success",
            "data": {
                "content_hash": content_hash,
                "cache_hit": cached_result is not None,
                "cached_analysis": cached_result,
            },
        }

    except Exception as e:
        logger.error(f"Error checking contract cache: {str(e)}")
        raise handle_api_error(e, context, ErrorCategory.DATABASE)


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
        docs_repo = DocumentsRepository(user_id=UUID(user_id))
        document = await docs_repo.get_document(UUID(document_id), user_id=UUID(user_id))

        logger.debug(
            f"Document query result for {document_id}: {document is not None}"
        )

        if not document:
            logger.warning(f"Document {document_id} not found for user {user_id}")
            raise ValueError(f"Document not found or you don't have access to it")

        # Convert to dict for backward compatibility
        document = {
            "id": str(document.id),
            "user_id": str(document.user_id),
            "original_filename": document.original_filename,
            "storage_path": document.storage_path,
            "file_type": document.file_type,
            "file_size": document.file_size,
            "content_hash": document.content_hash,
            "processing_status": document.processing_status,
        }
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
    """Create contract record with cache integration using repository pattern."""
    try:
        contracts_repo = ContractsRepository()
        
        # Extract property address from document if available
        property_address = None
        processing_results = document.get("processing_results", {})
        if isinstance(processing_results, dict):
            contract_terms = processing_results.get("contract_terms", {})
            if isinstance(contract_terms, dict):
                property_address = contract_terms.get("property_address")
        
        contract = await contracts_repo.upsert_contract_by_content_hash(
            content_hash=content_hash,
            contract_type=document.get("contract_type", "purchase_agreement"),
            australian_state=user.australian_state,
            metadata={
                "property_address": property_address,
                "file_name": document.get("original_filename", "unknown"),
                "file_type": document.get("file_type", "pdf"),
                "user_id": str(user.id)
            }
        )

        if not contract.id:
            raise ValueError("Failed to create contract record via repository")

        logger.info(f"Repository: Created contract record: {contract.id}")
        return str(contract.id)

    except Exception as e:
        logger.error(f"Contract repository create failed for content_hash {content_hash}: {str(e)}")
        raise ValueError(f"Failed to create contract record: {str(e)}")


@retry_database_operation(max_attempts=3)
async def _create_analysis_record_with_cache(
    db_client: SupabaseClient,
    contract_id: str,
    user_id: str,
    content_hash: Optional[str] = None,
) -> str:
    """Create analysis record with cache integration using repository pattern."""
    if not content_hash:
        raise ValueError("content_hash is required for analysis record creation")

    try:
        # Use AnalysesRepository for shared analyses
        analyses_repo = AnalysesRepository(use_service_role=True)
        
        analysis = await analyses_repo.upsert_analysis(
            content_hash=content_hash,
            agent_version="1.0",
            status="pending",
            result={},
        )

        if not analysis.id:
            raise ValueError("Failed to create analysis record via repository")

        logger.info(f"Repository: Created analysis record: {analysis.id}")
        return str(analysis.id)

    except Exception as e:
        logger.error(f"Analysis repository upsert failed for content_hash {content_hash}: {str(e)}")
        raise ValueError(f"Failed to create analysis record: {str(e)}")


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
        from app.tasks import comprehensive_document_analysis

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

        # Use task manager to properly launch the task with context
        from app.core.task_context import task_manager

        await task_manager.initialize()
        # Extract the task parameters that should be passed to the task
        task_args = (
            task_params["document_id"],
            task_params["analysis_id"],
            task_params["contract_id"],
            task_params["user_id"],
            task_params["analysis_options"],
        )
        task = await task_manager.launch_user_task(
            comprehensive_document_analysis, task_params["analysis_id"], *task_args
        )

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


@router.get("/{contract_id}/analysis")
async def get_contract_analysis(
    contract_id: str,
    user: User = Depends(get_current_user),
) -> ContractAnalysisResultResponse:
    """Get contract analysis results with cache information."""

    try:
        # Diagnostic logging: request context
        logger.info(
            f"get_contract_analysis start: user_id={user.id}, contract_id={contract_id}"
        )

        # Get authenticated client
        db_client = await AuthContext.get_authenticated_client(require_auth=True)

        # Ensure database client is initialized
        if not hasattr(db_client, "_client") or db_client._client is None:
            await db_client.initialize()
        # Diagnostic logging: auth context token presence (length only)
        try:
            token = AuthContext.get_user_token()
            logger.info(
                f"AuthContext token present={bool(token)}, length={len(token) if token else 0}"
            )
        except Exception:
            logger.info("AuthContext token check failed (non-fatal)")

        # First check if user has access to this contract through user_contract_views
        user_contract_views_repo = UserContractViewsRepository()
        user_contract_views = await user_contract_views_repo.get_user_contract_views(
            str(user.id), limit=1000  # Get all user's contract views
        )

        user_content_hashes = []
        if user_contract_views:
            logger.info(
                f"user_contract_views rows for user {user.id}: {len(user_contract_views)}"
            )
            user_content_hashes = [
                view["content_hash"]
                for view in user_contract_views
                if view.get("content_hash")
            ]

        # Also check documents table for additional access
        docs_repo = DocumentsRepository(user_id=user.id)
        user_documents = await docs_repo.list_user_documents(limit=1000)
        
        if user_documents:
            logger.info(
                f"documents rows for user {user.id}: {len(user_documents)}"
            )
            doc_content_hashes = [
                doc.content_hash
                for doc in user_documents
                if doc.content_hash
            ]
            user_content_hashes.extend(doc_content_hashes)

        logger.info(
            f"Aggregated accessible content_hashes count for user {user.id}: {len(user_content_hashes)}"
        )
        if not user_content_hashes:
            logger.warning(
                f"No accessible content hashes found for user {user.id}; likely RLS/auth issue"
            )
            raise HTTPException(
                status_code=403, detail="You don't have access to any contracts"
            )

        # Remove duplicates
        user_content_hashes = list(set(user_content_hashes))

        # Get contract by ID to get its content_hash
        contracts_repo = ContractsRepository()
        contract = await contracts_repo.get_contract_by_id(contract_id)

        if not contract:
            raise HTTPException(status_code=404, detail="Contract not found")

        content_hash = contract.content_hash
        logger.info(
            f"Contract resolved: contract_id={contract_id}, content_hash={content_hash}"
        )

        # Verify the user has access to this specific content_hash
        if content_hash not in user_content_hashes:
            sample_hashes = list(user_content_hashes)[:5]
            logger.warning(
                "Access check failed: user does not have content_hash. "
                f"user_id={user.id}, contract_id={contract_id}, content_hash={content_hash}, "
                f"sample_accessible_hashes={sample_hashes}"
            )
            raise HTTPException(
                status_code=403, detail="You don't have access to this contract"
            )

        # Get analysis results using AnalysesRepository
        analyses_repo = AnalysesRepository(use_service_role=True)
        analysis = await analyses_repo.get_analysis_by_content_hash(content_hash)

        if not analysis:
            raise HTTPException(status_code=404, detail="Analysis not found")

        # Extract data from analysis result
        analysis_result = analysis.result or {}
        risk_score = None
        if analysis_result.get("risk_assessment", {}).get("overall_risk_score"):
            risk_score = analysis_result["risk_assessment"]["overall_risk_score"]
        elif analysis_result.get("executive_summary", {}).get("overall_risk_score"):
            risk_score = analysis_result["executive_summary"]["overall_risk_score"]

        # Enhanced response with cache information
        response = {
            "contract_id": contract_id,
            "analysis_status": analysis.status,
            "analysis_result": analysis_result,
            "risk_score": risk_score,
            "processing_time": None,  # Not stored in analyses table
            "created_at": analysis.created_at.isoformat() if analysis.created_at else None,
        }

        # Add cache information if available
        if analysis_result.get("cached_from"):
            response["cached"] = True
            response["cache_source"] = analysis_result["cached_from"]

        logger.info(
            f"get_contract_analysis success: user_id={user.id}, contract_id={contract_id}, status={analysis.status}"
        )
        return response

    except HTTPException:
        # Re-raise HTTPExceptions (validation errors) without modification
        raise
    except Exception as e:
        logger.error(f"Get analysis error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{contract_id}/report")
async def get_contract_analysis_report(
    contract_id: str,
    format: str = Query("json", description="Report format: json or pdf"),
    user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Get contract analysis report with download URL for PDF format.

    Returns:
        - For format=json: Analysis data
        - For format=pdf: Signed download URL
    """
    context = create_error_context(
        user_id=str(user.id),
        contract_id=contract_id,
        operation="get_contract_analysis_report",
    )

    try:
        # Get analysis data first
        analysis_data = await get_contract_analysis(contract_id, user)

        if format == "pdf":
            # Generate PDF and upload to storage, return signed URL
            from app.tasks import generate_pdf_report
            from app.core.auth_context import AuthContext
            import uuid

            # Get authenticated client for storage operations
            db_client = await AuthContext.get_authenticated_client(require_auth=True)

            # Generate PDF content
            pdf_content = await generate_pdf_report(analysis_data)

            # Create storage path
            analysis_id = analysis_data.get("analysis_id", str(uuid.uuid4()))
            storage_path = f"reports/{contract_id}/{analysis_id}.pdf"

            # Upload to storage bucket using wrapped client helpers
            upload_result = await db_client.upload_file(
                bucket="documents",
                path=storage_path,
                file=pdf_content,
                content_type="application/pdf",
            )

            if not upload_result.get("success"):
                raise ValueError("Failed to upload PDF report")

            # Generate signed URL (valid for 1 hour)
            signed_url = await db_client.generate_signed_url(
                "documents", storage_path, 3600
            )

            return {"download_url": signed_url, "format": "pdf"}
        else:
            # Return JSON analysis data
            return analysis_data

    except Exception as e:
        logger.error(f"Report generation error: {str(e)}")
        raise handle_api_error(e, context, ErrorCategory.CONTRACT_ANALYSIS)


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

        # First check if user has access to this contract through user_contract_views
        user_contract_views_repo = UserContractViewsRepository()
        user_contract_views = await user_contract_views_repo.get_user_contract_views(
            str(user.id), limit=1000  # Get all user's contract views
        )

        user_content_hashes = []
        if user_contract_views:
            user_content_hashes = [
                view["content_hash"]
                for view in user_contract_views
                if view.get("content_hash")
            ]

        # Also check documents table for additional access
        docs_repo = DocumentsRepository(user_id=user.id)
        user_documents = await docs_repo.list_user_documents(limit=1000)
        
        if user_documents:
            doc_content_hashes = [
                doc.content_hash
                for doc in user_documents
                if doc.content_hash
            ]
            user_content_hashes.extend(doc_content_hashes)

        if not user_content_hashes:
            raise HTTPException(
                status_code=403, detail="You don't have access to any contracts"
            )

        # Remove duplicates
        user_content_hashes = list(set(user_content_hashes))

        # Get contract by ID to get its content_hash
        contracts_repo = ContractsRepository()
        contract = await contracts_repo.get_contract_by_id(contract_id)

        if not contract:
            raise HTTPException(status_code=404, detail="Contract not found")

        content_hash = contract.content_hash

        # Verify the user has access to this specific content_hash
        if content_hash not in user_content_hashes:
            raise HTTPException(
                status_code=403, detail="You don't have access to this contract"
            )

        # Delete user's view of this contract (contracts and analyses are shared resources)
        # Find and delete the specific contract view by content_hash
        user_views = await user_contract_views_repo.get_user_contract_views(str(user.id))
        for view in user_views:
            if view.get("content_hash") == content_hash:
                await user_contract_views_repo.delete_contract_view(view["id"])
                break

        # Also remove user's documents with this content_hash
        user_docs_with_hash = [doc for doc in user_documents if doc.content_hash == content_hash]
        for doc in user_docs_with_hash:
            await docs_repo.delete_document(doc.id)

        return {
            "message": "Contract analysis deleted successfully",
            "contract_id": contract_id,
            "analyses_deleted": 0,  # Contracts and analyses are shared resources, so we don't delete them
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete contract error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
