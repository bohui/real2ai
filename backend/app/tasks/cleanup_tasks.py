"""Cleanup tasks for Real2.AI - handling orphaned records and storage issues."""

import asyncio
import logging
from datetime import datetime, timedelta, UTC

from app.core.celery import celery_app
from app.clients.factory import get_service_supabase_client
from app.services.document_service import DocumentService
from app.services.repositories.analyses_repository import AnalysesRepository

logger = logging.getLogger(__name__)


@celery_app.task(bind=True)
def cleanup_orphaned_documents(self):
    """Cleanup orphaned document records where files don't exist in storage"""

    async def _async_cleanup():
        document_service = DocumentService(use_llm_document_processing=True)
        db_client = None

        try:
            # Get service database client (elevated permissions)
            db_client = await get_service_supabase_client()

            # Find documents that might be orphaned (uploaded/processing status, older than 1 hour)
            cutoff_time = datetime.now(UTC) - timedelta(hours=1)

            potentially_orphaned = (
                db_client.table("documents")
                .select("*")
                .in_("processing_status", ["uploaded", "processing"])
                .lt("created_at", cutoff_time.isoformat())
                .execute()
            )

            if not potentially_orphaned.data:
                logger.info("No potentially orphaned documents found")
                return {"cleaned_up": 0, "verified": 0}

            cleaned_up = 0
            verified = 0

            for document in potentially_orphaned.data:
                try:
                    # Try to access the file
                    await document_service.get_file_content(document["storage_path"])
                    verified += 1
                    logger.debug(f"Document {document['id']} file verified in storage")

                except Exception as e:
                    # File doesn't exist - mark as failed/orphaned
                    logger.warning(
                        f"Orphaned document found: {document['id']} - {document['storage_path']}"
                    )

                    db_client.table("documents").update(
                        {
                            "processing_status": "failed",
                            "processing_results": {
                                "error": "File not found in storage - orphaned record",
                                "storage_path": document["storage_path"],
                                "cleanup_timestamp": datetime.now(UTC).isoformat(),
                                "original_error": str(e),
                            },
                        }
                    ).eq("id", document["id"]).execute()

                    cleaned_up += 1

            logger.info(
                f"Cleanup completed: {cleaned_up} orphaned documents marked as failed, {verified} verified"
            )
            return {"cleaned_up": cleaned_up, "verified": verified}

        except Exception as e:
            logger.error(f"Orphaned document cleanup failed: {str(e)}")
            raise

    return asyncio.run(_async_cleanup())


@celery_app.task(bind=True)
def cleanup_failed_analyses(self):
    """Cleanup failed analyses older than 24 hours"""

    async def _async_cleanup_analyses():
        try:
            # Use AnalysesRepository with service role
            analyses_repo = AnalysesRepository(use_service_role=True)

            # Find failed analyses older than 24 hours
            cutoff_time = datetime.now(UTC) - timedelta(hours=24)

            # Get failed analyses (this is a simplified implementation - 
            # you might need to add a method to get analyses by status and date)
            try:
                # For now, use the stats method to check if there are any analyses
                stats = await analyses_repo.get_analysis_stats()
                if stats.get("total_analyses", 0) == 0:
                    logger.info("No analyses found")
                    return {"cleaned_up": 0}
                
                # In a full implementation, you would add a method like:
                # old_failures = await analyses_repo.get_analyses_by_status_and_date(
                #     status="failed", before_date=cutoff_time
                # )
                
                logger.info("Failed analysis cleanup: Repository method needs implementation for date filtering")
                return {"cleaned_up": 0}
                
            except Exception as e:
                logger.error(f"Failed to get old failed analyses: {str(e)}")
                return {"cleaned_up": 0}

        except Exception as e:
            logger.error(f"Failed analysis cleanup failed: {str(e)}")
            raise

    return asyncio.run(_async_cleanup_analyses())


@celery_app.task(bind=True)
def verify_storage_consistency(self):
    """Verify consistency between database records and storage files"""

    async def _async_verify():
        document_service = DocumentService(use_llm_document_processing=True)
        db_client = None

        try:
            # Get service database client (elevated permissions)
            db_client = await get_service_supabase_client()

            # Get all processed documents from last 7 days
            cutoff_time = datetime.now(UTC) - timedelta(days=7)

            recent_docs = (
                db_client.table("documents")
                .select("*")
                .eq("processing_status", "processed")
                .gt("created_at", cutoff_time.isoformat())
                .execute()
            )

            if not recent_docs.data:
                logger.info("No recent processed documents found")
                return {"verified": 0, "inconsistent": 0}

            verified = 0
            inconsistent = 0

            for document in recent_docs.data:
                try:
                    # Try to access the file
                    await document_service.get_file_content(document["storage_path"])
                    verified += 1

                except Exception as e:
                    # Inconsistency found
                    logger.warning(
                        f"Storage inconsistency found for processed document {document['id']}: {document['storage_path']}"
                    )

                    # Log the inconsistency but don't automatically fix processed documents
                    inconsistent += 1

            logger.info(
                f"Storage verification completed: {verified} consistent, {inconsistent} inconsistent"
            )
            return {"verified": verified, "inconsistent": inconsistent}

        except Exception as e:
            logger.error(f"Storage verification failed: {str(e)}")
            raise

    return asyncio.run(_async_verify())
