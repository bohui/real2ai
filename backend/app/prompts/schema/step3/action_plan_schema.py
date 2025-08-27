from typing import List, Dict, Any, Optional, Union
from pydantic import BaseModel, Field, field_validator, model_validator
from enum import Enum
from datetime import datetime, date


class ActionOwner(str, Enum):
    BUYER = "buyer"
    SOLICITOR = "solicitor"
    LENDER = "lender"
    AGENT = "agent"
    VENDOR = "vendor"
    INSPECTOR = "inspector"


class ActionPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class DueDate(BaseModel):
    date: Optional[str] = Field(None, description="ISO date (YYYY-MM-DD)")
    relative_deadline: Optional[str] = Field(
        None, description="e.g., '3 days before settlement'"
    )

    @field_validator("date")
    @classmethod
    def validate_date_format(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            try:
                datetime.strptime(v, "%Y-%m-%d")
            except ValueError:
                raise ValueError("Date must be in YYYY-MM-DD format")
        return v

    @model_validator(mode="after")
    def validate_due_date(self):
        date_val = self.date
        relative_val = self.relative_deadline

        if not date_val and not relative_val:
            raise ValueError("Either date or relative_deadline must be provided")
        if date_val and relative_val:
            raise ValueError("Provide either date or relative_deadline, not both")

        return self


class ActionItem(BaseModel):
    title: str = Field(..., min_length=5, max_length=100, description="Action title")
    description: str = Field(
        ..., min_length=20, max_length=800, description="Detailed action description"
    )
    owner: ActionOwner = Field(..., description="Responsible party")
    priority: ActionPriority = Field(
        ActionPriority.MEDIUM, description="Action priority level"
    )
    due_by: DueDate = Field(..., description="Due date for the action")
    dependencies: List[str] = Field(
        default_factory=list, max_items=5, description="Action dependencies (titles)"
    )
    blocking_risks: List[str] = Field(
        default_factory=list,
        max_items=5,
        description="Associated blocking risks (titles or ids)",
    )
    estimated_duration_days: Optional[int] = Field(
        None, ge=1, le=180, description="Estimated days to complete"
    )

    @field_validator("dependencies", "blocking_risks", mode="after")
    @classmethod
    def validate_references(cls, v: List[str]) -> List[str]:
        return [ref.strip() for ref in v if ref and ref.strip()]


class ActionPlanResult(BaseModel):
    actions: List[ActionItem] = Field(
        ..., min_items=1, max_items=20, description="Sequenced action plan"
    )
    timeline_summary: str = Field(
        ..., min_length=20, max_length=500, description="High-level timeline overview"
    )
    critical_path: List[str] = Field(
        default_factory=list, description="Critical actions that could delay settlement"
    )
    total_estimated_days: Optional[int] = Field(
        None, ge=1, description="Total estimated timeline in days"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Metadata, provenance, etc."
    )

    @field_validator("actions", mode="after")
    @classmethod
    def validate_action_sequence(cls, v: List["ActionItem"]) -> List["ActionItem"]:
        if not v:
            raise ValueError("Must provide at least one action")

        # Check for duplicate titles
        titles = [action.title for action in v]
        if len(titles) != len(set(titles)):
            raise ValueError("Action titles must be unique")

        # Validate dependencies exist
        for action in v:
            for dep in action.dependencies:
                if dep not in titles:
                    raise ValueError(
                        f"Dependency '{dep}' not found in action titles for '{action.title}'"
                    )

        return v

    @field_validator("critical_path")
    @classmethod
    def validate_critical_path(cls, v: List[str], info):
        actions = info.data.get("actions", []) if info.data else []
        action_titles = {action.title for action in actions}

        for critical_action in v:
            if critical_action not in action_titles:
                raise ValueError(
                    f"Critical path action '{critical_action}' not found in actions"
                )

        return v
