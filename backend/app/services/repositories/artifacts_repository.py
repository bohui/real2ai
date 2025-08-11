"""
Repository for shared document processing artifacts (FIXED VERSION)

This version properly uses context managers for connection management
instead of storing connections, preventing pool misuse.
"""

import asyncio
from typing import Dict, List, Optional, Tuple, Any
from uuid import UUID
import asyncpg
from dataclasses import dataclass
from datetime import datetime

from app.database.connection import get_service_role_connection
from app.utils.content_utils import get_artifact_key, validate_content_hmac, validate_params_fingerprint


@dataclass
class TextExtractionArtifact:
    """Text extraction artifact model"""
    id: UUID
    content_hmac: str
    algorithm_version: int
    params_fingerprint: str
    full_text_uri: str
    full_text_sha256: str
    total_pages: int
    total_words: int
    methods: Dict[str, Any]
    timings: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None


@dataclass
class PageArtifact:
    """Page artifact model"""
    id: UUID
    content_hmac: str
    algorithm_version: int
    params_fingerprint: str
    page_number: int
    page_text_uri: str
    page_text_sha256: str
    layout: Optional[Dict[str, Any]] = None
    metrics: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None


@dataclass  
class DiagramArtifact:
    """Diagram artifact model"""
    id: UUID
    content_hmac: str
    algorithm_version: int
    params_fingerprint: str
    page_number: int
    diagram_key: str
    diagram_meta: Dict[str, Any]
    created_at: Optional[datetime] = None


