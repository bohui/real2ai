"""
Unit tests for AnalyzeDefaultTerminationNode
"""

import pytest
from datetime import datetime, UTC
from unittest.mock import AsyncMock, patch, MagicMock

from app.agents.nodes.step2_section_analysis_subflow.analyze_default_termination_node import (
    DefaultTerminationNode,
)
from app.agents.subflows.step2_section_analysis_workflow import Step2AnalysisState


class TestAnalyzeDefaultTerminationNode:
    """Test suite for AnalyzeDefaultTerminationNode"""

    @pytest.fixture
    def node(self):
        """Create node instance for testing"""
        return DefaultTerminationNode(progress_range=(50, 60))

    @pytest.fixture
    def sample_state(self):
        """Sample Step2AnalysisState for testing"""
        return Step2AnalysisState(
            contract_text="Sample contract text for default termination analysis",
            entities_extraction={
                "content_hash": "test_hash_default_term",
                "document": {"content_hash": "test_hash_default_term"},
                "default_terms": [
                    {
                        "type": "finance_default",
                        "description": "Default on finance failure",
                        "remedies": ["forfeit_deposit"],
                    },
                    {
                        "type": "inspection_default",
                        "description": "Default on inspection failure",
                        "remedies": ["terminate_contract"],
                    },
                ],
                "termination_clauses": [
                    {
                        "type": "mutual_agreement",
                        "description": "Termination by mutual agreement",
                    },
                    {
                        "type": "breach",
                        "description": "Termination for breach",
                        "notice_period": "14_days",
                    },
                ],
            },
            legal_requirements_matrix={
                "NSW": {"purchase_agreement": ["default_termination_disclosure"]}
            },
            uploaded_diagrams={},
            australian_state="NSW",
            contract_type="purchase_agreement",
            purchase_method=None,
            use_category=None,
            property_condition=None,
            parties_property_result=None,
            financial_terms_result=None,
            conditions_result=None,
            warranties_result=None,
            default_termination_result=None,
            settlement_logistics_result=None,
            title_encumbrances_result=None,
            adjustments_outgoings_result=None,
            disclosure_compliance_result=None,
            special_risks_result=None,
            cross_section_validation_result=None,
            phase1_complete=False,
            phase2_complete=False,
            phase3_complete=False,
            processing_errors=[],
            skipped_analyzers=[],
            total_risk_flags=[],
            start_time=datetime.now(UTC),
            phase_completion_times={},
            total_diagrams_processed=0,
            diagram_processing_success_rate=0.0,
        )

    def test_node_creation(self, node):
        """Test node instance creation"""
        assert node is not None
        assert hasattr(node, "execute")
        assert hasattr(node, "emit_progress")
        assert node.progress_range == (50, 60)

    @pytest.mark.asyncio
    async def test_execute_successful_analysis(self, node, sample_state):
        """Test successful default termination analysis"""
        with patch(
            "app.services.repositories.contracts_repository.ContractsRepository"
        ) as mock_repo:
            # Mock repository to return no existing results
            mock_repo_instance = MagicMock()
            mock_repo_instance.get_contract_by_content_hash.return_value = None
            mock_repo.return_value = mock_repo_instance

            with patch("app.core.prompts.PromptContext"):
                with patch("app.services.get_llm_service") as mock_llm_service:
                    with patch("app.core.prompts.parsers.create_parser") as mock_parser:
                        # Mock successful LLM response
                        mock_llm = AsyncMock()
                        mock_llm.generate_content.return_value = MagicMock(
                            success=True,
                            parsed_data=MagicMock(
                                model_dump=lambda: {
                                    "total_default_events": 2,
                                    "total_termination_clauses": 2,
                                    "default_risk_level": "medium",
                                    "termination_flexibility": "moderate",
                                    "remedies_available": [
                                        "forfeit_deposit",
                                        "terminate_contract",
                                        "sue_for_damages",
                                    ],
                                    "notice_requirements": ["14_days", "immediate"],
                                    "confidence_score": 0.85,
                                    "overall_risk_level": "medium",
                                }
                            ),
                        )
                        mock_llm_service.return_value = mock_llm

                        # Mock parser
                        mock_parser_instance = MagicMock()
                        mock_parser.return_value = mock_parser_instance

                        # Mock prompt manager
                        with patch.object(
                            node, "prompt_manager"
                        ) as mock_prompt_manager:
                            mock_prompt_manager.render_composed.return_value = {
                                "system_prompt": "You are an expert default termination analyst",
                                "user_prompt": "Analyze default and termination terms in this contract",
                                "metadata": {"model": "gpt-4"},
                            }

                            result = await node.execute(sample_state)

                            # Verify result structure
                            assert "default_termination_result" in result
                            result_data = result["default_termination_result"]
                            assert result_data["analyzer"] == "default_termination"
                            assert result_data["status"] == "completed"
                            assert "timestamp" in result_data
                            assert result_data["total_default_events"] == 2

    @pytest.mark.asyncio
    async def test_execute_with_existing_persisted_result(self, node, sample_state):
        """Test short-circuiting when result already exists"""
        with patch(
            "app.services.repositories.contracts_repository.ContractsRepository"
        ) as mock_repo:
            # Mock repository to return existing result
            mock_repo_instance = MagicMock()
            mock_repo_instance.get_contract_by_content_hash.return_value = MagicMock(
                default_termination={"existing": "default_termination_result"}
            )
            mock_repo.return_value = mock_repo_instance

            result = await node.execute(sample_state)

            # Should return existing result without LLM processing
            assert "default_termination_result" in result
            assert result["default_termination_result"] == {
                "existing": "default_termination_result"
            }

    @pytest.mark.asyncio
    async def test_execute_parsing_failure_fallback(self, node, sample_state):
        """Test fallback behavior when LLM parsing fails"""
        with patch(
            "app.services.repositories.contracts_repository.ContractsRepository"
        ) as mock_repo:
            # Mock repository to return no existing results
            mock_repo_instance = MagicMock()
            mock_repo_instance.get_contract_by_content_hash.return_value = None
            mock_repo.return_value = mock_repo_instance

            with patch("app.core.prompts.PromptContext"):
                with patch("app.services.get_llm_service") as mock_llm_service:
                    with patch("app.core.prompts.parsers.create_parser") as mock_parser:
                        # Mock failed LLM response
                        mock_llm = AsyncMock()
                        mock_llm.generate_content.return_value = MagicMock(
                            success=False,
                            parsed_data=None,
                        )
                        mock_llm_service.return_value = mock_llm

                        # Mock parser
                        mock_parser_instance = MagicMock()
                        mock_parser.return_value = mock_parser_instance

                        # Mock prompt manager
                        with patch.object(
                            node, "prompt_manager"
                        ) as mock_prompt_manager:
                            mock_prompt_manager.render_composed.return_value = {
                                "system_prompt": "You are an expert default termination analyst",
                                "user_prompt": "Analyze default and termination terms in this contract",
                                "metadata": {"model": "gpt-4"},
                            }

                            result = await node.execute(sample_state)

                            # Should return fallback result
                            assert "default_termination_result" in result
                            result_data = result["default_termination_result"]
                            assert result_data["status"] == "parsing_failed"
                            assert "error" in result_data

    @pytest.mark.asyncio
    async def test_execute_exception_handling(self, node, sample_state):
        """Test exception handling during execution"""
        with patch(
            "app.services.repositories.contracts_repository.ContractsRepository"
        ) as mock_repo:
            # Mock repository to raise exception
            mock_repo.side_effect = Exception("Database connection failed")

            result = await node.execute(sample_state)

            # Should return error result
            assert "default_termination_result" in result
            result_data = result["default_termination_result"]
            assert result_data["status"] == "error"
            assert "Database connection failed" in result_data["error"]

    def test_progress_callback_setting(self, node):
        """Test progress callback can be set"""
        mock_callback = AsyncMock()
        node.set_progress_callback(mock_callback)
        assert node.progress_callback == mock_callback

    @pytest.mark.asyncio
    async def test_progress_emission(self, node, sample_state):
        """Test progress emission during execution"""
        mock_callback = AsyncMock()
        node.set_progress_callback(mock_callback)

        with patch(
            "app.services.repositories.contracts_repository.ContractsRepository"
        ) as mock_repo:
            # Mock repository to return no existing results
            mock_repo_instance = MagicMock()
            mock_repo_instance.get_contract_by_content_hash.return_value = None
            mock_repo.return_value = mock_repo_instance

            with patch("app.core.prompts.PromptContext"):
                with patch("app.services.get_llm_service") as mock_llm_service:
                    with patch("app.core.prompts.parsers.create_parser") as mock_parser:
                        # Mock successful LLM response
                        mock_llm = AsyncMock()
                        mock_llm.generate_content.return_value = MagicMock(
                            success=True,
                            parsed_data=MagicMock(
                                model_dump=lambda: {
                                    "total_default_events": 2,
                                    "default_risk_level": "medium",
                                    "confidence_score": 0.85,
                                }
                            ),
                        )
                        mock_llm_service.return_value = mock_llm

                        # Mock parser
                        mock_parser_instance = MagicMock()
                        mock_parser.return_value = mock_parser_instance

                        # Mock prompt manager
                        with patch.object(
                            node, "prompt_manager"
                        ) as mock_prompt_manager:
                            mock_prompt_manager.render_composed.return_value = {
                                "system_prompt": "You are an expert default termination analyst",
                                "user_prompt": "Analyze default and termination terms in this contract",
                                "metadata": {"model": "gpt-4"},
                            }

                            await node.execute(sample_state)

                            # Verify progress callback was called
                            mock_callback.assert_called()

    @pytest.mark.asyncio
    async def test_execute_with_complex_default_termination(self, node, sample_state):
        """Test execution with complex default termination context"""
        # Enhance sample state with more complex default termination terms
        sample_state["entities_extraction"]["default_terms"] = [
            {
                "type": "finance_default",
                "description": "Default on finance failure",
                "remedies": ["forfeit_deposit", "sue_for_damages"],
                "grace_period": "7_days",
            },
            {
                "type": "inspection_default",
                "description": "Default on inspection failure",
                "remedies": ["terminate_contract", "renegotiate_price"],
                "notice_period": "5_days",
            },
            {
                "type": "settlement_default",
                "description": "Default on settlement failure",
                "remedies": ["penalty_interest", "extend_settlement"],
                "penalty_rate": "15%",
            },
            {
                "type": "title_default",
                "description": "Default on title issues",
                "remedies": ["terminate_contract", "compensation"],
                "compensation_amount": "5000",
            },
        ]
        sample_state["entities_extraction"]["termination_clauses"] = [
            {
                "type": "mutual_agreement",
                "description": "Termination by mutual agreement",
                "notice_period": "immediate",
            },
            {
                "type": "breach",
                "description": "Termination for breach",
                "notice_period": "14_days",
                "cure_period": "7_days",
            },
            {
                "type": "force_majeure",
                "description": "Termination due to force majeure",
                "notice_period": "30_days",
            },
            {
                "type": "cooling_off",
                "description": "Cooling off period termination",
                "notice_period": "5_days",
                "refund": "full_deposit",
            },
        ]

        with patch(
            "app.services.repositories.contracts_repository.ContractsRepository"
        ) as mock_repo:
            # Mock repository to return no existing results
            mock_repo_instance = MagicMock()
            mock_repo_instance.get_contract_by_content_hash.return_value = None
            mock_repo.return_value = mock_repo_instance

            with patch("app.core.prompts.PromptContext"):
                with patch("app.services.get_llm_service") as mock_llm_service:
                    with patch("app.core.prompts.parsers.create_parser") as mock_parser:
                        # Mock successful LLM response with detailed default termination analysis
                        mock_llm = AsyncMock()
                        mock_llm.generate_content.return_value = MagicMock(
                            success=True,
                            parsed_data=MagicMock(
                                model_dump=lambda: {
                                    "total_default_events": 4,
                                    "total_termination_clauses": 4,
                                    "default_risk_level": "high",
                                    "termination_flexibility": "high",
                                    "remedies_available": [
                                        "forfeit_deposit",
                                        "terminate_contract",
                                        "sue_for_damages",
                                        "renegotiate_price",
                                        "penalty_interest",
                                        "compensation",
                                    ],
                                    "notice_requirements": [
                                        "immediate",
                                        "5_days",
                                        "7_days",
                                        "14_days",
                                        "30_days",
                                    ],
                                    "confidence_score": 0.92,
                                    "overall_risk_level": "high",
                                    "risk_factors": [
                                        "multiple_default_scenarios",
                                        "complex_termination_clauses",
                                        "high_penalty_rates",
                                    ],
                                    "protection_measures": [
                                        "cooling_off_period",
                                        "cure_periods",
                                        "mutual_agreement_option",
                                    ],
                                    "recommendations": [
                                        "review_default_penalties",
                                        "consider_insurance",
                                        "negotiate_grace_periods",
                                    ],
                                }
                            ),
                        )
                        mock_llm_service.return_value = mock_llm

                        # Mock parser
                        mock_parser_instance = MagicMock()
                        mock_parser.return_value = mock_parser_instance

                        # Mock prompt manager
                        with patch.object(
                            node, "prompt_manager"
                        ) as mock_prompt_manager:
                            mock_prompt_manager.render_composed.return_value = {
                                "system_prompt": "You are an expert default termination analyst",
                                "user_prompt": "Analyze default and termination terms in this contract",
                                "metadata": {"model": "gpt-4"},
                            }

                            result = await node.execute(sample_state)

                            # Verify detailed default termination analysis
                            assert "default_termination_result" in result
                            result_data = result["default_termination_result"]
                            assert result_data["status"] == "completed"
                            assert result_data["total_default_events"] == 4
                            assert result_data["default_risk_level"] == "high"
                            assert "risk_factors" in result_data
                            assert "protection_measures" in result_data
                            assert "recommendations" in result_data

    @pytest.mark.asyncio
    async def test_execute_with_no_default_termination(self, node, sample_state):
        """Test execution when no default termination terms are present"""
        # Remove default termination terms from sample state
        sample_state["entities_extraction"]["default_terms"] = []
        sample_state["entities_extraction"]["termination_clauses"] = []

        with patch(
            "app.services.repositories.contracts_repository.ContractsRepository"
        ) as mock_repo:
            # Mock repository to return no existing results
            mock_repo_instance = MagicMock()
            mock_repo_instance.get_contract_by_content_hash.return_value = None
            mock_repo.return_value = mock_repo_instance

            with patch("app.core.prompts.PromptContext"):
                with patch("app.services.get_llm_service") as mock_llm_service:
                    with patch("app.core.prompts.parsers.create_parser") as mock_parser:
                        # Mock successful LLM response for no default termination terms
                        mock_llm = AsyncMock()
                        mock_llm.generate_content.return_value = MagicMock(
                            success=True,
                            parsed_data=MagicMock(
                                model_dump=lambda: {
                                    "total_default_events": 0,
                                    "total_termination_clauses": 0,
                                    "default_risk_level": "low",
                                    "termination_flexibility": "low",
                                    "remedies_available": ["standard_legal_remedies"],
                                    "notice_requirements": ["standard_legal_notice"],
                                    "confidence_score": 1.0,
                                    "overall_risk_level": "low",
                                    "notes": "No explicit default or termination terms found, standard legal remedies apply",
                                    "recommendations": [
                                        "consider_adding_explicit_default_terms",
                                        "define_termination_procedures",
                                    ],
                                    "legal_implications": [
                                        "rely_on_statutory_defaults",
                                        "common_law_termination_rights",
                                    ],
                                }
                            ),
                        )
                        mock_llm_service.return_value = mock_llm

                        # Mock parser
                        mock_parser_instance = MagicMock()
                        mock_parser.return_value = mock_parser_instance

                        # Mock prompt manager
                        with patch.object(
                            node, "prompt_manager"
                        ) as mock_prompt_manager:
                            mock_prompt_manager.render_composed.return_value = {
                                "system_prompt": "You are an expert default termination analyst",
                                "user_prompt": "Analyze default and termination terms in this contract",
                                "metadata": {"model": "gpt-4"},
                            }

                            result = await node.execute(sample_state)

                            # Verify analysis of no default termination terms
                            assert "default_termination_result" in result
                            result_data = result["default_termination_result"]
                            assert result_data["status"] == "completed"
                            assert result_data["total_default_events"] == 0
                            assert result_data["default_risk_level"] == "low"
                            assert "notes" in result_data
                            assert "recommendations" in result_data
                            assert "legal_implications" in result_data
