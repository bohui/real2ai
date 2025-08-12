"""
Documents Repository - User-scoped document operations

This repository handles document-level operations with proper RLS enforcement.
Documents are user-scoped and this repository provides CRUD operations
with integrated JWT-based authentication.
"""

from typing import Dict, List, Optional, Any
from uuid import UUID
from dataclasses import dataclass
from datetime import datetime
import logging
import json

from app.database.connection import get_user_connection

logger = logging.getLogger(__name__)


@dataclass
class Document:
    """Document model aligned with current `documents` schema."""

    id: UUID
    user_id: UUID
    original_filename: str
    storage_path: str
    file_type: str
    file_size: int
    content_hash: Optional[str]
    processing_status: str
    processing_started_at: Optional[datetime] = None
    processing_completed_at: Optional[datetime] = None
    processing_errors: Optional[Dict[str, Any]] = None
    artifact_text_id: Optional[UUID] = None
    total_pages: Optional[int] = 0
    total_word_count: Optional[int] = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class DocumentsRepository:
    """Repository for user-scoped document operations"""

    def __init__(self, user_id: Optional[UUID] = None):
        """
        Initialize documents repository.

        Args:
            user_id: Optional user ID (uses auth context if not provided)
        """
        self.user_id = user_id

    async def create_document(self, document_data: Dict[str, Any]) -> Document:
        """
        Create a new document aligned with current schema.

        Expected keys in document_data:
        - id, user_id, original_filename, storage_path, file_type,
          file_size, content_hash, processing_status,
          contract_type (optional), australian_state (optional),
          text_extraction_method (optional)

        Returns:
        - Document dataclass instance
        """
        async with get_user_connection(self.user_id) as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO documents (
                    id, user_id, original_filename, storage_path, file_type,
                    file_size, content_hash, processing_status,
                    contract_type, australian_state, text_extraction_method
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                RETURNING 
                    id, user_id, original_filename, storage_path, file_type,
                    file_size, content_hash, processing_status, processing_started_at,
                    processing_completed_at, processing_errors, artifact_text_id,
                    total_pages, total_word_count, created_at, updated_at
                """,
                document_data.get("id"),
                document_data.get("user_id"),
                document_data.get("original_filename"),
                document_data.get("storage_path"),
                document_data.get("file_type"),
                document_data.get("file_size"),
                document_data.get("content_hash"),
                document_data.get("processing_status", "uploaded"),
                document_data.get("contract_type"),
                document_data.get("australian_state"),
                document_data.get("text_extraction_method"),
            )

            return Document(
                id=row["id"],
                user_id=row["user_id"],
                original_filename=row["original_filename"],
                storage_path=row["storage_path"],
                file_type=row["file_type"],
                file_size=row["file_size"],
                content_hash=row["content_hash"],
                processing_status=row["processing_status"],
                processing_started_at=row["processing_started_at"],
                processing_completed_at=row["processing_completed_at"],
                processing_errors=row["processing_errors"],
                artifact_text_id=row["artifact_text_id"],
                total_pages=row["total_pages"],
                total_word_count=row["total_word_count"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )

    async def get_document(self, document_id: UUID) -> Optional[Document]:
        """
        Get document by ID.

        Args:
            document_id: Document ID

        Returns:
            Document or None if not found
        """
        async with get_user_connection(self.user_id) as conn:
            logger.debug(
                "[DocumentsRepository] get_document",
                extra={
                    "document_id": str(document_id),
                    "repo_user_id": str(self.user_id) if self.user_id else None,
                },
            )
            row = await conn.fetchrow(
                """
                SELECT id, user_id, original_filename, storage_path, file_type, file_size, 
                       content_hash, processing_status, processing_started_at,
                       processing_completed_at, processing_errors, artifact_text_id,
                       total_pages, total_word_count, created_at, updated_at
                FROM documents
                WHERE id = $1
                """,
                document_id,
            )

            if not row:
                logger.debug(
                    "[DocumentsRepository] get_document: not found",
                    extra={"document_id": str(document_id)},
                )
                return None

            logger.debug(
                "[DocumentsRepository] get_document: row fetched",
                extra={"document_id": str(document_id)},
            )
            return Document(
                id=row["id"],
                user_id=row["user_id"],
                original_filename=row["original_filename"],
                storage_path=row["storage_path"],
                file_size=row["file_size"],
                file_type=row["file_type"],
                content_hash=row["content_hash"],
                processing_status=row["processing_status"],
                processing_started_at=row["processing_started_at"],
                processing_completed_at=row["processing_completed_at"],
                processing_errors=row["processing_errors"],
                artifact_text_id=row["artifact_text_id"],
                total_pages=row["total_pages"],
                total_word_count=row["total_word_count"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )

    async def update_document_status(
        self,
        document_id: UUID,
        status: str,
        error_details: Optional[Dict[str, Any]] = None,
        processing_started_at: Optional[datetime] = None,
        processing_completed_at: Optional[datetime] = None,
    ) -> bool:
        """
        Update document processing status.

        Args:
            document_id: Document ID
            status: New processing status
            error_details: Optional error details
            processing_started_at: Optional start time
            processing_completed_at: Optional completion time

        Returns:
            True if update successful, False otherwise
        """
        async with get_user_connection(self.user_id) as conn:
            # Build dynamic query based on provided parameters
            set_clauses = ["processing_status = $1", "updated_at = now()"]
            params = [status]
            param_count = 1

            if error_details is not None:
                param_count += 1
                set_clauses.append(f"processing_errors = ${param_count}::jsonb")
                params.append(json.dumps(error_details) if error_details is not None else None)

            if processing_started_at is not None:
                param_count += 1
                set_clauses.append(
                    f"processing_started_at = COALESCE(processing_started_at, ${param_count})"
                )
                params.append(processing_started_at)

            if processing_completed_at is not None:
                param_count += 1
                set_clauses.append(f"processing_completed_at = ${param_count}")
                params.append(processing_completed_at)

            # Add WHERE clause parameters
            param_count += 1
            params.append(document_id)

            query = f"""
                UPDATE documents 
                SET {', '.join(set_clauses)}
                WHERE id = ${param_count}
            """

            result = await conn.execute(query, *params)
            return result.split()[-1] == "1"

    async def update_document_metrics(
        self, document_id: UUID, aggregated_metrics: Dict[str, Any]
    ) -> bool:
        """
        Update document with aggregated metrics.

        Args:
            document_id: Document ID
            aggregated_metrics: Dictionary containing metrics like:
                - total_pages: int
                - total_word_count: int
                - artifact_text_id: UUID

        Returns:
            True if update successful, False otherwise
        """
        async with get_user_connection(self.user_id) as conn:
            set_clauses = ["updated_at = now()"]
            params = []
            param_count = 0

            if "total_pages" in aggregated_metrics:
                param_count += 1
                set_clauses.append(f"total_pages = ${param_count}")
                params.append(aggregated_metrics["total_pages"])

            if "total_word_count" in aggregated_metrics:
                param_count += 1
                set_clauses.append(f"total_word_count = ${param_count}")
                params.append(aggregated_metrics["total_word_count"])

            if "artifact_text_id" in aggregated_metrics:
                param_count += 1
                set_clauses.append(f"artifact_text_id = ${param_count}")
                params.append(aggregated_metrics["artifact_text_id"])

            if param_count == 0:
                # No metrics to update
                return True

            # Add WHERE clause parameters
            param_count += 1
            params.append(document_id)

            query = f"""
                UPDATE documents 
                SET {', '.join(set_clauses)}
                WHERE id = ${param_count}
            """

            result = await conn.execute(query, *params)
            return result.split()[-1] == "1"

    async def list_user_documents(
        self, limit: int = 50, offset: int = 0, status_filter: Optional[str] = None
    ) -> List[Document]:
        """
        List user's documents with optional filtering.

        Args:
            limit: Maximum number of documents to return
            offset: Offset for pagination
            status_filter: Optional status filter

        Returns:
            List of Document objects
        """
        async with get_user_connection(self.user_id) as conn:
            where_clause = ""
            params = [limit, offset]
            param_count = 2

            if status_filter:
                param_count += 1
                where_clause = f"WHERE processing_status = ${param_count}"
                params.append(status_filter)

            query = f"""
                SELECT id, user_id, original_filename, storage_path, file_type, file_size, 
                       content_hash, processing_status, processing_started_at,
                       processing_completed_at, processing_errors, artifact_text_id,
                       total_pages, total_word_count, created_at, updated_at
                FROM documents
                {where_clause}
                ORDER BY created_at DESC
                LIMIT $1 OFFSET $2
            """

            rows = await conn.fetch(query, *params)

            return [
                Document(
                    id=row["id"],
                    user_id=row["user_id"],
                    original_filename=row["original_filename"],
                    storage_path=row["storage_path"],
                    file_size=row["file_size"],
                    file_type=row["file_type"],
                    content_hash=row["content_hash"],
                    processing_status=row["processing_status"],
                    processing_started_at=row["processing_started_at"],
                    processing_completed_at=row["processing_completed_at"],
                    processing_errors=row["processing_errors"],
                    artifact_text_id=row["artifact_text_id"],
                    total_pages=row["total_pages"],
                    total_word_count=row["total_word_count"],
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                )
                for row in rows
            ]

    async def delete_document(self, document_id: UUID) -> bool:
        """
        Delete a document.

        Args:
            document_id: Document ID

        Returns:
            True if deletion successful, False otherwise
        """
        async with get_user_connection(self.user_id) as conn:
            result = await conn.execute(
                "DELETE FROM documents WHERE id = $1", document_id
            )
            return result.split()[-1] == "1"

    async def get_documents_by_status(self, status: str) -> List[Document]:
        """
        Get documents by processing status.

        Args:
            status: Processing status to filter by

        Returns:
            List of Document objects
        """
        return await self.list_user_documents(status_filter=status)

    async def batch_update_status(
        self,
        document_ids: List[UUID],
        status: str,
        error_details: Optional[Dict[str, Any]] = None,
    ) -> int:
        """
        Batch update multiple documents' status.

        Args:
            document_ids: List of document IDs
            status: New processing status
            error_details: Optional error details

        Returns:
            Number of documents updated
        """
        if not document_ids:
            return 0

        async with get_user_connection(self.user_id) as conn:
            query_params = [status]
            set_clauses = ["processing_status = $1", "updated_at = now()"]
            param_count = 1

            if error_details is not None:
                param_count += 1
                set_clauses.append(f"processing_errors = ${param_count}::jsonb")
                query_params.append(json.dumps(error_details) if error_details is not None else None)

            param_count += 1
            query_params.append(document_ids)

            query = f"""
                UPDATE documents 
                SET {', '.join(set_clauses)}
                WHERE id = ANY(${param_count})
            """

            result = await conn.execute(query, *query_params)
            return int(result.split()[-1])

    async def create_user_contract_view(
        self,
        *,
        user_id: UUID,
        content_hash: str,
        property_address: Optional[str] = None,
        source: str = "upload",
    ) -> bool:
        """Create a `user_contract_views` record for the user."""
        async with get_user_connection(self.user_id) as conn:
            result = await conn.execute(
                """
                INSERT INTO user_contract_views (user_id, content_hash, property_address, source)
                VALUES ($1, $2, $3, $4)
                """,
                user_id,
                content_hash,
                property_address,
                source,
            )
            return result.split()[-1] == "1"

    async def get_user_contract_views(
        self, content_hash: str, user_id: str, limit: int = 1
    ) -> List[Dict[str, Any]]:
        """Get user_contract_views records for content_hash and user_id."""
        async with get_user_connection(self.user_id) as conn:
            rows = await conn.fetch(
                """
                SELECT *
                FROM user_contract_views
                WHERE content_hash = $1 AND user_id = $2
                ORDER BY created_at DESC
                LIMIT $3
                """,
                content_hash,
                UUID(user_id),
                limit,
            )
            return [dict(row) for row in rows]

    async def get_documents_by_content_hash(
        self, content_hash: str, user_id: str, columns: str = "*"
    ) -> List[Document]:
        """
        Get documents by content_hash and user_id.

        Args:
            content_hash: Content hash to filter by
            user_id: User ID as string
            columns: Columns to select (default: all)

        Returns:
            List of Document objects
        """
        async with get_user_connection(self.user_id) as conn:
            if columns == "*":
                columns = """id, user_id, original_filename, storage_path, file_type, file_size, 
                            content_hash, processing_status, processing_started_at,
                            processing_completed_at, processing_errors, artifact_text_id,
                            total_pages, total_word_count, created_at, updated_at"""

            rows = await conn.fetch(
                f"""
                SELECT {columns}
                FROM documents
                WHERE content_hash = $1 AND user_id = $2
                ORDER BY created_at DESC
                """,
                content_hash,
                UUID(user_id),
            )

            # Only construct full `Document` objects when selecting all columns
            logger.debug(
                "[DocumentsRepository] get_documents_by_content_hash fetched rows",
                extra={
                    "content_hash": content_hash,
                    "user_id": user_id,
                    "columns": columns,
                    "row_count": len(rows),
                },
            )
            if columns.strip() == "*":
                return [
                    Document(
                        id=row["id"],
                        user_id=row["user_id"],
                        original_filename=row["original_filename"],
                        storage_path=row["storage_path"],
                        file_size=row["file_size"],
                        file_type=row["file_type"],
                        content_hash=row["content_hash"],
                        processing_status=row["processing_status"],
                        processing_started_at=row["processing_started_at"],
                        processing_completed_at=row["processing_completed_at"],
                        processing_errors=row["processing_errors"],
                        artifact_text_id=row["artifact_text_id"],
                        total_pages=row["total_pages"],
                        total_word_count=row["total_word_count"],
                        created_at=row["created_at"],
                        updated_at=row["updated_at"],
                    )
                    for row in rows
                ]
            # Return raw dictionaries for partial column selections
            try:
                return [dict(row) for row in rows]
            except Exception as e:
                logger.warning(
                    f"[DocumentsRepository] Failed to map rows to dict for columns {columns}: {e}"
                )
                return []

    async def update_processing_results(
        self, document_id: UUID, results: Dict[str, Any]
    ) -> bool:
        """
        Update document processing_results field.

        Args:
            document_id: Document ID
            results: Processing results dictionary

        Returns:
            True if update successful, False otherwise
        """
        async with get_user_connection(self.user_id) as conn:
            result = await conn.execute(
                """
                UPDATE documents 
                SET processing_results = $1::jsonb, updated_at = now()
                WHERE id = $2
                """,
                json.dumps(results) if results is not None else None,
                document_id,
            )
            return result.split()[-1] == "1"

    async def update_processing_status_and_results(
        self,
        document_id: UUID,
        status: str,
        results: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Update both processing_status and processing_results.

        Args:
            document_id: Document ID
            status: New processing status
            results: Optional processing results

        Returns:
            True if update successful, False otherwise
        """
        async with get_user_connection(self.user_id) as conn:
            if results is not None:
                result = await conn.execute(
                    """
                    UPDATE documents 
                    SET processing_status = $1, processing_results = $2::jsonb, updated_at = now()
                    WHERE id = $3
                    """,
                    status,
                    json.dumps(results) if results is not None else None,
                    document_id,
                )
            else:
                result = await conn.execute(
                    """
                    UPDATE documents 
                    SET processing_status = $1, updated_at = now()
                    WHERE id = $2
                    """,
                    status,
                    document_id,
                )
            return result.split()[-1] == "1"