@dataclass
class ParagraphArtifact:
    """Paragraph artifact model"""
    id: UUID
    content_hmac: str
    algorithm_version: int
    params_fingerprint: str
    page_number: int
    paragraph_index: int
    paragraph_text_uri: str
    paragraph_text_sha256: str
    features: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None


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
    # TEXT EXTRACTION ARTIFACTS
    # ================================

    async def get_text_artifact(
        self, 
        content_hmac: str, 
        algorithm_version: int, 
        params_fingerprint: str
    ) -> Optional[TextExtractionArtifact]:
        """
        Get text extraction artifact by key.
        
        Args:
            content_hmac: Content HMAC
            algorithm_version: Algorithm version
            params_fingerprint: Parameters fingerprint
            
        Returns:
            TextExtractionArtifact if found, None otherwise
            
        Raises:
            ValueError: If parameters are invalid
        """
        if not validate_content_hmac(content_hmac):
            raise ValueError(f"Invalid content HMAC: {content_hmac}")
        if not validate_params_fingerprint(params_fingerprint):
            raise ValueError(f"Invalid params fingerprint: {params_fingerprint}")

        # Use context manager for proper connection management
        async with get_service_role_connection() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, content_hmac, algorithm_version, params_fingerprint,
                       full_text_uri, full_text_sha256, total_pages, total_words,
                       methods, timings, created_at
                FROM text_extraction_artifacts
                WHERE content_hmac = $1 AND algorithm_version = $2 AND params_fingerprint = $3
                """,
                content_hmac, algorithm_version, params_fingerprint
            )
            
            if row is None:
                return None
                
            return TextExtractionArtifact(
                id=row['id'],
                content_hmac=row['content_hmac'],
                algorithm_version=row['algorithm_version'],
                params_fingerprint=row['params_fingerprint'],
                full_text_uri=row['full_text_uri'],
                full_text_sha256=row['full_text_sha256'],
                total_pages=row['total_pages'],
                total_words=row['total_words'],
                methods=row['methods'],
                timings=row['timings'],
                created_at=row['created_at']
            )

    async def insert_text_artifact(
        self,
        content_hmac: str,
        algorithm_version: int,
        params_fingerprint: str,
        full_text_uri: str,
        full_text_sha256: str,
        total_pages: int,
        total_words: int,
        methods: Dict[str, Any],
        timings: Optional[Dict[str, Any]] = None
    ) -> TextExtractionArtifact:
        """
        Insert text extraction artifact with ON CONFLICT DO NOTHING, then SELECT.
        
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
            TextExtractionArtifact (existing or newly inserted)
            
        Raises:
            ValueError: If parameters are invalid
        """
        if not validate_content_hmac(content_hmac):
            raise ValueError(f"Invalid content HMAC: {content_hmac}")
        if not validate_params_fingerprint(params_fingerprint):
            raise ValueError(f"Invalid params fingerprint: {params_fingerprint}")

        # Use context manager for proper connection management
        async with get_service_role_connection() as conn:
            # Use advisory lock to prevent stampedes on first compute
            lock_key = hash(content_hmac) & 0x7FFFFFFF  # Positive 32-bit integer
            
            async with conn.transaction():
                await conn.execute("SELECT pg_advisory_xact_lock($1)", lock_key)
                
                # Try insert first
                await conn.execute(
                    """
                    INSERT INTO text_extraction_artifacts (
                        content_hmac, algorithm_version, params_fingerprint,
                        full_text_uri, full_text_sha256, total_pages, total_words,
                        methods, timings
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                    ON CONFLICT (content_hmac, algorithm_version, params_fingerprint) DO NOTHING
                    """,
                    content_hmac, algorithm_version, params_fingerprint,
                    full_text_uri, full_text_sha256, total_pages, total_words,
                    methods, timings
                )
                
                # Then SELECT to get the artifact (whether newly inserted or existing)
                row = await conn.fetchrow(
                    """
                    SELECT id, content_hmac, algorithm_version, params_fingerprint,
                           full_text_uri, full_text_sha256, total_pages, total_words,
                           methods, timings, created_at
                    FROM text_extraction_artifacts
                    WHERE content_hmac = $1 AND algorithm_version = $2 AND params_fingerprint = $3
                    """,
                    content_hmac, algorithm_version, params_fingerprint
                )
                
                if row is None:
                    raise RuntimeError("Failed to insert or retrieve text extraction artifact")
                    
                return TextExtractionArtifact(
                    id=row['id'],
                    content_hmac=row['content_hmac'],
                    algorithm_version=row['algorithm_version'],
                    params_fingerprint=row['params_fingerprint'],
                    full_text_uri=row['full_text_uri'],
                    full_text_sha256=row['full_text_sha256'],
                    total_pages=row['total_pages'],
                    total_words=row['total_words'],
                    methods=row['methods'],
                    timings=row['timings'],
                    created_at=row['created_at']
                )

    # ================================
    # PAGE ARTIFACTS
    # ================================

    async def get_page_artifacts(
        self,
        content_hmac: str,
        algorithm_version: int,
        params_fingerprint: str
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
                content_hmac, algorithm_version, params_fingerprint
            )
            
            return [
                PageArtifact(
                    id=row['id'],
                    content_hmac=row['content_hmac'],
                    algorithm_version=row['algorithm_version'],
                    params_fingerprint=row['params_fingerprint'],
                    page_number=row['page_number'],
                    page_text_uri=row['page_text_uri'],
                    page_text_sha256=row['page_text_sha256'],
                    layout=row['layout'],
                    metrics=row['metrics'],
                    created_at=row['created_at']
                )
                for row in rows
            ]

    async def insert_page_artifact(
        self,
        content_hmac: str,
        algorithm_version: int,
        params_fingerprint: str,
        page_number: int,
        page_text_uri: str,
        page_text_sha256: str,
        layout: Optional[Dict[str, Any]] = None,
        metrics: Optional[Dict[str, Any]] = None
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

        async with get_service_role_connection() as conn:
            # Try insert first
            await conn.execute(
                """
                INSERT INTO artifact_pages (
                    content_hmac, algorithm_version, params_fingerprint,
                    page_number, page_text_uri, page_text_sha256, layout, metrics
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                ON CONFLICT (content_hmac, algorithm_version, params_fingerprint, page_number) DO NOTHING
                """,
                content_hmac, algorithm_version, params_fingerprint,
                page_number, page_text_uri, page_text_sha256, layout, metrics
            )
            
            # Then SELECT to get the artifact
            row = await conn.fetchrow(
                """
                SELECT id, content_hmac, algorithm_version, params_fingerprint,
                       page_number, page_text_uri, page_text_sha256,
                       layout, metrics, created_at
                FROM artifact_pages
                WHERE content_hmac = $1 AND algorithm_version = $2 AND params_fingerprint = $3
                      AND page_number = $4
                """,
                content_hmac, algorithm_version, params_fingerprint, page_number
            )
            
            if row is None:
                raise RuntimeError(f"Failed to insert or retrieve page artifact for page {page_number}")
                
            return PageArtifact(
                id=row['id'],
                content_hmac=row['content_hmac'],
                algorithm_version=row['algorithm_version'],
                params_fingerprint=row['params_fingerprint'],
                page_number=row['page_number'],
                page_text_uri=row['page_text_uri'],
                page_text_sha256=row['page_text_sha256'],
                layout=row['layout'],
                metrics=row['metrics'],
                created_at=row['created_at']
            )

    # ================================
    # DIAGRAM ARTIFACTS
    # ================================

    async def get_diagram_artifacts(
        self,
        content_hmac: str,
        algorithm_version: int,
        params_fingerprint: str
    ) -> List[DiagramArtifact]:
        """Get all diagram artifacts for a document."""
        if not validate_content_hmac(content_hmac):
            raise ValueError(f"Invalid content HMAC: {content_hmac}")
        if not validate_params_fingerprint(params_fingerprint):
            raise ValueError(f"Invalid params fingerprint: {params_fingerprint}")

        async with get_service_role_connection() as conn:
            rows = await conn.fetch(
                """
                SELECT id, content_hmac, algorithm_version, params_fingerprint,
                       page_number, diagram_key, diagram_meta, created_at
                FROM artifact_diagrams
                WHERE content_hmac = $1 AND algorithm_version = $2 AND params_fingerprint = $3
                ORDER BY page_number, diagram_key
                """,
                content_hmac, algorithm_version, params_fingerprint
            )
            
            return [
                DiagramArtifact(
                    id=row['id'],
                    content_hmac=row['content_hmac'],
                    algorithm_version=row['algorithm_version'],
                    params_fingerprint=row['params_fingerprint'],
                    page_number=row['page_number'],
                    diagram_key=row['diagram_key'],
                    diagram_meta=row['diagram_meta'],
                    created_at=row['created_at']
                )
                for row in rows
            ]

    async def insert_diagram_artifact(
        self,
        content_hmac: str,
        algorithm_version: int,
        params_fingerprint: str,
        page_number: int,
        diagram_key: str,
        diagram_meta: Dict[str, Any]
    ) -> DiagramArtifact:
        """Insert diagram artifact with ON CONFLICT DO NOTHING."""
        if not validate_content_hmac(content_hmac):
            raise ValueError(f"Invalid content HMAC: {content_hmac}")
        if not validate_params_fingerprint(params_fingerprint):
            raise ValueError(f"Invalid params fingerprint: {params_fingerprint}")

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
                content_hmac, algorithm_version, params_fingerprint,
                page_number, diagram_key, diagram_meta
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
                content_hmac, algorithm_version, params_fingerprint, page_number, diagram_key
            )
            
            if row is None:
                raise RuntimeError(f"Failed to insert or retrieve diagram artifact {diagram_key}")
                
            return DiagramArtifact(
                id=row['id'],
                content_hmac=row['content_hmac'],
                algorithm_version=row['algorithm_version'],
                params_fingerprint=row['params_fingerprint'],
                page_number=row['page_number'],
                diagram_key=row['diagram_key'],
                diagram_meta=row['diagram_meta'],
                created_at=row['created_at']
            )

    # ================================
    # PARAGRAPH ARTIFACTS (OPTIONAL)
    # ================================

    async def get_paragraph_artifacts(
        self,
        content_hmac: str,
        algorithm_version: int,
        params_fingerprint: str
    ) -> List[ParagraphArtifact]:
        """Get all paragraph artifacts for a document."""
        if not validate_content_hmac(content_hmac):
            raise ValueError(f"Invalid content HMAC: {content_hmac}")
        if not validate_params_fingerprint(params_fingerprint):
            raise ValueError(f"Invalid params fingerprint: {params_fingerprint}")

        async with get_service_role_connection() as conn:
            rows = await conn.fetch(
                """
                SELECT id, content_hmac, algorithm_version, params_fingerprint,
                       page_number, paragraph_index, paragraph_text_uri, paragraph_text_sha256,
                       features, created_at
                FROM artifact_paragraphs
                WHERE content_hmac = $1 AND algorithm_version = $2 AND params_fingerprint = $3
                ORDER BY page_number, paragraph_index
                """,
                content_hmac, algorithm_version, params_fingerprint
            )
            
            return [
                ParagraphArtifact(
                    id=row['id'],
                    content_hmac=row['content_hmac'],
                    algorithm_version=row['algorithm_version'],
                    params_fingerprint=row['params_fingerprint'],
                    page_number=row['page_number'],
                    paragraph_index=row['paragraph_index'],
                    paragraph_text_uri=row['paragraph_text_uri'],
                    paragraph_text_sha256=row['paragraph_text_sha256'],
                    features=row['features'],
                    created_at=row['created_at']
                )
                for row in rows
            ]

    async def insert_paragraph_artifact(
        self,
        content_hmac: str,
        algorithm_version: int,
        params_fingerprint: str,
        page_number: int,
        paragraph_index: int,
        paragraph_text_uri: str,
        paragraph_text_sha256: str,
        features: Optional[Dict[str, Any]] = None
    ) -> ParagraphArtifact:
        """Insert paragraph artifact with ON CONFLICT DO NOTHING."""
        if not validate_content_hmac(content_hmac):
            raise ValueError(f"Invalid content HMAC: {content_hmac}")
        if not validate_params_fingerprint(params_fingerprint):
            raise ValueError(f"Invalid params fingerprint: {params_fingerprint}")

        async with get_service_role_connection() as conn:
            # Use advisory lock to prevent stampedes on first compute
            lock_key = hash(f"{content_hmac}:{params_fingerprint}") & 0x7FFFFFFF  # Positive 32-bit integer
            
            async with conn.transaction():
                await conn.execute("SELECT pg_advisory_xact_lock($1)", lock_key)
                
                # Try insert first
                await conn.execute(
                    """
                    INSERT INTO artifact_paragraphs (
                        content_hmac, algorithm_version, params_fingerprint,
                        page_number, paragraph_index, paragraph_text_uri, 
                        paragraph_text_sha256, features
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                    ON CONFLICT (content_hmac, algorithm_version, params_fingerprint, page_number, paragraph_index) 
                    DO NOTHING
                    """,
                    content_hmac, algorithm_version, params_fingerprint,
                    page_number, paragraph_index, paragraph_text_uri,
                    paragraph_text_sha256, features
                )
                
                # Then SELECT to get the artifact (whether newly inserted or existing)
                row = await conn.fetchrow(
                    """
                    SELECT id, content_hmac, algorithm_version, params_fingerprint,
                           page_number, paragraph_index, paragraph_text_uri, paragraph_text_sha256,
                           features, created_at
                    FROM artifact_paragraphs
                    WHERE content_hmac = $1 AND algorithm_version = $2 AND params_fingerprint = $3
                          AND page_number = $4 AND paragraph_index = $5
                    """,
                    content_hmac, algorithm_version, params_fingerprint, page_number, paragraph_index
                )
            
            if row is None:
                raise RuntimeError(f"Failed to insert or retrieve paragraph artifact {paragraph_index}")
                
            return ParagraphArtifact(
                id=row['id'],
                content_hmac=row['content_hmac'],
                algorithm_version=row['algorithm_version'],
                params_fingerprint=row['params_fingerprint'],
                page_number=row['page_number'],
                paragraph_index=row['paragraph_index'],
                paragraph_text_uri=row['paragraph_text_uri'],
                paragraph_text_sha256=row['paragraph_text_sha256'],
                features=row['features'],
                created_at=row['created_at']
            )