"""
Service interfaces for dependency injection and circular import resolution.
"""

from typing import Protocol, Dict, Any, List, Optional, runtime_checkable
from fastapi import UploadFile


@runtime_checkable
class IDocumentProcessor(Protocol):
    """Interface for document processing services."""

    async def initialize(self) -> None:
        """Initialize the document processor."""
        ...

    async def upload_file(
        self,
        file: UploadFile,
        user_id: str,
        contract_type: Optional[str] = None,
        australian_state: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Upload and process a document file."""
        ...

    async def extract_text(
        self,
        storage_path: str,
        file_type: str,
        contract_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Extract text from a document."""
        ...

    async def get_file_content(self, storage_path: str) -> bytes:
        """Get raw file content from storage."""
        ...


@runtime_checkable
class ISemanticAnalyzer(Protocol):
    """Interface for semantic analysis services."""

    async def initialize(self) -> None:
        """Initialize the semantic analyzer."""
        ...

    async def analyze_diagram_semantic_content(
        self,
        image_content: bytes,
        diagram_context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Analyze semantic content of diagrams."""
        ...

    async def extract_contract_entities(
        self,
        text_content: str,
        contract_context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Extract entities from contract text."""
        ...


@runtime_checkable
class IContractAnalyzer(Protocol):
    """Interface for contract analysis services."""

    async def initialize(self) -> None:
        """Initialize the contract analyzer."""
        ...

    async def analyze_contract(
        self,
        contract_id: str,
        analysis_options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Analyze a contract for compliance and risks."""
        ...

    async def get_analysis_status(self, contract_id: str) -> Dict[str, Any]:
        """Get analysis status for a contract."""
        ...


@runtime_checkable
class IAIClient(Protocol):
    """Interface for AI service clients."""

    async def initialize(self) -> None:
        """Initialize the AI client."""
        ...

    async def analyze_text(self, text: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze text using AI."""
        ...

    async def analyze_image(
        self, image: bytes, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze image using AI."""
        ...


@runtime_checkable
class IDatabaseClient(Protocol):
    """Interface for database operations."""

    async def initialize(self) -> None:
        """Initialize the database client."""
        ...

    async def create(self, table: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new record."""
        ...

    async def read(
        self,
        table: str,
        filters: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None,
        count_only: bool = False,
    ) -> List[Dict[str, Any]]:
        """Read records with filters. If count_only is True, returns a dict with count."""
        ...

    async def update(
        self, table: str, record_id: str, data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update a record."""
        ...

    async def delete(self, table: str, record_id: str) -> bool:
        """Delete a record."""
        ...


class ServiceContainer:
    """Service container for dependency injection."""

    def __init__(self):
        self._services: Dict[type, Any] = {}
        self._factories: Dict[type, callable] = {}

    def register_instance(self, interface: type, instance: Any) -> None:
        """Register a service instance."""
        self._services[interface] = instance

    def register_factory(self, interface: type, factory: callable) -> None:
        """Register a service factory function."""
        self._factories[interface] = factory

    def get(self, interface: type) -> Any:
        """Get a service instance."""
        if interface in self._services:
            return self._services[interface]

        if interface in self._factories:
            instance = self._factories[interface]()
            self._services[interface] = instance
            return instance

        raise ValueError(f"Service not registered: {interface}")

    def clear(self) -> None:
        """Clear all registered services."""
        self._services.clear()
        self._factories.clear()


# Global service container instance
service_container = ServiceContainer()
