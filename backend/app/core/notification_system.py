"""
User Notification System for Real2.AI
Provides user-friendly notifications, progress updates, and feedback mechanisms
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, UTC
from enum import Enum
from dataclasses import dataclass, asdict

from app.services.communication.websocket_service import WebSocketManager
from app.services.communication.redis_pubsub import redis_pubsub_service

logger = logging.getLogger(__name__)


class NotificationType(str, Enum):
    """Types of notifications"""
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    PROGRESS = "progress"
    VALIDATION = "validation"


class NotificationPriority(str, Enum):
    """Notification priority levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class NotificationAction:
    """Action that user can take from notification"""
    label: str
    action_type: str  # "button", "link", "retry", "dismiss"
    action_data: Optional[Dict[str, Any]] = None
    primary: bool = False


@dataclass  
class UserNotification:
    """Enhanced user notification with rich context"""
    id: str
    type: NotificationType
    priority: NotificationPriority
    title: str
    message: str
    timestamp: datetime
    user_id: Optional[str] = None
    contract_id: Optional[str] = None
    session_id: Optional[str] = None
    
    # Enhanced features
    actions: List[NotificationAction] = None
    auto_dismiss_seconds: Optional[int] = None
    show_progress: bool = False
    progress_percent: Optional[int] = None
    
    # Help and guidance
    help_text: Optional[str] = None
    help_link: Optional[str] = None
    
    # Metadata
    metadata: Optional[Dict[str, Any]] = None
    acknowledged: bool = False
    
    def __post_init__(self):
        if self.actions is None:
            self.actions = []
        if self.timestamp is None:
            self.timestamp = datetime.now(UTC)

    def to_dict(self) -> Dict[str, Any]:
        """Convert notification to dictionary for JSON serialization"""
        result = asdict(self)
        result['timestamp'] = self.timestamp.isoformat()
        return result


