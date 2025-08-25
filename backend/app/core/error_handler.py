"""
Enhanced Error Handling System for Real2.AI
Provides user-friendly error messages, retry mechanisms, and graceful degradation
"""

import logging
import traceback
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, UTC
from enum import Enum
from dataclasses import dataclass
from fastapi import HTTPException

logger = logging.getLogger(__name__)


class ErrorCategory(str, Enum):
    """Error categories for better organization and handling"""

    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    VALIDATION = "validation"
    DATABASE = "database"
    EXTERNAL_API = "external_api"
    FILE_PROCESSING = "file_processing"
    CONTRACT_ANALYSIS = "contract_analysis"
    NETWORK = "network"
    RATE_LIMIT = "rate_limit"
    SYSTEM = "system"
    USER_INPUT = "user_input"


class ErrorSeverity(str, Enum):
    """Error severity levels"""

    CRITICAL = "critical"  # System-breaking issues
    HIGH = "high"  # Feature-breaking issues
    MEDIUM = "medium"  # Degraded functionality
    LOW = "low"  # Minor issues, warnings


@dataclass
class ErrorContext:
    """Additional context for error handling"""

    user_id: Optional[str] = None
    contract_id: Optional[str] = None
    session_id: Optional[str] = None
    operation: Optional[str] = None
    retry_count: int = 0
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class EnhancedError:
    """Enhanced error with user-friendly messaging and recovery options"""

    category: ErrorCategory
    severity: ErrorSeverity
    code: str
    user_message: str
    technical_message: str
    suggested_actions: List[str]
    retry_eligible: bool = False
    max_retries: int = 0
    context: Optional[ErrorContext] = None
    timestamp: datetime = datetime.now(UTC)


