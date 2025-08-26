from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class ActionItem(BaseModel):
    title: str = Field(..., description="Action title")
    description: str = Field(..., description="Detailed action description")
    owner: str = Field(..., description="Responsible party (buyer, solicitor, lender, agent)")
    due_by: Optional[str] = Field(None, description="ISO date or relative deadline")
    dependencies: List[str] = Field(default_factory=list, description="Action dependencies (titles)")
    blocking_risks: List[str] = Field(default_factory=list, description="Associated blocking risks (titles or ids)")


class ActionPlanResult(BaseModel):
    actions: List[ActionItem] = Field(default_factory=list, description="Sequenced action plan")
    timeline_summary: Optional[str] = Field(None, description="High-level timeline overview")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadata, provenance, etc.")