class NotificationSystem:
    """Centralized notification system for user feedback"""
    
    def __init__(self, websocket_manager: Optional[WebSocketManager] = None):
        self.websocket_manager = websocket_manager
        self.active_notifications: Dict[str, Dict[str, UserNotification]] = {}  # user_id -> notifications
        self.notification_templates = self._initialize_templates()
    
    def _initialize_templates(self) -> Dict[str, Dict[str, Any]]:
        """Initialize notification templates for common scenarios"""
        return {
            # Authentication & Authorization
            "login_success": {
                "type": NotificationType.SUCCESS,
                "priority": NotificationPriority.LOW,
                "title": "Welcome back!",
                "message": "You've been successfully logged in.",
                "auto_dismiss_seconds": 3
            },
            "session_expired": {
                "type": NotificationType.WARNING,
                "priority": NotificationPriority.MEDIUM,
                "title": "Session Expired",
                "message": "Your session has expired. Please log in again to continue.",
                "actions": [
                    NotificationAction("Log In", "button", {"action": "login"}, primary=True)
                ]
            },
            "insufficient_credits": {
                "type": NotificationType.WARNING,
                "priority": NotificationPriority.HIGH,
                "title": "No Credits Remaining",
                "message": "You don't have enough credits to analyze this contract.",
                "actions": [
                    NotificationAction("Upgrade Plan", "link", {"url": "/pricing"}, primary=True),
                    NotificationAction("Learn More", "link", {"url": "/help/credits"})
                ],
                "help_text": "Credits reset monthly on paid plans, or upgrade for more analysis capacity."
            },
            
            # File Upload & Processing
            "file_upload_success": {
                "type": NotificationType.SUCCESS,
                "priority": NotificationPriority.LOW,
                "title": "File Uploaded",
                "message": "Your document has been uploaded successfully.",
                "auto_dismiss_seconds": 3
            },
            "file_too_large": {
                "type": NotificationType.ERROR,
                "priority": NotificationPriority.MEDIUM,
                "title": "File Too Large",
                "message": "The file you uploaded is too large. Please use a file smaller than 10MB.",
                "actions": [
                    NotificationAction("Try Again", "retry", primary=True),
                    NotificationAction("Compress File", "link", {"url": "/help/compress-pdf"})
                ],
                "help_text": "Large files take longer to process and may cause analysis issues."
            },
            "file_format_error": {
                "type": NotificationType.ERROR,
                "priority": NotificationPriority.MEDIUM,
                "title": "Unsupported File Format",
                "message": "This file format isn't supported. Please upload a PDF, DOC, or DOCX file.",
                "actions": [
                    NotificationAction("Try Different File", "button", {"action": "file_select"}, primary=True),
                    NotificationAction("Conversion Help", "link", {"url": "/help/file-formats"})
                ],
                "help_text": "We support PDF, Word (.docx), and legacy Word (.doc) files."
            },
            
            # Contract Analysis
            "analysis_started": { 
                "type": NotificationType.INFO,
                "priority": NotificationPriority.MEDIUM,
                "title": "Analysis Started",
                "message": "Our AI is analyzing your contract. This usually takes 2-5 minutes.",
                "show_progress": True,
                "progress_percent": 10,
                "actions": [
                    NotificationAction("View Progress", "link", {"url": "/analysis/{contract_id}"})
                ]
            },
            "analysis_progress": {
                "type": NotificationType.PROGRESS,
                "priority": NotificationPriority.LOW,
                "title": "Analysis in Progress",
                "message": "Analyzing contract terms and compliance...",
                "show_progress": True,
                "auto_dismiss_seconds": 5
            },
            "analysis_completed": {
                "type": NotificationType.SUCCESS,
                "priority": NotificationPriority.HIGH,
                "title": "Analysis Complete",
                "message": "Your contract analysis is ready! Click to view the results.",
                "actions": [
                    NotificationAction("View Results", "link", {"url": "/analysis/{contract_id}"}, primary=True),
                    NotificationAction("Download Report", "button", {"action": "download_pdf"})
                ]
            },
            "analysis_failed": {
                "type": NotificationType.ERROR,
                "priority": NotificationPriority.HIGH,
                "title": "Analysis Failed",
                "message": "We couldn't analyze your contract. Please try again or contact support.",
                "actions": [
                    NotificationAction("Try Again", "retry", primary=True),
                    NotificationAction("Contact Support", "link", {"url": "/support"}),
                    NotificationAction("Upload Different File", "button", {"action": "file_select"})
                ],
                "help_text": "This usually happens with corrupted files or non-standard contracts."
            },
            "low_confidence_warning": {
                "type": NotificationType.WARNING,
                "priority": NotificationPriority.MEDIUM,
                "title": "Analysis Incomplete",
                "message": "We had trouble reading parts of your contract. Please review the results carefully.",
                "actions": [
                    NotificationAction("View Results", "link", {"url": "/analysis/{contract_id}"}, primary=True),
                    NotificationAction("Upload Better Copy", "button", {"action": "reupload"}),
                    NotificationAction("Get Help", "link", {"url": "/help/low-confidence"})
                ],
                "help_text": "Try uploading a clearer scan or higher quality document for better results."
            },
            
            # System & Network
            "connection_lost": {
                "type": NotificationType.WARNING,
                "priority": NotificationPriority.HIGH,
                "title": "Connection Lost",
                "message": "Lost connection to the server. Trying to reconnect...",
                "actions": [
                    NotificationAction("Refresh Page", "button", {"action": "refresh"}, primary=True)
                ]
            },
            "connection_restored": {
                "type": NotificationType.SUCCESS,
                "priority": NotificationPriority.MEDIUM,
                "title": "Connection Restored",
                "message": "Connection to the server has been restored.",
                "auto_dismiss_seconds": 3
            },
            "system_maintenance": {
                "type": NotificationType.INFO,
                "priority": NotificationPriority.MEDIUM,
                "title": "Scheduled Maintenance",
                "message": "System maintenance is scheduled for tonight at 2 AM AEST (30 minutes).",
                "actions": [
                    NotificationAction("Learn More", "link", {"url": "/status"})
                ],
                "help_text": "Save your work and plan accordingly. Service will be restored automatically."
            },
            
            # Rate Limiting
            "rate_limit_warning": {
                "type": NotificationType.WARNING,
                "priority": NotificationPriority.MEDIUM,
                "title": "Slow Down",
                "message": "You're making requests too quickly. Please wait a moment before trying again.",
                "actions": [
                    NotificationAction("Try Again", "retry", primary=True)
                ],
                "auto_dismiss_seconds": 10
            },
            
            # Validation Errors
            "validation_error": {
                "type": NotificationType.ERROR,
                "priority": NotificationPriority.MEDIUM,
                "title": "Please Check Your Information",
                "message": "Some required information is missing or incorrect.",
                "actions": [
                    NotificationAction("Review Form", "button", {"action": "focus_form"}, primary=True)
                ]
            },
            
            # Success Messages
            "settings_saved": {
                "type": NotificationType.SUCCESS,
                "priority": NotificationPriority.LOW,
                "title": "Settings Saved",
                "message": "Your preferences have been updated successfully.",
                "auto_dismiss_seconds": 3
            },
            "report_downloaded": {
                "type": NotificationType.SUCCESS,
                "priority": NotificationPriority.LOW,
                "title": "Report Downloaded",
                "message": "Your contract analysis report has been downloaded.",
                "auto_dismiss_seconds": 3
            }
        }
    
    async def send_notification(
        self,
        template_name: str,
        user_id: str,
        contract_id: Optional[str] = None,
        session_id: Optional[str] = None,
        custom_data: Optional[Dict[str, Any]] = None,
        **format_kwargs
    ) -> UserNotification:
        """Send notification using predefined template"""
        
        template = self.notification_templates.get(template_name)
        if not template:
            logger.error(f"Unknown notification template: {template_name}")
            template = {
                "type": NotificationType.INFO,
                "priority": NotificationPriority.MEDIUM,
                "title": "Notification",
                "message": "An event occurred."
            }
        
        # Create notification ID
        notification_id = f"{template_name}_{user_id}_{datetime.now(UTC).timestamp()}"
        
        # Apply custom data overrides
        if custom_data:
            template = {**template, **custom_data}
        
        # Format message template with provided data
        message = template["message"]
        title = template["title"]
        help_text = template.get("help_text")
        
        try:
            if format_kwargs:
                message = message.format(**format_kwargs)
                title = title.format(**format_kwargs)
                if help_text:
                    help_text = help_text.format(**format_kwargs)
        except KeyError as e:
            logger.warning(f"Template formatting failed for {template_name}: {e}")
        
        # Create notification object
        notification = UserNotification(
            id=notification_id,
            type=NotificationType(template["type"]),
            priority=NotificationPriority(template["priority"]),
            title=title,
            message=message,
            user_id=user_id,
            contract_id=contract_id,
            session_id=session_id,
            actions=[NotificationAction(**action) if isinstance(action, dict) else action 
                    for action in template.get("actions", [])],
            auto_dismiss_seconds=template.get("auto_dismiss_seconds"),
            show_progress=template.get("show_progress", False),
            progress_percent=template.get("progress_percent"),
            help_text=help_text,
            help_link=template.get("help_link"),
            metadata=format_kwargs
        )
        
        # Store notification
        if user_id not in self.active_notifications:
            self.active_notifications[user_id] = {}
        self.active_notifications[user_id][notification_id] = notification
        
        # Send via WebSocket if available
        if self.websocket_manager and session_id:
            await self._send_websocket_notification(notification, session_id)
        
        # Send via Redis pub/sub for real-time updates
        await self._send_pubsub_notification(notification)
        
        logger.info(f"Sent notification {template_name} to user {user_id}")
        return notification
    
    async def send_custom_notification(
        self,
        user_id: str,
        notification_type: NotificationType,
        title: str,
        message: str,
        priority: NotificationPriority = NotificationPriority.MEDIUM,
        contract_id: Optional[str] = None,
        session_id: Optional[str] = None,
        actions: List[NotificationAction] = None,
        **kwargs
    ) -> UserNotification:
        """Send custom notification with full control"""
        
        notification_id = f"custom_{user_id}_{datetime.now(UTC).timestamp()}"
        
        notification = UserNotification(
            id=notification_id,
            type=notification_type,
            priority=priority,
            title=title,
            message=message,
            timestamp=datetime.now(UTC),
            user_id=user_id,
            contract_id=contract_id,
            session_id=session_id,
            actions=actions or [],
            **kwargs
        )
        
        # Store notification
        if user_id not in self.active_notifications:
            self.active_notifications[user_id] = {}
        self.active_notifications[user_id][notification_id] = notification
        
        # Send via available channels
        if self.websocket_manager and session_id:
            await self._send_websocket_notification(notification, session_id)
        
        await self._send_pubsub_notification(notification)
        
        return notification
    
    async def update_progress_notification(
        self,
        user_id: str,
        notification_id: str,
        progress_percent: int,
        message: Optional[str] = None,
        session_id: Optional[str] = None
    ):
        """Update progress for existing notification"""
        
        if user_id in self.active_notifications:
            notification = self.active_notifications[user_id].get(notification_id)
            if notification:
                notification.progress_percent = progress_percent
                if message:
                    notification.message = message
                notification.timestamp = datetime.now(UTC)
                
                # Send update
                if self.websocket_manager and session_id:
                    await self._send_websocket_notification(notification, session_id)
                
                await self._send_pubsub_notification(notification)
    
    async def dismiss_notification(self, user_id: str, notification_id: str):
        """Dismiss/acknowledge notification"""
        
        if user_id in self.active_notifications:
            notification = self.active_notifications[user_id].get(notification_id)
            if notification:
                notification.acknowledged = True
                # Remove from active notifications
                del self.active_notifications[user_id][notification_id]
                logger.info(f"Dismissed notification {notification_id} for user {user_id}")
    
    async def get_user_notifications(
        self, 
        user_id: str, 
        include_acknowledged: bool = False
    ) -> List[UserNotification]:
        """Get all notifications for a user"""
        
        user_notifications = self.active_notifications.get(user_id, {})
        
        if include_acknowledged:
            return list(user_notifications.values())
        else:
            return [n for n in user_notifications.values() if not n.acknowledged]
    
    async def clear_user_notifications(self, user_id: str):
        """Clear all notifications for a user"""
        
        if user_id in self.active_notifications:
            del self.active_notifications[user_id]
            logger.info(f"Cleared all notifications for user {user_id}")
    
    async def _send_websocket_notification(
        self, 
        notification: UserNotification, 
        session_id: str
    ):
        """Send notification via WebSocket"""
        
        try:
            message = {
                "event_type": "user_notification",
                "timestamp": notification.timestamp.isoformat(),
                "data": notification.to_dict()
            }
            
            await self.websocket_manager.send_message(session_id, message)
            
        except Exception as e:
            logger.error(f"Failed to send WebSocket notification: {e}")
    
    async def _send_pubsub_notification(self, notification: UserNotification):
        """Send notification via Redis pub/sub"""
        
        try:
            channel = f"user_notifications_{notification.user_id}"
            message = {
                "event_type": "user_notification",
                "timestamp": notification.timestamp.isoformat(),
                "data": notification.to_dict()
            }
            
            await redis_pubsub_service.publish_progress(notification.user_id, message)
            
        except Exception as e:
            logger.error(f"Failed to send pub/sub notification: {e}")
    
    def get_notification_stats(self) -> Dict[str, Any]:
        """Get notification system statistics"""
        
        total_notifications = sum(len(notifications) for notifications in self.active_notifications.values())
        
        type_counts = {}
        priority_counts = {}
        
        for user_notifications in self.active_notifications.values():
            for notification in user_notifications.values():
                type_counts[notification.type.value] = type_counts.get(notification.type.value, 0) + 1
                priority_counts[notification.priority.value] = priority_counts.get(notification.priority.value, 0) + 1
        
        return {
            "total_active_notifications": total_notifications,
            "active_users": len(self.active_notifications),
            "notifications_by_type": type_counts,
            "notifications_by_priority": priority_counts
        }