class ErrorHandler:
    """Centralized error handling with user-friendly messages and retry logic"""

    def __init__(self):
        self.error_mappings = self._initialize_error_mappings()
        self.retry_strategies = self._initialize_retry_strategies()

    def _initialize_error_mappings(self) -> Dict[str, EnhancedError]:
        """Initialize comprehensive error mappings"""
        return {
            # Authentication Errors
            "token_expired": EnhancedError(
                category=ErrorCategory.AUTHENTICATION,
                severity=ErrorSeverity.MEDIUM,
                code="AUTH_001",
                user_message="Your session has expired. Please log in again.",
                technical_message="JWT token has expired",
                suggested_actions=[
                    "Click the login button to sign in again",
                    "Make sure your device's clock is set correctly",
                ],
                retry_eligible=False,
            ),
            "invalid_credentials": EnhancedError(
                category=ErrorCategory.AUTHENTICATION,
                severity=ErrorSeverity.MEDIUM,
                code="AUTH_002",
                user_message="The email or password you entered is incorrect.",
                technical_message="Invalid user credentials provided",
                suggested_actions=[
                    "Double-check your email address and password",
                    "Use the 'Forgot Password' link if needed",
                    "Contact support if you continue having issues",
                ],
                retry_eligible=False,
            ),
            "insufficient_credits": EnhancedError(
                category=ErrorCategory.AUTHORIZATION,
                severity=ErrorSeverity.HIGH,
                code="AUTH_003",
                user_message="You don't have enough credits to analyze this contract.",
                technical_message="User has insufficient credits for operation",
                suggested_actions=[
                    "Upgrade to a paid plan for more credits",
                    "Wait for your credits to reset next month",
                    "Contact support for credit assistance",
                ],
                retry_eligible=False,
            ),
            # File Processing Errors
            "file_too_large": EnhancedError(
                category=ErrorCategory.FILE_PROCESSING,
                severity=ErrorSeverity.MEDIUM,
                code="FILE_001",
                user_message="The file you uploaded is too large. Please use a file smaller than 10MB.",
                technical_message="Uploaded file exceeds size limit",
                suggested_actions=[
                    "Compress the PDF file using a PDF compressor",
                    "Split large documents into smaller sections",
                    "Try uploading a different file format",
                ],
                retry_eligible=False,
            ),
            "file_format_unsupported": EnhancedError(
                category=ErrorCategory.FILE_PROCESSING,
                severity=ErrorSeverity.MEDIUM,
                code="FILE_002",
                user_message="This file format isn't supported. Please upload a PDF, DOC, or DOCX file.",
                technical_message="Unsupported file format uploaded",
                suggested_actions=[
                    "Convert your file to PDF format",
                    "Save Word documents as .docx files",
                    "Contact support if your file should be supported",
                ],
                retry_eligible=False,
            ),
            "file_corrupted": EnhancedError(
                category=ErrorCategory.FILE_PROCESSING,
                severity=ErrorSeverity.MEDIUM,
                code="FILE_003",
                user_message="The file appears to be corrupted or unreadable.",
                technical_message="Unable to process corrupted file",
                suggested_actions=[
                    "Try uploading the file again",
                    "Open the file on your device to check if it works",
                    "Re-save or re-export the document",
                    "Contact the document sender for a new copy",
                ],
                retry_eligible=True,
                max_retries=2,
            ),
            "empty_file": EnhancedError(
                category=ErrorCategory.FILE_PROCESSING,
                severity=ErrorSeverity.MEDIUM,
                code="FILE_004",
                user_message="The uploaded file is empty. Please select a valid document with content.",
                technical_message="Zero-byte file uploaded",
                suggested_actions=[
                    "Select a different file that contains content",
                    "Check that the file isn't corrupted or empty",
                    "Ensure the document was saved properly before uploading",
                    "Try opening the file on your device first to verify it has content",
                ],
                retry_eligible=False,
            ),
            # Contract Analysis Errors
            "analysis_failed": EnhancedError(
                category=ErrorCategory.CONTRACT_ANALYSIS,
                severity=ErrorSeverity.HIGH,
                code="ANALYSIS_001",
                user_message="We couldn't analyze your contract. Our AI is having trouble understanding the document.",
                technical_message="Contract analysis workflow failed",
                suggested_actions=[
                    "Make sure the document is a property contract",
                    "Check that the text is clear and readable",
                    "Try uploading a higher quality scan",
                    "Contact support with your document details",
                ],
                retry_eligible=True,
                max_retries=3,
            ),
            "low_confidence_extraction": EnhancedError(
                category=ErrorCategory.CONTRACT_ANALYSIS,
                severity=ErrorSeverity.MEDIUM,
                code="ANALYSIS_002",
                user_message="We had trouble reading parts of your contract. The analysis may be incomplete.",
                technical_message="Low confidence in text extraction",
                suggested_actions=[
                    "Upload a clearer copy of the document",
                    "Check the analysis results carefully",
                    "Consult with a legal professional for confirmation",
                    "Contact support if important details are missing",
                ],
                retry_eligible=True,
                max_retries=2,
            ),
            "unsupported_contract_type": EnhancedError(
                category=ErrorCategory.CONTRACT_ANALYSIS,
                severity=ErrorSeverity.MEDIUM,
                code="ANALYSIS_003",
                user_message="This doesn't appear to be a standard property contract. Our analysis may be limited.",
                technical_message="Contract type not recognized or supported",
                suggested_actions=[
                    "Verify this is a property purchase contract",
                    "Check the analysis results for partial insights",
                    "Contact support for assistance with special contract types",
                    "Consider having the contract reviewed manually by a lawyer",
                ],
                retry_eligible=False,
            ),
            # Database Errors
            "database_connection": EnhancedError(
                category=ErrorCategory.DATABASE,
                severity=ErrorSeverity.CRITICAL,
                code="DB_001",
                user_message="We're experiencing technical difficulties. Please try again in a few moments.",
                technical_message="Database connection failed",
                suggested_actions=[
                    "Wait a few minutes and try again",
                    "Refresh the page",
                    "Check our status page for system updates",
                    "Contact support if the issue persists",
                ],
                retry_eligible=True,
                max_retries=3,
            ),
            "database_timeout": EnhancedError(
                category=ErrorCategory.DATABASE,
                severity=ErrorSeverity.HIGH,
                code="DB_002",
                user_message="The operation is taking longer than expected. Please try again.",
                technical_message="Database operation timed out",
                suggested_actions=[
                    "Wait a moment and try again",
                    "Check your internet connection",
                    "Try the operation during off-peak hours",
                ],
                retry_eligible=True,
                max_retries=2,
            ),
            # External API Errors
            "openai_api_limit": EnhancedError(
                category=ErrorCategory.EXTERNAL_API,
                severity=ErrorSeverity.HIGH,
                code="API_001",
                user_message="Our AI service is temporarily busy. Please try again in a few minutes.",
                technical_message="OpenAI API rate limit exceeded",
                suggested_actions=[
                    "Wait 5-10 minutes before trying again",
                    "Try during off-peak hours for faster processing",
                    "Contact support if you need urgent analysis",
                ],
                retry_eligible=True,
                max_retries=3,
            ),
            "api_service_unavailable": EnhancedError(
                category=ErrorCategory.EXTERNAL_API,
                severity=ErrorSeverity.CRITICAL,
                code="API_002",
                user_message="An essential service is temporarily unavailable. We're working to restore it.",
                technical_message="External API service unavailable",
                suggested_actions=[
                    "Check our status page for updates",
                    "Try again in 15-30 minutes",
                    "Follow us on social media for real-time updates",
                    "Contact support for urgent requests",
                ],
                retry_eligible=True,
                max_retries=2,
            ),
            # Network Errors
            "network_timeout": EnhancedError(
                category=ErrorCategory.NETWORK,
                severity=ErrorSeverity.MEDIUM,
                code="NET_001",
                user_message="The request timed out. Please check your connection and try again.",
                technical_message="Network request timeout",
                suggested_actions=[
                    "Check your internet connection",
                    "Refresh the page and try again",
                    "Try switching to a different network",
                    "Contact support if timeouts persist",
                ],
                retry_eligible=True,
                max_retries=3,
            ),
            # Rate Limiting
            "rate_limit_exceeded": EnhancedError(
                category=ErrorCategory.RATE_LIMIT,
                severity=ErrorSeverity.MEDIUM,
                code="RATE_001",
                user_message="You're sending requests too quickly. Please slow down and try again.",
                technical_message="Rate limit exceeded for user",
                suggested_actions=[
                    "Wait 60 seconds before trying again",
                    "Reduce the frequency of your requests",
                    "Upgrade your plan for higher limits",
                    "Contact support if you need higher limits",
                ],
                retry_eligible=True,
                max_retries=1,
            ),
            # Validation Errors
            "invalid_australian_state": EnhancedError(
                category=ErrorCategory.VALIDATION,
                severity=ErrorSeverity.MEDIUM,
                code="VAL_001",
                user_message="Please select a valid Australian state for accurate contract analysis.",
                technical_message="Invalid or missing Australian state parameter",
                suggested_actions=[
                    "Select your state from the dropdown menu",
                    "Make sure you're analyzing an Australian property contract",
                    "Contact support if your state isn't listed",
                ],
                retry_eligible=False,
            ),
            "missing_required_field": EnhancedError(
                category=ErrorCategory.VALIDATION,
                severity=ErrorSeverity.MEDIUM,
                code="VAL_002",
                user_message="Please fill in all required fields before continuing.",
                technical_message="Required field validation failed",
                suggested_actions=[
                    "Check for any highlighted empty fields",
                    "Make sure all required information is provided",
                    "Contact support if you're unsure what's required",
                ],
                retry_eligible=False,
            ),
        }

    def _initialize_retry_strategies(self) -> Dict[ErrorCategory, Dict[str, Any]]:
        """Initialize retry strategies for different error categories"""
        return {
            ErrorCategory.DATABASE: {
                "initial_delay": 1.0,
                "max_delay": 30.0,
                "exponential_base": 2.0,
                "jitter": True,
            },
            ErrorCategory.EXTERNAL_API: {
                "initial_delay": 5.0,
                "max_delay": 300.0,
                "exponential_base": 2.0,
                "jitter": True,
            },
            ErrorCategory.NETWORK: {
                "initial_delay": 2.0,
                "max_delay": 60.0,
                "exponential_base": 2.0,
                "jitter": True,
            },
            ErrorCategory.CONTRACT_ANALYSIS: {
                "initial_delay": 10.0,
                "max_delay": 180.0,
                "exponential_base": 1.5,
                "jitter": True,
            },
            ErrorCategory.FILE_PROCESSING: {
                "initial_delay": 3.0,
                "max_delay": 30.0,
                "exponential_base": 2.0,
                "jitter": False,
            },
        }

    def handle_error(
        self,
        error: Exception,
        context: Optional[ErrorContext] = None,
        fallback_category: ErrorCategory = ErrorCategory.SYSTEM,
    ) -> Tuple[EnhancedError, HTTPException]:
        """
        Handle any error and return enhanced error info plus HTTP response
        """
        try:
            # Map exception to enhanced error
            enhanced_error = self._map_exception_to_error(
                error, context, fallback_category
            )

            # Log the error appropriately
            self._log_error(enhanced_error, error, context)

            # Create HTTP response
            http_exception = self._create_http_exception(enhanced_error)

            return enhanced_error, http_exception

        except Exception as handler_error:
            # Fallback if error handler itself fails
            logger.critical(f"Error handler failed: {str(handler_error)}")
            fallback_error = self._create_fallback_error(error, context)
            fallback_http = HTTPException(
                status_code=500,
                detail="A system error occurred. Please try again later.",
            )
            return fallback_error, fallback_http

    def _map_exception_to_error(
        self,
        error: Exception,
        context: Optional[ErrorContext],
        fallback_category: ErrorCategory,
    ) -> EnhancedError:
        """Map Python exception to enhanced error"""

        error_str = str(error).lower()
        error_type = type(error).__name__

        # Try to identify error from message content
        if "token" in error_str and ("expired" in error_str or "invalid" in error_str):
            enhanced_error = self.error_mappings["token_expired"].copy()
        elif "credential" in error_str or "authentication" in error_str:
            enhanced_error = self.error_mappings["invalid_credentials"].copy()
        elif "credit" in error_str and "insufficient" in error_str:
            enhanced_error = self.error_mappings["insufficient_credits"].copy()
        elif "file" in error_str and "large" in error_str:
            enhanced_error = self.error_mappings["file_too_large"].copy()
        elif "format" in error_str and "unsupported" in error_str:
            enhanced_error = self.error_mappings["file_format_unsupported"].copy()
        elif "corrupted" in error_str or "unreadable" in error_str:
            enhanced_error = self.error_mappings["file_corrupted"].copy()
        elif "empty" in error_str and "file" in error_str:
            enhanced_error = self.error_mappings["empty_file"].copy()
        elif "analysis" in error_str and "failed" in error_str:
            enhanced_error = self.error_mappings["analysis_failed"].copy()
        elif "confidence" in error_str and "low" in error_str:
            enhanced_error = self.error_mappings["low_confidence_extraction"].copy()
        elif "database" in error_str and "connection" in error_str:
            enhanced_error = self.error_mappings["database_connection"].copy()
        elif "timeout" in error_str:
            if "database" in error_str or "db" in error_str:
                enhanced_error = self.error_mappings["database_timeout"].copy()
            else:
                enhanced_error = self.error_mappings["network_timeout"].copy()
        elif "rate limit" in error_str or "too many requests" in error_str:
            enhanced_error = self.error_mappings["rate_limit_exceeded"].copy()
        elif "openai" in error_str or "api" in error_str:
            if "limit" in error_str:
                enhanced_error = self.error_mappings["openai_api_limit"].copy()
            else:
                enhanced_error = self.error_mappings["api_service_unavailable"].copy()
        elif "state" in error_str and (
            "invalid" in error_str or "not found" in error_str
        ):
            enhanced_error = self.error_mappings["invalid_australian_state"].copy()
        elif "required" in error_str and "field" in error_str:
            enhanced_error = self.error_mappings["missing_required_field"].copy()
        else:
            # Create generic error for unmapped exceptions
            enhanced_error = EnhancedError(
                category=fallback_category,
                severity=ErrorSeverity.MEDIUM,
                code="SYS_001",
                user_message="Something went wrong. Please try again or contact support if the issue persists.",
                technical_message=f"{error_type}: {str(error)}",
                suggested_actions=[
                    "Try the operation again",
                    "Refresh the page",
                    "Check your internet connection",
                    "Contact support if the problem continues",
                ],
                retry_eligible=True,
                max_retries=2,
            )

        # Add context if provided
        if context:
            enhanced_error.context = context

        return enhanced_error

    def _log_error(
        self,
        enhanced_error: EnhancedError,
        original_error: Exception,
        context: Optional[ErrorContext],
    ):
        """Log error with appropriate level and context"""

        log_data = {
            "error_code": enhanced_error.code,
            "category": enhanced_error.category.value,
            "severity": enhanced_error.severity.value,
            "technical_message": enhanced_error.technical_message,
            "original_error": str(original_error),
            "traceback": traceback.format_exc(),
        }

        if context:
            log_data.update(
                {
                    "user_id": context.user_id,
                    "contract_id": context.contract_id,
                    "session_id": context.session_id,
                    "operation": context.operation,
                    "retry_count": context.retry_count,
                    "metadata": context.metadata,
                }
            )

        # Log at appropriate level
        if enhanced_error.severity == ErrorSeverity.CRITICAL:
            logger.critical("Critical error occurred", extra=log_data)
        elif enhanced_error.severity == ErrorSeverity.HIGH:
            logger.error("High severity error occurred", extra=log_data)
        elif enhanced_error.severity == ErrorSeverity.MEDIUM:
            logger.warning("Medium severity error occurred", extra=log_data)
        else:
            logger.info("Low severity error occurred", extra=log_data)

    def _create_http_exception(self, enhanced_error: EnhancedError) -> HTTPException:
        """Create HTTP exception from enhanced error"""

        # Map severity to HTTP status codes
        status_mapping = {
            ErrorSeverity.CRITICAL: 503,  # Service Unavailable
            ErrorSeverity.HIGH: 500,  # Internal Server Error
            ErrorSeverity.MEDIUM: 400,  # Bad Request
            ErrorSeverity.LOW: 400,  # Bad Request
        }

        # Special cases for specific categories
        if enhanced_error.category == ErrorCategory.AUTHENTICATION:
            status_code = 401  # Unauthorized
        elif enhanced_error.category == ErrorCategory.AUTHORIZATION:
            status_code = 403  # Forbidden
        elif enhanced_error.category == ErrorCategory.VALIDATION:
            status_code = 422  # Unprocessable Entity
        elif enhanced_error.category == ErrorCategory.RATE_LIMIT:
            status_code = 429  # Too Many Requests
        else:
            status_code = status_mapping.get(enhanced_error.severity, 500)

        # Create detailed response
        detail = {
            "error_code": enhanced_error.code,
            "message": enhanced_error.user_message,
            "category": enhanced_error.category.value,
            "severity": enhanced_error.severity.value,
            "suggested_actions": enhanced_error.suggested_actions,
            "retry_eligible": enhanced_error.retry_eligible,
            "timestamp": enhanced_error.timestamp.isoformat(),
        }

        if enhanced_error.retry_eligible:
            detail["max_retries"] = enhanced_error.max_retries
            if enhanced_error.context and enhanced_error.context.retry_count > 0:
                detail["retry_count"] = enhanced_error.context.retry_count

        return HTTPException(status_code=status_code, detail=detail)

    def _create_fallback_error(
        self, error: Exception, context: Optional[ErrorContext]
    ) -> EnhancedError:
        """Create fallback error when main error handling fails"""
        return EnhancedError(
            category=ErrorCategory.SYSTEM,
            severity=ErrorSeverity.CRITICAL,
            code="SYS_999",
            user_message="A critical system error occurred. Please contact support.",
            technical_message=f"Error handler failed processing: {str(error)}",
            suggested_actions=[
                "Contact support immediately",
                "Include details about what you were doing when this happened",
            ],
            retry_eligible=False,
            context=context,
        )

    def create_validation_error(
        self, field_name: str, value: Any, message: str
    ) -> HTTPException:
        """Create user-friendly validation error"""

        detail = {
            "error_code": "VAL_003",
            "message": f"Invalid {field_name}: {message}",
            "category": ErrorCategory.VALIDATION.value,
            "severity": ErrorSeverity.MEDIUM.value,
            "field": field_name,
            "value": str(value),
            "suggested_actions": [
                f"Please provide a valid {field_name}",
                "Check the format requirements",
                "Contact support if you need help",
            ],
            "retry_eligible": False,
            "timestamp": datetime.now(UTC).isoformat(),
        }

        return HTTPException(status_code=422, detail=detail)


# Global error handler instance
error_handler = ErrorHandler()


def handle_api_error(
    error: Exception,
    context: Optional[ErrorContext] = None,
    fallback_category: ErrorCategory = ErrorCategory.SYSTEM,
) -> HTTPException:
    """
    Convenience function to handle API errors
    Returns HTTP exception ready to be raised
    """
    enhanced_error, http_exception = error_handler.handle_error(
        error, context, fallback_category
    )
    return http_exception


def create_error_context(
    user_id: Optional[str] = None,
    contract_id: Optional[str] = None,
    session_id: Optional[str] = None,
    operation: Optional[str] = None,
    retry_count: int = 0,
    **metadata,
) -> ErrorContext:
    """Convenience function to create error context"""
    return ErrorContext(
        user_id=user_id,
        contract_id=contract_id,
        session_id=session_id,
        operation=operation,
        retry_count=retry_count,
        metadata=metadata if metadata else None,
    )
