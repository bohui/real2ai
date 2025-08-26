from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class SectionSummary(BaseModel):
    name: str = Field(..., description="Section name")
    summary: str = Field(..., description="Summary for the section")


class KeyRisk(BaseModel):
    title: str = Field(..., description="Risk title")
    description: str = Field(..., description="Brief risk description")


class ActionPlanOverviewItem(BaseModel):
    title: str = Field(..., description="Action title")
    owner: str = Field(..., description="Responsible party")


class BuyerReportResult(BaseModel):
    executive_summary: str = Field(..., description="Buyer-facing executive summary")
    section_summaries: List[SectionSummary] = Field(default_factory=list, description="Summaries per major section")
    key_risks: List[KeyRisk] = Field(default_factory=list, description="Key risks for the buyer")
    action_plan_overview: List[ActionPlanOverviewItem] = Field(default_factory=list, description="High-level action plan overview")
    evidence_refs: List[str] = Field(default_factory=list, description="Evidence references used in report")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadata and rendering hints")