# Global notification system instance  
notification_system = NotificationSystem()


# Convenience functions for common notification scenarios
async def notify_user_success(
    user_id: str, 
    message: str, 
    title: str = "Success",
    session_id: Optional[str] = None,
    **kwargs
):
    """Send success notification to user"""
    return await notification_system.send_custom_notification(
        user_id=user_id,
        notification_type=NotificationType.SUCCESS,
        title=title,
        message=message,
        priority=NotificationPriority.LOW,
        session_id=session_id,
        auto_dismiss_seconds=5,
        **kwargs
    )


async def notify_user_error(
    user_id: str,
    message: str,
    title: str = "Error",
    session_id: Optional[str] = None,
    actions: List[NotificationAction] = None,
    **kwargs
):
    """Send error notification to user"""
    return await notification_system.send_custom_notification(
        user_id=user_id,
        notification_type=NotificationType.ERROR,
        title=title,
        message=message,
        priority=NotificationPriority.HIGH,
        session_id=session_id,
        actions=actions or [NotificationAction("Try Again", "retry", primary=True)],
        **kwargs
    )


async def notify_user_progress(
    user_id: str,
    title: str,
    message: str,
    progress_percent: int,
    session_id: Optional[str] = None,
    contract_id: Optional[str] = None,
    **kwargs
):
    """Send progress notification to user"""
    return await notification_system.send_custom_notification(
        user_id=user_id,
        notification_type=NotificationType.PROGRESS,
        title=title,
        message=message,
        priority=NotificationPriority.MEDIUM,
        session_id=session_id,
        contract_id=contract_id,
        show_progress=True,
        progress_percent=progress_percent,
        **kwargs
    )