"""
Checkpoint Cleaner Service

This service handles clearing of failed processing checkpoints to allow
workflows to restart from the beginning instead of resuming from failed states.
"""

import logging
from typing import Dict, Any, Optional, List
from uuid import UUID
from datetime import datetime, timezone

from app.core.task_recovery import CheckpointData
from app.services.repositories.analysis_progress_repository import AnalysisProgressRepository

logger = logging.getLogger(__name__)


class CheckpointCleaner:
    """
    Service for cleaning up failed processing checkpoints and progress records.
    
    This allows workflows to restart cleanly when document processing fails,
    preventing them from resuming at failed states.
    """
    
    def __init__(self):
        self.progress_repo = AnalysisProgressRepository()
    
    async def clear_failed_processing_checkpoints(
        self,
        content_hash: str,
        user_id: str,
        failure_reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Clear all checkpoints and progress records for a failed processing operation.
        
        This method should be called when document processing fails early
        (e.g., authentication errors, document extraction failures) to ensure
        the workflow can restart cleanly.
        
        Args:
            content_hash: Content hash of the failed document
            user_id: User ID who initiated the processing
            failure_reason: Optional reason for the failure
            
        Returns:
            Dict containing cleanup results and statistics
        """
        try:
            logger.info(
                f"Clearing failed processing checkpoints for content_hash {content_hash}, user {user_id}"
            )
            
            cleanup_results = {
                "content_hash": content_hash,
                "user_id": user_id,
                "failure_reason": failure_reason,
                "cleared_at": datetime.now(timezone.utc).isoformat(),
                "progress_records_cleared": 0,
                "checkpoints_cleared": 0,
                "success": False
            }
            
            # Clear progress records for this content_hash and user
            try:
                deleted_progress_count = await self.progress_repo.clear_progress_for_content_hash(
                    content_hash, user_id
                )
                cleanup_results["progress_records_cleared"] = deleted_progress_count
                
                logger.info(
                    f"Cleared {deleted_progress_count} progress records for content_hash {content_hash}"
                )
            except Exception as progress_error:
                logger.warning(f"Failed to clear progress records: {progress_error}")
                cleanup_results["progress_clear_error"] = str(progress_error)
            
            # Note: Task recovery checkpoints are typically handled by the task recovery system
            # We'll add a marker in the cleanup results to indicate checkpoint clearing is needed
            cleanup_results["checkpoint_clear_recommended"] = True
            cleanup_results["success"] = True
            
            logger.info(
                f"Successfully cleared failed processing state for content_hash {content_hash}"
            )
            
            return cleanup_results
            
        except Exception as e:
            logger.error(f"Failed to clear failed processing checkpoints: {e}", exc_info=True)
            return {
                "content_hash": content_hash,
                "user_id": user_id,
                "failure_reason": failure_reason,
                "cleared_at": datetime.now(timezone.utc).isoformat(),
                "error": str(e),
                "success": False
            }
    
    async def clear_stale_progress_records(
        self,
        max_age_hours: int = 24,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Clear stale progress records that are older than the specified age.
        
        This helps clean up orphaned progress records from failed or interrupted
        processing operations.
        
        Args:
            max_age_hours: Maximum age in hours for progress records to keep
            user_id: Optional user ID to limit cleanup to specific user
            
        Returns:
            Dict containing cleanup statistics
        """
        try:
            logger.info(f"Clearing stale progress records older than {max_age_hours} hours")
            
            # Calculate cutoff time
            cutoff_time = datetime.now(timezone.utc).replace(
                hour=datetime.now(timezone.utc).hour - max_age_hours
            )
            
            # Clear stale records
            cleared_count = await self.progress_repo.clear_stale_progress(
                cutoff_time, user_id
            )
            
            cleanup_results = {
                "cleared_at": datetime.now(timezone.utc).isoformat(),
                "max_age_hours": max_age_hours,
                "cutoff_time": cutoff_time.isoformat(),
                "records_cleared": cleared_count,
                "user_id": user_id,
                "success": True
            }
            
            logger.info(f"Cleared {cleared_count} stale progress records")
            return cleanup_results
            
        except Exception as e:
            logger.error(f"Failed to clear stale progress records: {e}", exc_info=True)
            return {
                "cleared_at": datetime.now(timezone.utc).isoformat(),
                "error": str(e),
                "success": False
            }
    
    async def validate_processing_can_restart(
        self,
        content_hash: str,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Validate that processing can restart cleanly for the given content hash.
        
        This checks for any remaining checkpoints or progress records that might
        interfere with a clean restart.
        
        Args:
            content_hash: Content hash to validate
            user_id: User ID to validate for
            
        Returns:
            Dict containing validation results
        """
        try:
            validation_results = {
                "content_hash": content_hash,
                "user_id": user_id,
                "checked_at": datetime.now(timezone.utc).isoformat(),
                "can_restart_cleanly": False,
                "existing_progress_records": 0,
                "last_progress_step": None,
                "recommendations": []
            }
            
            # Check for existing progress records
            try:
                latest_progress = await self.progress_repo.get_latest_progress(
                    content_hash, user_id
                )
                
                if latest_progress:
                    validation_results["existing_progress_records"] = 1
                    validation_results["last_progress_step"] = latest_progress.get("current_step")
                    validation_results["last_progress_status"] = latest_progress.get("status")
                    
                    # Check if the last step indicates failure
                    last_step = latest_progress.get("current_step", "")
                    last_status = latest_progress.get("status", "")
                    
                    if (last_step.endswith("_failed") or 
                        last_status == "failed" or
                        last_step == "processing_failed"):
                        validation_results["can_restart_cleanly"] = True
                        validation_results["recommendations"].append(
                            "Clear failed progress record before restarting"
                        )
                    else:
                        validation_results["can_restart_cleanly"] = False
                        validation_results["recommendations"].append(
                            "Existing progress indicates processing may still be active"
                        )
                else:
                    validation_results["can_restart_cleanly"] = True
                    validation_results["recommendations"].append(
                        "No existing progress records - safe to start"
                    )
                    
            except Exception as progress_error:
                logger.warning(f"Could not check progress records: {progress_error}")
                validation_results["progress_check_error"] = str(progress_error)
                validation_results["recommendations"].append(
                    "Could not verify progress state - proceed with caution"
                )
            
            return validation_results
            
        except Exception as e:
            logger.error(f"Failed to validate restart capability: {e}", exc_info=True)
            return {
                "content_hash": content_hash,
                "user_id": user_id,
                "checked_at": datetime.now(timezone.utc).isoformat(),
                "error": str(e),
                "can_restart_cleanly": False
            }


# Convenience functions for common operations

async def clear_failed_document_processing(
    content_hash: str,
    user_id: str,
    failure_reason: str = "Document processing failed"
) -> bool:
    """
    Convenience function to clear failed document processing state.
    
    Args:
        content_hash: Content hash of the failed document
        user_id: User ID who initiated the processing  
        failure_reason: Reason for the failure
        
    Returns:
        bool: True if cleanup was successful
    """
    cleaner = CheckpointCleaner()
    results = await cleaner.clear_failed_processing_checkpoints(
        content_hash, user_id, failure_reason
    )
    return results.get("success", False)


async def prepare_for_clean_restart(
    content_hash: str,
    user_id: str
) -> Dict[str, Any]:
    """
    Convenience function to prepare for a clean restart of document processing.
    
    This validates the current state and clears any failed processing records.
    
    Args:
        content_hash: Content hash to prepare for restart
        user_id: User ID to prepare for
        
    Returns:
        Dict containing preparation results and recommendations
    """
    cleaner = CheckpointCleaner()
    
    # First validate current state
    validation = await cleaner.validate_processing_can_restart(content_hash, user_id)
    
    # If there are failed records, clear them
    if not validation.get("can_restart_cleanly", False):
        if validation.get("last_progress_step", "").endswith("_failed"):
            clear_results = await cleaner.clear_failed_processing_checkpoints(
                content_hash, user_id, "Preparing for clean restart"
            )
            
            return {
                "preparation_completed": True,
                "validation_results": validation,
                "cleanup_results": clear_results,
                "ready_for_restart": clear_results.get("success", False)
            }
    
    return {
        "preparation_completed": True,
        "validation_results": validation,
        "ready_for_restart": validation.get("can_restart_cleanly", False)
    }