"""User and subscription enums."""

from enum import Enum


class UserType(str, Enum):
    """User types in the system"""
    BUYER = "buyer"
    INVESTOR = "investor"
    AGENT = "agent"


class SubscriptionStatus(str, Enum):
    """Subscription status levels"""
    FREE = "free"
    BASIC = "basic"
    PREMIUM = "premium"
    ENTERPRISE = "enterprise"
