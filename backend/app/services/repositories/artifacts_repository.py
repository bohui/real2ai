"""
Repository for shared document processing artifacts (FIXED VERSION)

This version properly uses context managers for connection management
instead of storing connections, preventing pool misuse.
"""

import json
import logging
from typing import Dict, List, Optional, Any
from uuid import UUID

# Import moved inside methods to avoid circular imports
# from app.database.connection import get_service_role_connection
from app.utils.content_utils import (
    validate_content_hmac,
    validate_params_fingerprint,
)
from app.models.supabase_models import (
    FullTextArtifact,
    ArtifactPage as PageArtifact,
    ArtifactDiagram as DiagramArtifact,
)
import traceback
from app.utils.json_utils import safe_json_loads

logger = logging.getLogger(__name__)


class ArtifactsRepository:
    """
    Repository for managing shared document processing artifacts.

    FIXED: Now uses proper context managers for all database operations
    instead of storing connections. This ensures connections are properly
    released back to the pool instead of being closed.
    """

    def __init__(self):
        """
        Initialize artifacts repository.

        Note: No stored connection! Each method uses its own context manager
        for proper connection pool management.
        """
        # No stored connection! Each method uses its own context manager
        pass

    # ================================
    # FULL TEXT ARTIFACTS
    # ================================

    async def get_full_text_artifact(
        self, content_hmac: str, algorithm_version: int, params_fingerprint: str
    ) -> Optional[FullTextArtifact]:
        """
        Get full text artifact by key.

        Args:
            content_hmac: Content HMAC
            algorithm_version: Algorithm version
            params_fingerprint: Parameters fingerprint

        Returns:
            FullTextArtifact if found, None otherwise

        Raises:
            ValueError: If parameters are invalid
        """
        if not validate_content_hmac(content_hmac):
            raise ValueError(f"Invalid content HMAC: {content_hmac}")
        if not validate_params_fingerprint(params_fingerprint):
            raise ValueError(f"Invalid params fingerprint: {params_fingerprint}")

        # Use context manager for proper connection management
        from app.database.connection import get_service_role_connection

        async with get_service_role_connection() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, content_hmac, algorithm_version, params_fingerprint,
                       full_text_uri, full_text_sha256, total_pages, total_words,
                       methods, timings, created_at
                FROM artifacts_full_text
                WHERE content_hmac = $1 AND algorithm_version = $2 AND params_fingerprint = $3
                """,
                content_hmac,
                algorithm_version,
                params_fingerprint,
            )

            if row is None:
                return None

            # Ensure methods and timings are dictionaries, not JSON strings
            methods = row["methods"]
            if isinstance(methods, str):
                methods = json.loads(methods)

            timings = row["timings"]
            if isinstance(timings, str) and timings:
                timings = json.loads(timings)

            return FullTextArtifact(
                id=row["id"],
                content_hmac=row["content_hmac"],
                algorithm_version=row["algorithm_version"],
                params_fingerprint=row["params_fingerprint"],
                full_text_uri=row["full_text_uri"],
                full_text_sha256=row["full_text_sha256"],
                total_pages=row["total_pages"],
                total_words=row["total_words"],
                methods=methods,
                timings=timings,
                created_at=row["created_at"],
            )

    async def get_full_text_artifact_by_id(
        self, artifact_id: UUID
    ) -> Optional[FullTextArtifact]:
        """
        Get full text artifact by ID.

        Args:
            artifact_id: Artifact ID

        Returns:
            FullTextArtifact if found, None otherwise
        """
        from app.database.connection import get_service_role_connection

        async with get_service_role_connection() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, content_hmac, algorithm_version, params_fingerprint,
                       full_text_uri, full_text_sha256, total_pages, total_words,
                       methods, timings, created_at
                FROM artifacts_full_text
                WHERE id = $1
                """,
                artifact_id,
            )

            if row is None:
                return None

            # Ensure methods and timings are dictionaries, not JSON strings
            methods = row["methods"]
            if isinstance(methods, str):
                methods = json.loads(methods)

            timings = row["timings"]
            if isinstance(timings, str) and timings:
                timings = json.loads(timings)

            return FullTextArtifact(
                id=row["id"],
                content_hmac=row["content_hmac"],
                algorithm_version=row["algorithm_version"],
                params_fingerprint=row["params_fingerprint"],
                full_text_uri=row["full_text_uri"],
                full_text_sha256=row["full_text_sha256"],
                total_pages=row["total_pages"],
                total_words=row["total_words"],
                methods=methods,
                timings=timings,
                created_at=row["created_at"],
            )

    async def insert_full_text_artifact(
        self,
        content_hmac: str,
        algorithm_version: int,
        params_fingerprint: str,
        full_text_uri: str,
        full_text_sha256: str,
        total_pages: int,
        total_words: int,
        methods: Dict[str, Any],
        timings: Optional[Dict[str, Any]] = None,
    ) -> FullTextArtifact:
        """
        Insert full text artifact with ON CONFLICT DO NOTHING, then SELECT.

        Args:
            content_hmac: Content HMAC
            algorithm_version: Algorithm version
            params_fingerprint: Parameters fingerprint
            full_text_uri: URI to full text blob
            full_text_sha256: SHA256 of full text blob
            total_pages: Total number of pages
            total_words: Total word count
            methods: Processing methods used
            timings: Optional timing information

        Returns:
            FullTextArtifact (existing or newly inserted)

        Raises:
            ValueError: If parameters are invalid
        """
        if not validate_content_hmac(content_hmac):
            raise ValueError(f"Invalid content HMAC: {content_hmac}")
        if not validate_params_fingerprint(params_fingerprint):
            raise ValueError(f"Invalid params fingerprint: {params_fingerprint}")

        # Use context manager for proper connection management
        from app.database.connection import get_service_role_connection

        async with get_service_role_connection() as conn:
            # Use advisory lock to prevent stampedes on first compute
            lock_key = hash(content_hmac) & 0x7FFFFFFF  # Positive 32-bit integer

            async with conn.transaction():
                await conn.execute("SELECT pg_advisory_xact_lock($1)", lock_key)

                # Try insert first
                await conn.execute(
                    """
                    INSERT INTO artifacts_full_text (
                        content_hmac, algorithm_version, params_fingerprint,
                        full_text_uri, full_text_sha256, total_pages, total_words,
                        methods, timings
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, ($8)::jsonb, ($9)::jsonb)
                    ON CONFLICT (content_hmac, algorithm_version, params_fingerprint) DO NOTHING
                    """,
                    content_hmac,
                    algorithm_version,
                    params_fingerprint,
                    full_text_uri,
                    full_text_sha256,
                    total_pages,
                    total_words,
                    json.dumps(methods) if methods is not None else "{}",
                    json.dumps(timings) if timings is not None else None,
                )

                # Then SELECT to get the artifact (whether newly inserted or existing)
                row = await conn.fetchrow(
                    """
                    SELECT id, content_hmac, algorithm_version, params_fingerprint,
                           full_text_uri, full_text_sha256, total_pages, total_words,
                           methods, timings, created_at
                    FROM artifacts_full_text
                    WHERE content_hmac = $1 AND algorithm_version = $2 AND params_fingerprint = $3
                    """,
                    content_hmac,
                    algorithm_version,
                    params_fingerprint,
                )

                if row is None:
                    raise RuntimeError(
                        "Failed to insert or retrieve full text artifact"
                    )

                # Ensure methods and timings are dictionaries, not JSON strings
                methods = row["methods"]
                if isinstance(methods, str):
                    methods = json.loads(methods)

                timings = row["timings"]
                if isinstance(timings, str) and timings:
                    timings = json.loads(timings)

                return FullTextArtifact(
                    id=row["id"],
                    content_hmac=row["content_hmac"],
                    algorithm_version=row["algorithm_version"],
                    params_fingerprint=row["params_fingerprint"],
                    full_text_uri=row["full_text_uri"],
                    full_text_sha256=row["full_text_sha256"],
                    total_pages=row["total_pages"],
                    total_words=row["total_words"],
                    methods=methods,
                    timings=timings,
                    created_at=row["created_at"],
                )

    # ================================
    # PAGE ARTIFACTS
    # ================================

    async def get_page_artifacts(
        self, content_hmac: str, algorithm_version: int, params_fingerprint: str
    ) -> List[PageArtifact]:
        """
        Get all page artifacts for a document.

        Args:
            content_hmac: Content HMAC
            algorithm_version: Algorithm version
            params_fingerprint: Parameters fingerprint

        Returns:
            List of PageArtifacts ordered by page number
        """
        if not validate_content_hmac(content_hmac):
            raise ValueError(f"Invalid content HMAC: {content_hmac}")
        if not validate_params_fingerprint(params_fingerprint):
            raise ValueError(f"Invalid params fingerprint: {params_fingerprint}")

        from app.database.connection import get_service_role_connection

        async with get_service_role_connection() as conn:
            rows = await conn.fetch(
                """
                SELECT id, content_hmac, algorithm_version, params_fingerprint,
                       page_number, page_text_uri, page_text_sha256,
                       layout, metrics, created_at
                FROM artifact_pages
                WHERE content_hmac = $1 AND algorithm_version = $2 AND params_fingerprint = $3
                ORDER BY page_number
                """,
                content_hmac,
                algorithm_version,
                params_fingerprint,
            )

            artifacts = []
            for row in rows:
                try:
                    # Parse JSON fields safely
                    layout = safe_json_loads(row["layout"])
                    metrics = safe_json_loads(row["metrics"])

                    artifact = PageArtifact(
                        id=row["id"],
                        content_hmac=row["content_hmac"],
                        algorithm_version=row["algorithm_version"],
                        params_fingerprint=row["params_fingerprint"],
                        page_number=row["page_number"],
                        page_text_uri=row["page_text_uri"],
                        page_text_sha256=row["page_text_sha256"],
                        layout=layout,
                        metrics=metrics,
                        created_at=row["created_at"],
                    )
                    artifacts.append(artifact)
                except Exception as e:
                    logger.error(f"Error creating PageArtifact from row: {e}")
                    logger.error(f"Row data: {dict(row)}")
                    logger.error(f"layout type: {type(row['layout'])}")
                    logger.error(f"metrics type: {type(row['metrics'])}")
                    logger.error(f"Traceback: {traceback.format_exc()}")
                    # Skip this row and continue with others
                    continue

            return artifacts

    async def insert_page_artifact(
        self,
        content_hmac: str,
        algorithm_version: int,
        params_fingerprint: str,
        page_number: int,
        page_text_uri: str,
        page_text_sha256: str,
        layout: Optional[Dict[str, Any]] = None,
        metrics: Optional[Dict[str, Any]] = None,
    ) -> PageArtifact:
        """
        Insert page artifact with ON CONFLICT DO NOTHING.

        Args:
            content_hmac: Content HMAC
            algorithm_version: Algorithm version
            params_fingerprint: Parameters fingerprint
            page_number: Page number (1-based)
            page_text_uri: URI to page text blob
            page_text_sha256: SHA256 of page text blob
            layout: Optional layout information
            metrics: Optional page metrics

        Returns:
            PageArtifact (existing or newly inserted)
        """
        if not validate_content_hmac(content_hmac):
            raise ValueError(f"Invalid content HMAC: {content_hmac}")
        if not validate_params_fingerprint(params_fingerprint):
            raise ValueError(f"Invalid params fingerprint: {params_fingerprint}")

        from app.database.connection import get_service_role_connection

        async with get_service_role_connection() as conn:
            # Try insert first
            await conn.execute(
                """
                INSERT INTO artifact_pages (
                    content_hmac, algorithm_version, params_fingerprint,
                    page_number, page_text_uri, page_text_sha256, layout, metrics
                ) VALUES ($1, $2, $3, $4, $5, $6, ($7)::jsonb, ($8)::jsonb)
                ON CONFLICT (content_hmac, algorithm_version, params_fingerprint, page_number) DO NOTHING
                """,
                content_hmac,
                algorithm_version,
                params_fingerprint,
                page_number,
                page_text_uri,
                page_text_sha256,
                layout,
                metrics,
            )

            # Then SELECT to get the artifact
            row = await conn.fetchrow(
                """
                SELECT id, content_hmac, algorithm_version, params_fingerprint,
                       page_number, page_text_uri, page_text_sha256,
                       layout, metrics, COALESCE(content_type, 'text') as content_type, created_at
                FROM artifact_pages
                WHERE content_hmac = $1 AND algorithm_version = $2 AND params_fingerprint = $3
                      AND page_number = $4
                """,
                content_hmac,
                algorithm_version,
                params_fingerprint,
                page_number,
            )

            if row is None:
                raise RuntimeError(
                    f"Failed to insert or retrieve page artifact for page {page_number}"
                )

            # Deserialize JSON fields if they are strings
            layout = safe_json_loads(row["layout"])
            metrics = safe_json_loads(row["metrics"])

            return PageArtifact(
                id=row["id"],
                content_hmac=row["content_hmac"],
                algorithm_version=row["algorithm_version"],
                params_fingerprint=row["params_fingerprint"],
                page_number=row["page_number"],
                page_text_uri=row["page_text_uri"],
                page_text_sha256=row["page_text_sha256"],
                layout=layout,
                metrics=metrics,
                content_type=row["content_type"],
                created_at=row["created_at"],
            )

    # ================================
    # DIAGRAM ARTIFACTS
    # ================================

    async def get_diagram_artifacts(
        self, content_hmac: str, algorithm_version: int, params_fingerprint: str
    ) -> List[DiagramArtifact]:
        """Get all diagram artifacts for a document."""
        if not validate_content_hmac(content_hmac):
            raise ValueError(f"Invalid content HMAC: {content_hmac}")
        if not validate_params_fingerprint(params_fingerprint):
            raise ValueError(f"Invalid params fingerprint: {params_fingerprint}")

        from app.database.connection import get_service_role_connection

        async with get_service_role_connection() as conn:
            rows = await conn.fetch(
                """
                SELECT id, content_hmac, algorithm_version, params_fingerprint,
                       page_number, diagram_key, diagram_meta, created_at
                FROM artifact_diagrams
                WHERE content_hmac = $1 AND algorithm_version = $2 AND params_fingerprint = $3
                ORDER BY page_number, diagram_key
                """,
                content_hmac,
                algorithm_version,
                params_fingerprint,
            )

            artifacts = []
            for row in rows:
                try:
                    # Parse JSON fields safely
                    diagram_meta = safe_json_loads(row["diagram_meta"], {})

                    artifact = DiagramArtifact(
                        id=row["id"],
                        content_hmac=row["content_hmac"],
                        algorithm_version=row["algorithm_version"],
                        params_fingerprint=row["params_fingerprint"],
                        page_number=row["page_number"],
                        diagram_key=row["diagram_key"],
                        diagram_meta=diagram_meta,
                        created_at=row["created_at"],
                    )
                    artifacts.append(artifact)
                except Exception as e:
                    logger.error(f"Error creating DiagramArtifact from row: {e}")
                    logger.error(f"Row data: {dict(row)}")
                    logger.error(f"diagram_meta type: {type(row['diagram_meta'])}")
                    logger.error(f"diagram_meta value: {row['diagram_meta']}")
                    import traceback

                    logger.error(f"Traceback: {traceback.format_exc()}")
                    # Skip this row and continue with others
                    continue

            return artifacts

    async def insert_diagram_artifact(
        self,
        content_hmac: str,
        algorithm_version: int,
        params_fingerprint: str,
        page_number: int,
        diagram_key: str,
        diagram_meta: Dict[str, Any],
    ) -> DiagramArtifact:
        """Insert diagram artifact with ON CONFLICT DO NOTHING."""
        if not validate_content_hmac(content_hmac):
            raise ValueError(f"Invalid content HMAC: {content_hmac}")
        if not validate_params_fingerprint(params_fingerprint):
            raise ValueError(f"Invalid params fingerprint: {params_fingerprint}")

        from app.database.connection import get_service_role_connection

        async with get_service_role_connection() as conn:
            # Try insert first
            await conn.execute(
                """
                INSERT INTO artifact_diagrams (
                    content_hmac, algorithm_version, params_fingerprint,
                    page_number, diagram_key, diagram_meta
                ) VALUES ($1, $2, $3, $4, $5, $6)
                ON CONFLICT (content_hmac, algorithm_version, params_fingerprint, page_number, diagram_key) 
                DO NOTHING
                """,
                content_hmac,
                algorithm_version,
                params_fingerprint,
                page_number,
                diagram_key,
                diagram_meta,
            )

            # Then SELECT to get the artifact
            row = await conn.fetchrow(
                """
                SELECT id, content_hmac, algorithm_version, params_fingerprint,
                       page_number, diagram_key, diagram_meta, created_at
                FROM artifact_diagrams
                WHERE content_hmac = $1 AND algorithm_version = $2 AND params_fingerprint = $3
                      AND page_number = $4 AND diagram_key = $5
                """,
                content_hmac,
                algorithm_version,
                params_fingerprint,
                page_number,
                diagram_key,
            )

            if row is None:
                raise RuntimeError(
                    f"Failed to insert or retrieve diagram artifact {diagram_key}"
                )

            # Deserialize JSON fields if they are strings
            diagram_meta = safe_json_loads(row["diagram_meta"], {})

            return DiagramArtifact(
                id=row["id"],
                content_hmac=row["content_hmac"],
                algorithm_version=row["algorithm_version"],
                params_fingerprint=row["params_fingerprint"],
                page_number=row["page_number"],
                diagram_key=row["diagram_key"],
                diagram_meta=diagram_meta,
                artifact_type="diagram",  # Default for this method
                image_uri=None,
                image_sha256=None,
                image_metadata=None,
                created_at=row["created_at"],
            )

    # ================================
    # UNIFIED ARTIFACT ACCESS METHODS
    # ================================

    async def get_all_page_artifacts(
        self, content_hmac: str, algorithm_version: int, params_fingerprint: str
    ) -> List[PageArtifact]:
        """
        Get all page artifacts (text, markdown, JSON) for a document.

        This unified method retrieves all page-level content regardless of which
        workflow created them, enabling the main contract analysis workflow to
        access all processed results from a single method.

        Args:
            content_hmac: Content HMAC for identification
            algorithm_version: Algorithm version
            params_fingerprint: Parameters fingerprint

        Returns:
            List of unified PageArtifact objects
        """
        if not validate_content_hmac(content_hmac):
            raise ValueError(f"Invalid content HMAC: {content_hmac}")
        if not validate_params_fingerprint(params_fingerprint):
            raise ValueError(f"Invalid params fingerprint: {params_fingerprint}")

        from app.database.connection import get_service_role_connection

        async with get_service_role_connection() as conn:
            rows = await conn.fetch(
                """
                SELECT id, content_hmac, algorithm_version, params_fingerprint,
                       page_number, page_text_uri, page_text_sha256, layout, metrics,
                       COALESCE(content_type, 'text') as content_type, created_at
                FROM artifact_pages
                WHERE content_hmac = $1 AND algorithm_version = $2 AND params_fingerprint = $3
                ORDER BY page_number
                """,
                content_hmac,
                algorithm_version,
                params_fingerprint,
            )

            artifacts = []
            for row in rows:
                # Deserialize JSON fields if they are strings
                layout = safe_json_loads(row["layout"])
                metrics = safe_json_loads(row["metrics"])

                artifacts.append(
                    PageArtifact(
                        id=row["id"],
                        content_hmac=row["content_hmac"],
                        algorithm_version=row["algorithm_version"],
                        params_fingerprint=row["params_fingerprint"],
                        page_number=row["page_number"],
                        page_text_uri=row["page_text_uri"],
                        page_text_sha256=row["page_text_sha256"],
                        layout=layout,
                        metrics=metrics,
                        content_type=row["content_type"],
                        created_at=row["created_at"],
                    )
                )

            return artifacts

    async def get_all_visual_artifacts(
        self, content_hmac: str, algorithm_version: int, params_fingerprint: str
    ) -> List[DiagramArtifact]:
        """
        Get all visual artifacts (diagrams and images) for a document.

        This unified method retrieves all visual content regardless of which
        workflow created them, including traditional diagrams and JPG page images
        from external OCR processing.

        Args:
            content_hmac: Content HMAC for identification
            algorithm_version: Algorithm version
            params_fingerprint: Parameters fingerprint

        Returns:
            List of unified DiagramArtifact objects
        """
        if not validate_content_hmac(content_hmac):
            raise ValueError(f"Invalid content HMAC: {content_hmac}")
        if not validate_params_fingerprint(params_fingerprint):
            raise ValueError(f"Invalid params fingerprint: {params_fingerprint}")

        from app.database.connection import get_service_role_connection

        async with get_service_role_connection() as conn:
            rows = await conn.fetch(
                """
                SELECT id, content_hmac, algorithm_version, params_fingerprint,
                       page_number, diagram_key, diagram_meta,
                       COALESCE(artifact_type, 'diagram') as artifact_type,
                       image_uri, image_sha256, image_metadata, created_at
                FROM artifact_diagrams
                WHERE content_hmac = $1 AND algorithm_version = $2 AND params_fingerprint = $3
                ORDER BY page_number, diagram_key
                """,
                content_hmac,
                algorithm_version,
                params_fingerprint,
            )

            artifacts = []
            for row in rows:
                # Deserialize JSON fields if they are strings
                diagram_meta = safe_json_loads(row["diagram_meta"], {})

                image_metadata = safe_json_loads(row["image_metadata"])

                artifacts.append(
                    DiagramArtifact(
                        id=row["id"],
                        content_hmac=row["content_hmac"],
                        algorithm_version=row["algorithm_version"],
                        params_fingerprint=row["params_fingerprint"],
                        page_number=row["page_number"],
                        diagram_key=row["diagram_key"],
                        diagram_meta=diagram_meta,
                        artifact_type=row["artifact_type"],
                        image_uri=row["image_uri"],
                        image_sha256=row["image_sha256"],
                        image_metadata=image_metadata,
                        created_at=row["created_at"],
                    )
                )

            return artifacts

    async def get_document_processing_summary(
        self, content_hmac: str, algorithm_version: int, params_fingerprint: str
    ) -> Dict[str, Any]:
        """
        Get a comprehensive summary of all artifacts for a document.

        This method provides a single interface for the main contract analysis
        workflow to understand what processing results are available without
        needing to check multiple tables or understand workflow differences.

        Args:
            content_hmac: Content HMAC for identification
            algorithm_version: Algorithm version
            params_fingerprint: Parameters fingerprint

        Returns:
            Dictionary with artifact counts and metadata by type
        """
        if not validate_content_hmac(content_hmac):
            raise ValueError(f"Invalid content HMAC: {content_hmac}")
        if not validate_params_fingerprint(params_fingerprint):
            raise ValueError(f"Invalid params fingerprint: {params_fingerprint}")

        from app.database.connection import get_service_role_connection

        async with get_service_role_connection() as conn:
            # Get page artifact summary
            page_summary = await conn.fetchrow(
                """
                SELECT 
                    COUNT(*) as total_pages,
                    COUNT(*) FILTER (WHERE content_type = 'text') as text_pages,
                    COUNT(*) FILTER (WHERE content_type = 'markdown') as markdown_pages,
                    COUNT(*) FILTER (WHERE content_type = 'json_metadata') as json_pages
                FROM artifact_pages
                WHERE content_hmac = $1 AND algorithm_version = $2 AND params_fingerprint = $3
                """,
                content_hmac,
                algorithm_version,
                params_fingerprint,
            )

            # Get visual artifact summary
            visual_summary = await conn.fetchrow(
                """
                SELECT 
                    COUNT(*) as total_visuals,
                    COUNT(*) FILTER (WHERE artifact_type = 'diagram') as diagrams,
                    COUNT(*) FILTER (WHERE artifact_type = 'image_jpg') as jpg_images,
                    COUNT(*) FILTER (WHERE artifact_type = 'image_png') as png_images
                FROM artifact_diagrams
                WHERE content_hmac = $1 AND algorithm_version = $2 AND params_fingerprint = $3
                """,
                content_hmac,
                algorithm_version,
                params_fingerprint,
            )

            # Check if full text artifact exists
            full_text_artifact = await conn.fetchrow(
                """
                SELECT total_pages, total_words, methods
                FROM artifacts_full_text
                WHERE content_hmac = $1 AND algorithm_version = $2 AND params_fingerprint = $3
                """,
                content_hmac,
                algorithm_version,
                params_fingerprint,
            )

            return {
                "content_hmac": content_hmac,
                "algorithm_version": algorithm_version,
                "params_fingerprint": params_fingerprint,
                "full_text": {
                    "available": full_text_artifact is not None,
                    "total_pages": (
                        full_text_artifact["total_pages"] if full_text_artifact else 0
                    ),
                    "total_words": (
                        full_text_artifact["total_words"] if full_text_artifact else 0
                    ),
                    "methods": (
                        full_text_artifact["methods"] if full_text_artifact else []
                    ),
                },
                "page_artifacts": {
                    "total_pages": page_summary["total_pages"],
                    "by_type": {
                        "text": page_summary["text_pages"],
                        "markdown": page_summary["markdown_pages"],
                        "json_metadata": page_summary["json_pages"],
                    },
                },
                "visual_artifacts": {
                    "total_visuals": visual_summary["total_visuals"],
                    "by_type": {
                        "diagrams": visual_summary["diagrams"],
                        "jpg_images": visual_summary["jpg_images"],
                        "png_images": visual_summary["png_images"],
                    },
                },
                "processing_workflows": self._detect_workflows(
                    page_summary, visual_summary
                ),
            }

    def _detect_workflows(self, page_summary: Dict, visual_summary: Dict) -> List[str]:
        """
        Detect which workflows have processed this document based on artifact patterns.

        Args:
            page_summary: Summary of page artifacts
            visual_summary: Summary of visual artifacts

        Returns:
            List of workflow names that have processed this document
        """
        workflows = []

        # Main document processing workflow indicators
        if page_summary["text_pages"] > 0 or visual_summary["diagrams"] > 0:
            workflows.append("main_document_processing")

        # External OCR workflow indicators
        if (
            page_summary["markdown_pages"] > 0
            or page_summary["json_pages"] > 0
            or visual_summary["jpg_images"] > 0
        ):
            workflows.append("external_ocr_processing")

        return workflows

    # ================================
    # UNIFIED INSERTION METHODS
    # ================================

    async def insert_unified_page_artifact(
        self,
        content_hmac: str,
        algorithm_version: int,
        params_fingerprint: str,
        page_number: int,
        page_text_uri: str,
        page_text_sha256: str,
        content_type: str = "text",
        layout: Optional[Dict[str, Any]] = None,
        metrics: Optional[Dict[str, Any]] = None,
    ) -> PageArtifact:
        """
        Insert a page artifact with content type discrimination.

        This unified method supports both traditional text processing and external OCR
        workflows by using content_type to distinguish between different formats.

        Args:
            content_hmac: Content HMAC for identification
            algorithm_version: Algorithm version
            params_fingerprint: Parameters fingerprint
            page_number: Page number (1-based)
            page_text_uri: URI to text content storage
            page_text_sha256: SHA256 hash of text content
            content_type: Type of content ("text", "markdown", "json_metadata")
            layout: Optional layout information
            metrics: Optional metrics/stats information

        Returns:
            PageArtifact object
        """
        if not validate_content_hmac(content_hmac):
            raise ValueError(f"Invalid content HMAC: {content_hmac}")
        if not validate_params_fingerprint(params_fingerprint):
            raise ValueError(f"Invalid params fingerprint: {params_fingerprint}")
        if content_type not in ["text", "markdown", "json_metadata"]:
            raise ValueError(f"Invalid content_type: {content_type}")

        from app.database.connection import get_service_role_connection

        async with get_service_role_connection() as conn:
            lock_key = (
                hash(
                    f"{content_hmac}:{params_fingerprint}:{content_type}:{page_number}"
                )
                & 0x7FFFFFFF
            )

            async with conn.transaction():
                await conn.execute("SELECT pg_advisory_xact_lock($1)", lock_key)

                # Try insert first - serialize complex objects to JSON
                layout_json = json.dumps(layout) if layout is not None else None
                metrics_json = json.dumps(metrics) if metrics is not None else None

                await conn.execute(
                    """
                    INSERT INTO artifact_pages (
                        content_hmac, algorithm_version, params_fingerprint,
                        page_number, page_text_uri, page_text_sha256, 
                        layout, metrics, content_type
                    ) VALUES ($1, $2, $3, $4, $5, $6, ($7)::jsonb, ($8)::jsonb, $9)
                    ON CONFLICT (content_hmac, algorithm_version, params_fingerprint, page_number) 
                    DO UPDATE SET
                        layout = COALESCE(artifact_pages.layout, EXCLUDED.layout),
                        metrics = COALESCE(artifact_pages.metrics, EXCLUDED.metrics),
                        content_type = CASE 
                            WHEN artifact_pages.content_type = 'text' AND EXCLUDED.content_type != 'text' 
                            THEN EXCLUDED.content_type
                            ELSE artifact_pages.content_type
                        END
                    """,
                    content_hmac,
                    algorithm_version,
                    params_fingerprint,
                    page_number,
                    page_text_uri,
                    page_text_sha256,
                    layout_json,
                    metrics_json,
                    content_type,
                )

                # Then SELECT to get the artifact
                row = await conn.fetchrow(
                    """
                    SELECT id, content_hmac, algorithm_version, params_fingerprint,
                           page_number, page_text_uri, page_text_sha256, layout, metrics,
                           content_type, created_at
                    FROM artifact_pages
                    WHERE content_hmac = $1 AND algorithm_version = $2 AND params_fingerprint = $3
                          AND page_number = $4
                    """,
                    content_hmac,
                    algorithm_version,
                    params_fingerprint,
                    page_number,
                )

            if row is None:
                raise RuntimeError(
                    f"Failed to insert or retrieve unified page artifact {page_number}"
                )

            # Deserialize JSON fields if they are strings
            layout = safe_json_loads(row["layout"])
            metrics = safe_json_loads(row["metrics"])

            return PageArtifact(
                id=row["id"],
                content_hmac=row["content_hmac"],
                algorithm_version=row["algorithm_version"],
                params_fingerprint=row["params_fingerprint"],
                page_number=row["page_number"],
                page_text_uri=row["page_text_uri"],
                page_text_sha256=row["page_text_sha256"],
                layout=layout,
                metrics=metrics,
                content_type=row["content_type"],
                created_at=row["created_at"],
            )

    async def insert_unified_visual_artifact(
        self,
        content_hmac: str,
        algorithm_version: int,
        params_fingerprint: str,
        page_number: int,
        diagram_key: str,
        artifact_type: str = "diagram",
        diagram_meta: Optional[Dict[str, Any]] = None,
        image_uri: Optional[str] = None,
        image_sha256: Optional[str] = None,
        image_metadata: Optional[Dict[str, Any]] = None,
    ) -> DiagramArtifact:
        """
        Insert a visual artifact with type discrimination.

        This unified method supports both traditional diagram processing and external OCR
        image workflows by using artifact_type to distinguish between different formats.

        Args:
            content_hmac: Content HMAC for identification
            algorithm_version: Algorithm version
            params_fingerprint: Parameters fingerprint
            page_number: Page number (1-based)
            diagram_key: Unique key for the diagram/image
            artifact_type: Type of artifact ("diagram", "image_jpg", "image_png")
            diagram_meta: Metadata for diagrams
            image_uri: URI for image artifacts
            image_sha256: SHA256 hash for image artifacts
            image_metadata: Metadata for image artifacts

        Returns:
            DiagramArtifact object
        """
        if not validate_content_hmac(content_hmac):
            raise ValueError(f"Invalid content HMAC: {content_hmac}")
        if not validate_params_fingerprint(params_fingerprint):
            raise ValueError(f"Invalid params fingerprint: {params_fingerprint}")
        if artifact_type not in ["diagram", "image_jpg", "image_png"]:
            raise ValueError(f"Invalid artifact_type: {artifact_type}")

        from app.database.connection import get_service_role_connection

        async with get_service_role_connection() as conn:
            lock_key = (
                hash(
                    f"{content_hmac}:{params_fingerprint}:{artifact_type}:{page_number}:{diagram_key}"
                )
                & 0x7FFFFFFF
            )

            async with conn.transaction():
                await conn.execute("SELECT pg_advisory_xact_lock($1)", lock_key)

                # Serialize complex objects to JSON
                diagram_meta_json = (
                    json.dumps(diagram_meta) if diagram_meta is not None else "{}"
                )
                image_metadata_json = (
                    json.dumps(image_metadata) if image_metadata is not None else None
                )

                await conn.execute(
                    """
                    INSERT INTO artifact_diagrams (
                        content_hmac, algorithm_version, params_fingerprint,
                        page_number, diagram_key, diagram_meta, artifact_type,
                        image_uri, image_sha256, image_metadata
                    ) VALUES ($1, $2, $3, $4, $5, ($6)::jsonb, $7, $8, $9, ($10)::jsonb)
                    ON CONFLICT (content_hmac, algorithm_version, params_fingerprint, page_number, diagram_key) 
                    DO NOTHING
                    """,
                    content_hmac,
                    algorithm_version,
                    params_fingerprint,
                    page_number,
                    diagram_key,
                    diagram_meta_json,
                    artifact_type,
                    image_uri,
                    image_sha256,
                    image_metadata_json,
                )

                # Then SELECT to get the artifact
                row = await conn.fetchrow(
                    """
                    SELECT id, content_hmac, algorithm_version, params_fingerprint,
                           page_number, diagram_key, diagram_meta, artifact_type,
                           image_uri, image_sha256, image_metadata, created_at
                    FROM artifact_diagrams
                    WHERE content_hmac = $1 AND algorithm_version = $2 AND params_fingerprint = $3
                          AND page_number = $4 AND diagram_key = $5
                    """,
                    content_hmac,
                    algorithm_version,
                    params_fingerprint,
                    page_number,
                    diagram_key,
                )

            if row is None:
                raise RuntimeError(
                    f"Failed to insert or retrieve unified visual artifact {diagram_key}"
                )

            # Deserialize JSON fields if they are strings
            diagram_meta = safe_json_loads(row["diagram_meta"], {})
            image_metadata = safe_json_loads(row["image_metadata"])

            return DiagramArtifact(
                id=row["id"],
                content_hmac=row["content_hmac"],
                algorithm_version=row["algorithm_version"],
                params_fingerprint=row["params_fingerprint"],
                page_number=row["page_number"],
                diagram_key=row["diagram_key"],
                diagram_meta=diagram_meta,
                artifact_type=row["artifact_type"],
                image_uri=row["image_uri"],
                image_sha256=row["image_sha256"],
                image_metadata=image_metadata,
                created_at=row["created_at"],
            )

    # ================================
    # SIMPLIFIED HELPER METHODS
    # ================================

    async def get_page_artifacts_by_content_hmac(
        self,
        content_hmac: str,
        algorithm_version: int = 1,
        params_fingerprint: Optional[str] = None,
    ) -> List[PageArtifact]:
        """
        Get page artifacts by content_hmac with optional version and params.

        This is a helper method that uses default algorithm_version and can
        query across all params_fingerprints if not specified.

        Args:
            content_hmac: Content HMAC for identification
            algorithm_version: Algorithm version (default: 1)
            params_fingerprint: Optional params fingerprint, if None returns all

        Returns:
            List of PageArtifact objects
        """
        if not validate_content_hmac(content_hmac):
            raise ValueError(f"Invalid content HMAC: {content_hmac}")

        from app.database.connection import get_service_role_connection

        async with get_service_role_connection() as conn:
            if params_fingerprint:
                # Query with specific params_fingerprint
                if not validate_params_fingerprint(params_fingerprint):
                    raise ValueError(
                        f"Invalid params fingerprint: {params_fingerprint}"
                    )

                rows = await conn.fetch(
                    """
                    SELECT id, content_hmac, algorithm_version, params_fingerprint,
                           page_number, page_text_uri, page_text_sha256, layout, metrics,
                           COALESCE(content_type, 'text') as content_type, created_at
                    FROM artifact_pages
                    WHERE content_hmac = $1 AND algorithm_version = $2 AND params_fingerprint = $3
                    ORDER BY page_number
                    """,
                    content_hmac,
                    algorithm_version,
                    params_fingerprint,
                )
            else:
                # Query across all params_fingerprints, get the most recent
                rows = await conn.fetch(
                    """
                    SELECT DISTINCT ON (page_number) 
                           id, content_hmac, algorithm_version, params_fingerprint,
                           page_number, page_text_uri, page_text_sha256, layout, metrics,
                           COALESCE(content_type, 'text') as content_type, created_at
                    FROM artifact_pages
                    WHERE content_hmac = $1 AND algorithm_version = $2
                    ORDER BY page_number, created_at DESC
                    """,
                    content_hmac,
                    algorithm_version,
                )

            artifacts = []
            for row in rows:
                # Deserialize JSON fields if they are strings
                layout = safe_json_loads(row["layout"])
                metrics = safe_json_loads(row["metrics"])

                artifacts.append(
                    PageArtifact(
                        id=row["id"],
                        content_hmac=row["content_hmac"],
                        algorithm_version=row["algorithm_version"],
                        params_fingerprint=row["params_fingerprint"],
                        page_number=row["page_number"],
                        page_text_uri=row["page_text_uri"],
                        page_text_sha256=row["page_text_sha256"],
                        layout=layout,
                        metrics=metrics,
                        content_type=row["content_type"],
                        created_at=row["created_at"],
                    )
                )

            return artifacts

    async def get_diagram_artifacts_by_content_hmac(
        self,
        content_hmac: str,
        algorithm_version: int = 1,
        params_fingerprint: Optional[str] = None,
    ) -> List[DiagramArtifact]:
        """
        Get diagram/visual artifacts by content_hmac with optional version and params.

        This is a helper method that uses default algorithm_version and can
        query across all params_fingerprints if not specified.

        Args:
            content_hmac: Content HMAC for identification
            algorithm_version: Algorithm version (default: 1)
            params_fingerprint: Optional params fingerprint, if None returns all

        Returns:
            List of DiagramArtifact objects
        """
        if not validate_content_hmac(content_hmac):
            raise ValueError(f"Invalid content HMAC: {content_hmac}")

        from app.database.connection import get_service_role_connection

        async with get_service_role_connection() as conn:
            if params_fingerprint:
                # Query with specific params_fingerprint
                if not validate_params_fingerprint(params_fingerprint):
                    raise ValueError(
                        f"Invalid params fingerprint: {params_fingerprint}"
                    )

                rows = await conn.fetch(
                    """
                    SELECT id, content_hmac, algorithm_version, params_fingerprint,
                           page_number, diagram_key, diagram_meta,
                           COALESCE(artifact_type, 'diagram') as artifact_type,
                           image_uri, image_sha256, image_metadata, created_at
                    FROM artifact_diagrams
                    WHERE content_hmac = $1 AND algorithm_version = $2 AND params_fingerprint = $3
                    ORDER BY page_number, diagram_key
                    """,
                    content_hmac,
                    algorithm_version,
                    params_fingerprint,
                )
            else:
                # Query across all params_fingerprints, get the most recent
                rows = await conn.fetch(
                    """
                    SELECT DISTINCT ON (page_number, diagram_key) 
                           id, content_hmac, algorithm_version, params_fingerprint,
                           page_number, diagram_key, diagram_meta,
                           COALESCE(artifact_type, 'diagram') as artifact_type,
                           image_uri, image_sha256, image_metadata, created_at
                    FROM artifact_diagrams
                    WHERE content_hmac = $1 AND algorithm_version = $2
                    ORDER BY page_number, diagram_key, created_at DESC
                    """,
                    content_hmac,
                    algorithm_version,
                )

            artifacts = []
            for row in rows:
                try:
                    # Parse JSON fields safely
                    diagram_meta = safe_json_loads(row["diagram_meta"], {})
                    image_metadata = safe_json_loads(row["image_metadata"])

                    # Log the parsed values for debugging
                    logger.debug(
                        f"Parsed diagram_meta: {type(diagram_meta)} - {diagram_meta}"
                    )
                    logger.debug(
                        f"Parsed image_metadata: {type(image_metadata)} - {image_metadata}"
                    )

                    artifact = DiagramArtifact(
                        id=row["id"],
                        content_hmac=row["content_hmac"],
                        algorithm_version=row["algorithm_version"],
                        params_fingerprint=row["params_fingerprint"],
                        page_number=row["page_number"],
                        diagram_key=row["diagram_key"],
                        diagram_meta=diagram_meta,
                        artifact_type=row["artifact_type"],
                        image_uri=row["image_uri"],
                        image_sha256=row["image_sha256"],
                        image_metadata=image_metadata,
                        created_at=row["created_at"],
                    )
                    artifacts.append(artifact)
                except Exception as e:
                    logger.error(f"Error creating DiagramArtifact from row: {e}")
                    logger.error(f"Row data: {dict(row)}")
                    logger.error(f"diagram_meta type: {type(row['diagram_meta'])}")
                    logger.error(f"diagram_meta value: {row['diagram_meta']}")

                    logger.error(f"Traceback: {traceback.format_exc()}")
                    # Skip this row and continue with others
                    continue

            return artifacts
