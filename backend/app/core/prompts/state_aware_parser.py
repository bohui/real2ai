"""
State-Aware Output Parser System

This module provides state-specific output parsers that can be selected based on
the Australian state context, eliminating the need for conditional logic in prompt templates.
"""

import logging
from typing import TypeVar, Dict, Any, Type, Optional, Union
from abc import ABC, abstractmethod

from pydantic import BaseModel

from .output_parser import create_parser, BaseOutputParser, ParsingResult

logger = logging.getLogger(__name__)

T = TypeVar('T', bound=BaseModel)


class StateAwareParser(BaseOutputParser[T]):
    """
    State-aware parser that selects appropriate output parser based on Australian state context.
    
    This eliminates the need for conditional logic in prompt templates and centralizes
    state-specific parsing logic in the execution stage.
    """
    
    def __init__(
        self,
        base_model: Type[T],
        state_specific_models: Optional[Dict[str, Type[T]]] = None,
        default_state: str = "NSW",
        **kwargs
    ):
        """
        Initialize state-aware parser.
        
        Args:
            base_model: Base Pydantic model for parsing
            state_specific_models: Dictionary mapping state codes to state-specific models
            default_state: Default state if none specified
            **kwargs: Additional arguments for base parser
        """
        super().__init__(base_model, **kwargs)
        self.state_specific_models = state_specific_models or {}
        self.default_state = default_state
        
        # Create parsers for each state
        self._state_parsers: Dict[str, BaseOutputParser[T]] = {}
        self._initialize_state_parsers()
    
    def _initialize_state_parsers(self):
        """Initialize parsers for each supported state."""
        # Base parser for default state
        self._state_parsers[self.default_state] = create_parser(
            self.pydantic_model, **self._get_parser_kwargs()
        )
        
        # State-specific parsers
        for state, model in self.state_specific_models.items():
            self._state_parsers[state] = create_parser(
                model, **self._get_parser_kwargs()
            )
    
    def _get_parser_kwargs(self) -> Dict[str, Any]:
        """Get parser configuration kwargs."""
        return {
            "output_format": self.output_format,
            "strict_mode": self.strict_mode,
            "retry_on_failure": self.retry_on_failure,
            "max_retries": getattr(self, 'max_retries', 2)
        }
    
    def get_parser_for_state(self, state: str) -> BaseOutputParser[T]:
        """
        Get the appropriate parser for a given state.
        
        Args:
            state: Australian state code (NSW, VIC, QLD, etc.)
            
        Returns:
            Output parser configured for the specified state
        """
        # Normalize state code
        state = state.upper() if state else self.default_state
        
        # Return state-specific parser if available, otherwise default
        return self._state_parsers.get(state, self._state_parsers[self.default_state])
    
    def parse(self, text: str, state: Optional[str] = None) -> ParsingResult:
        """
        Parse output using state-specific parser.
        
        Args:
            text: Raw AI output text
            state: Australian state context for parsing
            
        Returns:
            ParsingResult with parsed data or error information
        """
        parser = self.get_parser_for_state(state)
        return parser.parse(text)
    
    def parse_with_retry(self, text: str, state: Optional[str] = None) -> ParsingResult:
        """
        Parse output with retry using state-specific parser.
        
        Args:
            text: Raw AI output text
            state: Australian state context for parsing
            
        Returns:
            ParsingResult with parsed data or error information
        """
        parser = self.get_parser_for_state(state)
        return parser.parse_with_retry(text)
    
    def get_format_instructions(self, state: Optional[str] = None) -> str:
        """
        Get format instructions for a specific state.
        
        Args:
            state: Australian state context
            
        Returns:
            Format instructions string
        """
        parser = self.get_parser_for_state(state)
        return parser.get_format_instructions()


