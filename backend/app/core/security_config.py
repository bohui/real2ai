"""Security configuration for Real2.AI platform.

This module centralizes security settings and provides configuration
management for file security, authentication, and other security features.
"""

from typing import Dict, List, Set, Optional
from pydantic import BaseSettings, Field
import logging

logger = logging.getLogger(__name__)


class SecurityConfig(BaseSettings):
    """Security configuration settings."""
    
    # File Security Settings
    enable_file_content_validation: bool = True
    enable_mime_type_validation: bool = True
    enable_magic_bytes_validation: bool = True
    enable_malware_scanning: bool = True
    enable_filename_sanitization: bool = True
    
    # File Size Limits (in bytes)
    max_pdf_size: int = 50 * 1024 * 1024      # 50MB
    max_doc_size: int = 25 * 1024 * 1024      # 25MB
    max_image_size: int = 10 * 1024 * 1024    # 10MB
    max_general_file_size: int = 50 * 1024 * 1024  # 50MB
    
    # Allowed file types
    allowed_extensions: List[str] = [
        "pdf", "doc", "docx", "jpg", "jpeg", "png", 
        "webp", "gif", "bmp", "tiff", "tif"
    ]
    
    # Security logging
    enable_security_logging: bool = True
    log_all_uploads: bool = True
    log_security_events: bool = True
    log_suspicious_activity: bool = True
    
    # Rate limiting for uploads
    enable_upload_rate_limiting: bool = True
    max_uploads_per_minute: int = 10
    max_uploads_per_hour: int = 100
    
    # Quarantine settings
    enable_file_quarantine: bool = False
    quarantine_suspicious_files: bool = False
    quarantine_retention_days: int = 30
    
    # Content validation
    scan_depth_bytes: int = 10 * 1024  # First 10KB of file
    enable_deep_content_scan: bool = True
    
    # Security headers and CORS
    enable_security_headers: bool = True
    enable_cors_validation: bool = True
    allowed_origins: List[str] = ["http://localhost:3000", "https://real2ai.com"]
    
    class Config:
        env_prefix = "SECURITY_"
        case_sensitive = False


class FileSecurityPolicy:
    """File security policy implementation."""
    
    def __init__(self, config: SecurityConfig):
        self.config = config
        
    def get_max_file_size(self, file_extension: str) -> int:
        """Get maximum file size for a given extension."""
        size_map = {
            'pdf': self.config.max_pdf_size,
            'doc': self.config.max_doc_size,
            'docx': self.config.max_doc_size,
            'jpg': self.config.max_image_size,
            'jpeg': self.config.max_image_size,
            'png': self.config.max_image_size,
            'webp': self.config.max_image_size,
            'gif': self.config.max_image_size,
            'bmp': self.config.max_image_size,
            'tiff': self.config.max_image_size,
            'tif': self.config.max_image_size,
        }
        return size_map.get(file_extension, self.config.max_general_file_size)
    
    def is_extension_allowed(self, extension: str) -> bool:
        """Check if file extension is allowed."""
        return extension.lower() in [ext.lower() for ext in self.config.allowed_extensions]
    
    def should_scan_content(self, file_size: int) -> bool:
        """Determine if file content should be scanned."""
        if not self.config.enable_malware_scanning:
            return False
        # Skip scanning for very large files to avoid performance issues
        return file_size <= self.config.scan_depth_bytes or self.config.enable_deep_content_scan
    
    def get_security_settings(self) -> Dict:
        """Get current security settings as dictionary."""
        return {
            "content_validation": self.config.enable_file_content_validation,
            "mime_validation": self.config.enable_mime_type_validation,
            "magic_bytes_validation": self.config.enable_magic_bytes_validation,
            "malware_scanning": self.config.enable_malware_scanning,
            "filename_sanitization": self.config.enable_filename_sanitization,
            "max_file_sizes": {
                "pdf": self.config.max_pdf_size,
                "doc": self.config.max_doc_size,
                "image": self.config.max_image_size,
                "general": self.config.max_general_file_size
            },
            "allowed_extensions": self.config.allowed_extensions,
            "rate_limiting": {
                "enabled": self.config.enable_upload_rate_limiting,
                "per_minute": self.config.max_uploads_per_minute,
                "per_hour": self.config.max_uploads_per_hour
            }
        }


class SecurityEventLogger:
    """Security event logging utility."""
    
    def __init__(self, config: SecurityConfig):
        self.config = config
        self.logger = logging.getLogger("security")
        
    def log_upload_attempt(
        self, 
        user_id: str, 
        filename: str, 
        file_size: int, 
        client_ip: Optional[str] = None
    ):
        """Log file upload attempt."""
        if not self.config.log_all_uploads:
            return
            
        self.logger.info(
            "File upload attempt",
            extra={
                "user_id": user_id,
                "filename": filename,
                "file_size": file_size,
                "client_ip": client_ip,
                "event_type": "upload_attempt"
            }
        )
    
    def log_security_violation(
        self, 
        user_id: str, 
        filename: str, 
        violation_type: str, 
        details: str,
        client_ip: Optional[str] = None
    ):
        """Log security violation."""
        if not self.config.log_security_events:
            return
            
        self.logger.warning(
            f"Security violation: {violation_type}",
            extra={
                "user_id": user_id,
                "filename": filename,
                "violation_type": violation_type,
                "details": details,
                "client_ip": client_ip,
                "event_type": "security_violation"
            }
        )
    
    def log_suspicious_activity(
        self, 
        user_id: str, 
        activity_type: str, 
        details: Dict,
        client_ip: Optional[str] = None
    ):
        """Log suspicious activity."""
        if not self.config.log_suspicious_activity:
            return
            
        self.logger.warning(
            f"Suspicious activity: {activity_type}",
            extra={
                "user_id": user_id,
                "activity_type": activity_type,
                "details": details,
                "client_ip": client_ip,
                "event_type": "suspicious_activity"
            }
        )
    
    def log_malware_detection(
        self, 
        user_id: str, 
        filename: str, 
        threat_type: str,
        file_hash: str,
        client_ip: Optional[str] = None
    ):
        """Log malware detection."""
        self.logger.critical(
            f"Malware detected: {threat_type}",
            extra={
                "user_id": user_id,
                "filename": filename,
                "threat_type": threat_type,
                "file_hash": file_hash,
                "client_ip": client_ip,
                "event_type": "malware_detection"
            }
        )


# Global instances
security_config = SecurityConfig()
file_security_policy = FileSecurityPolicy(security_config)
security_event_logger = SecurityEventLogger(security_config)