"""
Repository for user-scoped document processing data (FIXED VERSION)

This version properly uses context managers for connection management
instead of storing connections, preventing pool misuse.
"""

from typing import Dict, List, Optional, Any
from uuid import UUID
from dataclasses import dataclass
from datetime import datetime
import json

from app.database.connection import get_user_connection


@dataclass
class DocumentPage:
    """Document page model"""

    document_id: UUID
    page_number: int
    artifact_page_id: UUID
    annotations: Optional[Dict[str, Any]] = None
    flags: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class DocumentDiagram:
    """Document diagram model"""

    document_id: UUID
    page_number: int
    diagram_key: str
    artifact_diagram_id: UUID
    annotations: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class UserDocsRepository:
    """
    Repository for user-scoped document processing data.

    FIXED: Now uses proper context managers for all database operations
    instead of storing connections. This ensures connections are properly
    released back to the pool instead of being closed.
    """

    def __init__(self, user_id: UUID):
        """
        Initialize user docs repository.

        Args:
            user_id: User ID for scoped operations

        Note: No stored connection! Each method uses its own context manager
        for proper connection pool management.
        """
        self.user_id = user_id
        # No stored connection! Each method uses its own context manager

    # ================================
    # DOCUMENT METADATA UPDATES
    # ================================

    async def update_document_artifact_reference(
        self,
        document_id: UUID,
        artifact_text_id: UUID,
        total_pages: Optional[int] = None,
        total_word_count: Optional[int] = None,
    ) -> bool:
        """
        Update document with artifact reference and aggregated metrics.

        Args:
            document_id: Document ID
            artifact_text_id: Text extraction artifact ID
            total_pages: Total page count
            total_word_count: Total word count

        Returns:
            True if update successful, False otherwise
        """
        # Use context manager for proper connection management
        async with get_user_connection(self.user_id) as conn:
            result = await conn.execute(
                """
                UPDATE documents 
                SET artifact_text_id = $1,
                    total_pages = COALESCE($2, total_pages),
                    total_word_count = COALESCE($3, total_word_count)
                WHERE id = $4 AND user_id = $5
                """,
                artifact_text_id,
                total_pages,
                total_word_count,
                document_id,
                self.user_id,
            )

            return result.split()[-1] == "1"  # Check if exactly one row was updated

    async def update_document_processing_status(
        self,
        document_id: UUID,
        processing_status: str,
        processing_started_at: Optional[datetime] = None,
        processing_completed_at: Optional[datetime] = None,
        processing_errors: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Update document processing status.

        Args:
            document_id: Document ID
            processing_status: Status (processing, basic_complete, failed, etc.)
            processing_started_at: When processing started
            processing_completed_at: When processing completed
            processing_errors: Any processing errors

        Returns:
            True if update successful, False otherwise
        """
        async with get_user_connection(self.user_id) as conn:
            # Build dynamic query based on provided parameters
            set_clauses = ["processing_status = $1"]
            params = [processing_status]
            param_count = 1

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

            if processing_errors is not None:
                param_count += 1
                set_clauses.append(f"processing_errors = ${param_count}")
                # Ensure proper JSON encoding
                params.append(json.dumps(processing_errors))

            # Add WHERE clause parameters
            param_count += 1
            params.append(document_id)
            param_count += 1
            params.append(self.user_id)

            query = f"""
                UPDATE documents 
                SET {', '.join(set_clauses)}
                WHERE id = ${param_count - 1} AND user_id = ${param_count}
            """

            result = await conn.execute(query, *params)
            return result.split()[-1] == "1"

    # ================================
    # DOCUMENT PAGES
    # ================================

    async def upsert_document_page(
        self,
        document_id: UUID,
        page_number: int,
        artifact_page_id: UUID,
        annotations: Optional[Dict[str, Any]] = None,
        flags: Optional[Dict[str, Any]] = None,
    ) -> DocumentPage:
        """
        Upsert document page reference with artifact ID.

        Args:
            document_id: Document ID
            page_number: Page number (1-based)
            artifact_page_id: Reference to artifact page
            annotations: User-specific annotations
            flags: User-specific flags

        Returns:
            DocumentPage (existing or newly created)
        """
        async with get_user_connection(self.user_id) as conn:
            # Use ON CONFLICT to handle upserts - don't overwrite existing annotations
            row = await conn.fetchrow(
                """
                INSERT INTO user_document_pages (
                    document_id, page_number, artifact_page_id, annotations, flags
                ) VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT (document_id, page_number) DO UPDATE SET
                    artifact_page_id = EXCLUDED.artifact_page_id,
                    annotations = COALESCE(user_document_pages.annotations, EXCLUDED.annotations),
                    flags = COALESCE(user_document_pages.flags, EXCLUDED.flags),
                    updated_at = now()
                RETURNING document_id, page_number, artifact_page_id, 
                          annotations, flags, created_at, updated_at
                """,
                document_id,
                page_number,
                artifact_page_id,
                json.dumps(annotations) if annotations is not None else None,
                json.dumps(flags) if flags is not None else None,
            )

            return DocumentPage(
                document_id=row["document_id"],
                page_number=row["page_number"],
                artifact_page_id=row["artifact_page_id"],
                annotations=row["annotations"],
                flags=row["flags"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )

    async def get_document_pages(self, document_id: UUID) -> List[DocumentPage]:
        """Get all pages for a document."""
        async with get_user_connection(self.user_id) as conn:
            rows = await conn.fetch(
                """
                SELECT document_id, page_number, artifact_page_id,
                       annotations, flags, created_at, updated_at
                FROM user_document_pages
                WHERE document_id = $1
                ORDER BY page_number
                """,
                document_id,
            )

            return [
                DocumentPage(
                    document_id=row["document_id"],
                    page_number=row["page_number"],
                    artifact_page_id=row["artifact_page_id"],
                    annotations=row["annotations"],
                    flags=row["flags"],
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                )
                for row in rows
            ]

    # ================================
    # DOCUMENT DIAGRAMS
    # ================================

    async def upsert_document_diagram(
        self,
        document_id: UUID,
        page_number: int,
        diagram_key: str,
        artifact_diagram_id: UUID,
        annotations: Optional[Dict[str, Any]] = None,
    ) -> DocumentDiagram:
        """
        Upsert document diagram reference with artifact ID.

        Args:
            document_id: Document ID
            page_number: Page number
            diagram_key: Diagram identifier
            artifact_diagram_id: Reference to artifact diagram
            annotations: User-specific annotations

        Returns:
            DocumentDiagram (existing or newly created)
        """
        async with get_user_connection(self.user_id) as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO user_document_diagrams (
                    document_id, page_number, diagram_key, artifact_diagram_id, annotations
                ) VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT (document_id, page_number, diagram_key) DO UPDATE SET
                    artifact_diagram_id = EXCLUDED.artifact_diagram_id,
                    annotations = COALESCE(user_document_diagrams.annotations, EXCLUDED.annotations),
                    updated_at = now()
                RETURNING document_id, page_number, diagram_key, artifact_diagram_id,
                          annotations, created_at, updated_at
                """,
                document_id,
                page_number,
                diagram_key,
                artifact_diagram_id,
                json.dumps(annotations) if annotations is not None else None,
            )

            return DocumentDiagram(
                document_id=row["document_id"],
                page_number=row["page_number"],
                diagram_key=row["diagram_key"],
                artifact_diagram_id=row["artifact_diagram_id"],
                annotations=row["annotations"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )

    async def get_document_diagrams(self, document_id: UUID) -> List[DocumentDiagram]:
        """Get all diagrams for a document."""
        async with get_user_connection(self.user_id) as conn:
            rows = await conn.fetch(
                """
                SELECT document_id, page_number, diagram_key, artifact_diagram_id,
                       annotations, created_at, updated_at
                FROM user_document_diagrams
                WHERE document_id = $1
                ORDER BY page_number, diagram_key
                """,
                document_id,
            )

            return [
                DocumentDiagram(
                    document_id=row["document_id"],
                    page_number=row["page_number"],
                    diagram_key=row["diagram_key"],
                    artifact_diagram_id=row["artifact_diagram_id"],
                    annotations=row["annotations"],
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                )
                for row in rows
            ]

    # ================================
    # BATCH OPERATIONS
    # ================================

    async def batch_upsert_document_pages(
        self, document_id: UUID, page_data: List[Dict[str, Any]]
    ) -> List[DocumentPage]:
        """
        Batch upsert multiple document pages.

        Args:
            document_id: Document ID
            page_data: List of page data dictionaries with keys:
                      page_number, artifact_page_id, annotations (optional), flags (optional)

        Returns:
            List of DocumentPage objects
        """
        if not page_data:
            return []

        results = []
        for page in page_data:
            result = await self.upsert_document_page(
                document_id=document_id,
                page_number=page["page_number"],
                artifact_page_id=page["artifact_page_id"],
                annotations=page.get("annotations"),
                flags=page.get("flags"),
            )
            results.append(result)

        return results

    async def batch_upsert_document_diagrams(
        self, document_id: UUID, diagram_data: List[Dict[str, Any]]
    ) -> List[DocumentDiagram]:
        """
        Batch upsert multiple document diagrams.

        Args:
            document_id: Document ID
            diagram_data: List of diagram data dictionaries with keys:
                         page_number, diagram_key, artifact_diagram_id, annotations (optional)

        Returns:
            List of DocumentDiagram objects
        """
        if not diagram_data:
            return []

        results = []
        for diagram in diagram_data:
            result = await self.upsert_document_diagram(
                document_id=document_id,
                page_number=diagram["page_number"],
                diagram_key=diagram["diagram_key"],
                artifact_diagram_id=diagram["artifact_diagram_id"],
                annotations=diagram.get("annotations"),
            )
            results.append(result)

        return results
