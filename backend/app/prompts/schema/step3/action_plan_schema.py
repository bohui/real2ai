from typing import List, Dict, Any, Optional, Union
from pydantic import BaseModel, Field
from enum import Enum


class ActionOwner(str, Enum):
    BUYER = "buyer"
    SOLICITOR = "solicitor"
    LENDER = "lender"
    AGENT = "agent"


class DueDate(BaseModel):
    date: Optional[str] = Field(None, description="ISO date")
    relative_deadline: Optional[str] = Field(None, description="e.g., '3 days before settlement'")


class ActionItem(BaseModel):
    title: str = Field(..., description="Action title")
    description: str = Field(..., description="Detailed action description")
    owner: ActionOwner = Field(..., description="Responsible party")
    due_by: DueDate = Field(..., description="Due date for the action")
    dependencies: List[str] = Field(default_factory=list, description="Action dependencies (titles)")
    blocking_risks: List[str] = Field(default_factory=list, description="Associated blocking risks (titles or ids)")


class ActionPlanResult(BaseModel):
    actions: List[ActionItem] = Field(default_factory=list, description="Sequenced action plan")
    timeline_summary: Optional[str] = Field(None, description="High-level timeline overview")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadata, provenance, etc.")
