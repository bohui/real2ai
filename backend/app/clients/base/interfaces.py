"""
Service-specific interfaces for external clients.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union
from datetime import datetime


class DatabaseOperations(ABC):
    """Abstract interface for database operations."""
    
    @abstractmethod
    async def create(self, table: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new record in the specified table."""
        pass
    
    @abstractmethod
    async def read(self, table: str, filters: Dict[str, Any], limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Read records from the specified table with optional filters."""
        pass
    
    @abstractmethod
    async def update(self, table: str, record_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update a record in the specified table."""
        pass
    
    @abstractmethod
    async def delete(self, table: str, record_id: str) -> bool:
        """Delete a record from the specified table."""
        pass
    
    @abstractmethod
    async def upsert(self, table: str, data: Dict[str, Any], conflict_columns: List[str] = None) -> Dict[str, Any]:
        """Insert or update a record based on conflict resolution."""
        pass
    
    @abstractmethod
    async def execute_rpc(self, function_name: str, params: Dict[str, Any] = None) -> Any:
        """Execute a remote procedure call or stored function."""
        pass


class AuthOperations(ABC):
    """Abstract interface for authentication operations."""
    
    @abstractmethod
    async def authenticate_user(self, token: str) -> Dict[str, Any]:
        """Authenticate a user using their token."""
        pass
    
    @abstractmethod
    async def get_user(self, user_id: str) -> Dict[str, Any]:
        """Get user information by ID."""
        pass
    
    @abstractmethod
    async def create_user(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new user account."""
        pass
    
    @abstractmethod
    async def update_user(self, user_id: str, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update user information."""
        pass
    
    @abstractmethod
    async def delete_user(self, user_id: str) -> bool:
        """Delete a user account."""
        pass
    
    @abstractmethod
    async def reset_password(self, email: str) -> bool:
        """Initiate password reset for a user."""
        pass


class AIOperations(ABC):
    """Abstract interface for AI service operations."""
    
    @abstractmethod
    async def generate_content(self, prompt: str, **kwargs) -> str:
        """Generate content based on a prompt."""
        pass
    
    @abstractmethod
    async def analyze_document(self, content: bytes, content_type: str, **kwargs) -> Dict[str, Any]:
        """Analyze a document and extract information."""
        pass
    
    @abstractmethod
    async def extract_text(self, content: bytes, content_type: str, **kwargs) -> Dict[str, Any]:
        """Extract text from a document using OCR."""
        pass
    
    @abstractmethod
    async def classify_content(self, content: str, categories: List[str], **kwargs) -> Dict[str, Any]:
        """Classify content into predefined categories."""
        pass


class CacheOperations(ABC):
    """Abstract interface for caching operations."""
    
    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        """Get a value from cache."""
        pass
    
    @abstractmethod
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set a value in cache with optional TTL."""
        pass
    
    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete a key from cache."""
        pass
    
    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check if a key exists in cache."""
        pass
    
    @abstractmethod
    async def flush(self) -> bool:
        """Clear all cache entries."""
        pass
    
    @abstractmethod
    async def get_ttl(self, key: str) -> Optional[int]:
        """Get time-to-live for a key."""
        pass


class StorageOperations(ABC):
    """Abstract interface for file storage operations."""
    
    @abstractmethod
    async def upload_file(self, bucket: str, file_path: str, content: bytes, content_type: str = None) -> Dict[str, Any]:
        """Upload a file to storage."""
        pass
    
    @abstractmethod
    async def download_file(self, bucket: str, file_path: str) -> bytes:
        """Download a file from storage."""
        pass
    
    @abstractmethod
    async def delete_file(self, bucket: str, file_path: str) -> bool:
        """Delete a file from storage."""
        pass
    
    @abstractmethod
    async def list_files(self, bucket: str, prefix: str = None, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """List files in a bucket with optional prefix filter."""
        pass
    
    @abstractmethod
    async def generate_signed_url(self, bucket: str, file_path: str, expires_in: int = 3600) -> str:
        """Generate a signed URL for file access."""
        pass
    
    @abstractmethod
    async def get_file_info(self, bucket: str, file_path: str) -> Dict[str, Any]:
        """Get file metadata and information."""
        pass


class PaymentOperations(ABC):
    """Abstract interface for payment processing operations."""
    
    @abstractmethod
    async def create_customer(self, customer_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new customer in the payment system."""
        pass
    
    @abstractmethod
    async def create_payment_intent(self, amount: int, currency: str, customer_id: str = None, **kwargs) -> Dict[str, Any]:
        """Create a payment intent."""
        pass
    
    @abstractmethod
    async def confirm_payment(self, payment_intent_id: str, payment_method: str = None) -> Dict[str, Any]:
        """Confirm a payment intent."""
        pass
    
    @abstractmethod
    async def refund_payment(self, payment_intent_id: str, amount: Optional[int] = None) -> Dict[str, Any]:
        """Refund a payment."""
        pass
    
    @abstractmethod
    async def get_payment_status(self, payment_intent_id: str) -> Dict[str, Any]:
        """Get the status of a payment."""
        pass


class NotificationOperations(ABC):
    """Abstract interface for notification operations."""
    
    @abstractmethod
    async def send_email(self, to: Union[str, List[str]], subject: str, body: str, html_body: str = None, **kwargs) -> Dict[str, Any]:
        """Send an email notification."""
        pass
    
    @abstractmethod
    async def send_sms(self, to: str, message: str, **kwargs) -> Dict[str, Any]:
        """Send an SMS notification."""
        pass
    
    @abstractmethod
    async def send_push_notification(self, device_token: str, title: str, body: str, **kwargs) -> Dict[str, Any]:
        """Send a push notification."""
        pass
    
    @abstractmethod
    async def create_notification_template(self, template_id: str, template_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a notification template."""
        pass
    
    @abstractmethod
    async def send_templated_notification(self, template_id: str, recipients: List[str], template_variables: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """Send notification using a template."""
        pass