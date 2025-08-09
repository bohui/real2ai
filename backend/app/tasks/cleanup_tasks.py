"""Cleanup tasks for Real2.AI - handling orphaned records and storage issues."""

import asyncio
import logging
from typing import List, Dict, Any
from datetime import datetime, timedelta, UTC

from app.core.celery import celery_app
from app.clients.factory import get_service_supabase_client
from app.services.document_service import DocumentService

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
    """Cleanup failed contract analyses older than 24 hours"""

    async def _async_cleanup_analyses():
        db_client = None

        try:
            # Get service database client (elevated permissions)
            db_client = await get_service_supabase_client()

            # Find failed analyses older than 24 hours
            cutoff_time = datetime.now(UTC) - timedelta(hours=24)

            old_failures = (
                db_client.table("contract_analyses")
                .select("*")
                .eq("status", "failed")
                .lt("created_at", cutoff_time.isoformat())
                .execute()
            )

            if not old_failures.data:
                logger.info("No old failed analyses found")
                return {"cleaned_up": 0}

            # Archive old failures (move to analysis_result as historical record)
            cleaned_up = 0
            for analysis in old_failures.data:
                try:
                    # Update with archived status
                    current_result = analysis.get("analysis_result", {})
                    archived_result = {
                        **current_result,
                        "archived": True,
                        "archived_at": datetime.now(UTC).isoformat(),
                        "original_failure_date": analysis.get("updated_at"),
                    }

                    db_client.table("contract_analyses").update(
                        {
                            "status": "archived_failure",
                            "analysis_result": archived_result,
                        }
                    ).eq("id", analysis["id"]).execute()

                    cleaned_up += 1

                except Exception as e:
                    logger.error(
                        f"Failed to archive analysis {analysis['id']}: {str(e)}"
                    )
                    continue

            logger.info(f"Archived {cleaned_up} old failed analyses")
            return {"cleaned_up": cleaned_up}

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