class StateAwareParserFactory:
    """
    Factory for creating state-aware parsers with predefined state configurations.
    """
    
    @staticmethod
    def create_contract_terms_parser() -> StateAwareParser:
        """Create state-aware parser for contract terms extraction."""
        from app.models.workflow_outputs import ContractTermsOutput
        
        # Define state-specific models with additional fields
        state_models = {
            "NSW": type("NSWContractTermsOutput", (ContractTermsOutput,), {
                "__annotations__": {
                    "section_149_certificate": Dict[str, Any],
                    "home_building_act": Dict[str, Any],
                    "conveyancing_act": Dict[str, Any],
                    "vendor_disclosure": Dict[str, Any],
                    "consumer_guarantees": Dict[str, Any],
                }
            }),
            "VIC": type("VICContractTermsOutput", (ContractTermsOutput,), {
                "__annotations__": {
                    "section_32_statement": Dict[str, Any],
                    "owners_corporation": Dict[str, Any],
                    "planning_permits": Dict[str, Any],
                    "sale_of_land_act": Dict[str, Any],
                    "building_permits": Dict[str, Any],
                }
            }),
            "QLD": type("QLDContractTermsOutput", (ContractTermsOutput,), {
                "__annotations__": {
                    "form_1": Dict[str, Any],
                    "body_corporate": Dict[str, Any],
                    "qbcc_licensing": Dict[str, Any],
                    "community_titles": Dict[str, Any],
                    "disclosure_requirements": Dict[str, Any],
                }
            })
        }
        
        return StateAwareParser(
            ContractTermsOutput,
            state_specific_models=state_models,
            default_state="NSW",
            strict_mode=False,
            retry_on_failure=True
        )
    
    @staticmethod
    def create_compliance_parser() -> StateAwareParser:
        """Create state-aware parser for compliance analysis."""
        from app.models.workflow_outputs import ComplianceAnalysisOutput
        
        # Define state-specific compliance models
        state_models = {
            "NSW": type("NSWComplianceOutput", (ComplianceAnalysisOutput,), {
                "__annotations__": {
                    "nsw_conveyancing_compliance": Dict[str, Any],
                    "nsw_planning_compliance": Dict[str, Any],
                    "nsw_building_compliance": Dict[str, Any],
                }
            }),
            "VIC": type("VICComplianceOutput", (ComplianceAnalysisOutput,), {
                "__annotations__": {
                    "vic_sale_of_land_compliance": Dict[str, Any],
                    "vic_planning_compliance": Dict[str, Any],
                    "vic_building_compliance": Dict[str, Any],
                }
            }),
            "QLD": type("QLDComplianceOutput", (ComplianceAnalysisOutput,), {
                "__annotations__": {
                    "qld_property_law_compliance": Dict[str, Any],
                    "qld_planning_compliance": Dict[str, Any],
                    "qld_building_compliance": Dict[str, Any],
                }
            })
        }
        
        return StateAwareParser(
            ComplianceAnalysisOutput,
            state_specific_models=state_models,
            default_state="NSW",
            strict_mode=False,
            retry_on_failure=True
        )
    
    @staticmethod
    def create_risk_parser() -> StateAwareParser:
        """Create state-aware parser for risk analysis."""
        from app.models.workflow_outputs import RiskAnalysisOutput
        
        # Define state-specific risk models
        state_models = {
            "NSW": type("NSWRiskOutput", (RiskAnalysisOutput,), {
                "__annotations__": {
                    "nsw_specific_risks": Dict[str, Any],
                    "nsw_legal_risks": Dict[str, Any],
                }
            }),
            "VIC": type("VICRiskOutput", (RiskAnalysisOutput,), {
                "__annotations__": {
                    "vic_specific_risks": Dict[str, Any],
                    "vic_legal_risks": Dict[str, Any],
                }
            }),
            "QLD": type("QLDRiskOutput", (RiskAnalysisOutput,), {
                "__annotations__": {
                    "qld_specific_risks": Dict[str, Any],
                    "qld_legal_risks": Dict[str, Any],
                }
            })
        }
        
        return StateAwareParser(
            RiskAnalysisOutput,
            state_specific_models=state_models,
            default_state="NSW",
            strict_mode=False,
            retry_on_failure=True
        )


# Convenience function for creating state-aware parsers
def create_state_aware_parser(
    base_model: Type[T],
    state_specific_models: Optional[Dict[str, Type[T]]] = None,
    default_state: str = "NSW",
    **kwargs
) -> StateAwareParser[T]:
    """
    Create a state-aware parser.
    
    Args:
        base_model: Base Pydantic model for parsing
        state_specific_models: Dictionary mapping state codes to state-specific models
        default_state: Default state if none specified
        **kwargs: Additional arguments for base parser
        
    Returns:
        Configured StateAwareParser instance
    """
    return StateAwareParser(
        base_model,
        state_specific_models=state_specific_models,
        default_state=default_state,
        **kwargs
    )
