"""
Unit tests for AnalyzeConditionsNode
"""

import pytest
from datetime import datetime, UTC
from unittest.mock import AsyncMock, patch, MagicMock

from app.agents.nodes.step2_section_analysis.analyze_conditions_node import (
    ConditionsNode,
)
from app.agents.subflows.step2_section_analysis_workflow import Step2AnalysisState


class TestAnalyzeConditionsNode:
    """Test suite for AnalyzeConditionsNode"""

    @pytest.fixture
    def node(self):
        """Create node instance for testing"""
        return ConditionsNode(progress_range=(30, 40))

    @pytest.fixture
    def sample_state(self):
        """Sample Step2AnalysisState for testing"""
        return Step2AnalysisState(
            contract_text="Sample contract text for conditions analysis",
            extracted_entity
                "content_hash": "test_hash_789",
                "document": {"content_hash": "test_hash_789"},
                "conditions": [
                    {
                        "type": "finance",
                        "deadline": "2024-02-15",
                        "description": "Subject to finance",
                    },
                    {
                        "type": "inspection",
                        "deadline": "2024-02-10",
                        "description": "Subject to building inspection",
                    },
                    {
                        "type": "sale",
                        "deadline": "2024-02-20",
                        "description": "Subject to sale of existing property",
                    },
                ],
                "financial": {"purchase_price": 800000},
            },
            legal_requirements_matrix={
                "NSW": {"purchase_agreement": ["conditions_disclosure"]}
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
        assert node.progress_range == (30, 40)

    @pytest.mark.asyncio
    async def test_execute_successful_analysis(self, node, sample_state):
        """Test successful conditions analysis"""
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
                                    "total_conditions": 3,
                                    "finance_conditions": 1,
                                    "inspection_conditions": 1,
                                    "sale_conditions": 1,
                                    "special_conditions_count": 1,
                                    "overall_condition_risk": "medium",
                                    "confidence_score": 0.92,
                                    "critical_deadlines": ["2024-02-10", "2024-02-15"],
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
                                "system_prompt": "You are an expert conditions analyst",
                                "user_prompt": "Analyze conditions in this contract",
                                "metadata": {"model": "gpt-4"},
                            }

                            result = await node.execute(sample_state)

                            # Verify result structure
                            assert "conditions_result" in result
                            result_data = result["conditions_result"]
                            assert result_data["analyzer"] == "conditions"
                            assert result_data["status"] == "completed"
                            assert "timestamp" in result_data
                            assert result_data["total_conditions"] == 3
                            assert result_data["overall_condition_risk"] == "medium"

    @pytest.mark.asyncio
    async def test_execute_with_existing_persisted_result(self, node, sample_state):
        """Test short-circuiting when result already exists"""
        with patch(
            "app.services.repositories.contracts_repository.ContractsRepository"
        ) as mock_repo:
            # Mock repository to return existing result
            mock_repo_instance = MagicMock()
            mock_repo_instance.get_contract_by_content_hash.return_value = MagicMock(
                conditions={"existing": "conditions_result"}
            )
            mock_repo.return_value = mock_repo_instance

            result = await node.execute(sample_state)

            # Should return existing result without LLM processing
            assert "conditions_result" in result
            assert result["conditions_result"] == {"existing": "conditions_result"}

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
                                "system_prompt": "You are an expert conditions analyst",
                                "user_prompt": "Analyze conditions in this contract",
                                "metadata": {"model": "gpt-4"},
                            }

                            result = await node.execute(sample_state)

                            # Should return fallback result
                            assert "conditions_result" in result
                            result_data = result["conditions_result"]
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
            assert "conditions_result" in result
            result_data = result["conditions_result"]
            assert result_data["status"] == "error"
            assert "Database connection failed" in result_data["error"]

    @pytest.mark.asyncio
    async def test_execute_persistence_failure_handling(self, node, sample_state):
        """Test handling when persistence fails"""
        with patch(
            "app.services.repositories.contracts_repository.ContractsRepository"
        ) as mock_repo:
            # Mock repository to return no existing results but fail on update
            mock_repo_instance = MagicMock()
            mock_repo_instance.get_contract_by_content_hash.return_value = None
            mock_repo_instance.update_section_analysis_key.side_effect = Exception(
                "Update failed"
            )
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
                                    "total_conditions": 3,
                                    "overall_condition_risk": "medium",
                                    "confidence_score": 0.92,
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
                                "system_prompt": "You are an expert conditions analyst",
                                "user_prompt": "Analyze conditions in this contract",
                                "metadata": {"model": "gpt-4"},
                            }

                            result = await node.execute(sample_state)

                            # Should still return result even if persistence fails
                            assert "conditions_result" in result
                            result_data = result["conditions_result"]
                            assert result_data["status"] == "completed"

    @pytest.mark.asyncio
    async def test_execute_without_parser_fallback(self, node, sample_state):
        """Test fallback when parser creation fails"""
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
                        # Mock parser creation failure
                        mock_parser.side_effect = Exception("Parser creation failed")

                        # Mock successful unstructured LLM response
                        mock_llm = AsyncMock()
                        mock_llm.generate_content.return_value = (
                            "Unstructured conditions analysis"
                        )
                        mock_llm_service.return_value = mock_llm

                        # Mock prompt manager
                        with patch.object(
                            node, "prompt_manager"
                        ) as mock_prompt_manager:
                            mock_prompt_manager.render_composed.return_value = {
                                "system_prompt": "You are an expert conditions analyst",
                                "user_prompt": "Analyze conditions in this contract",
                                "metadata": {"model": "gpt-4"},
                            }

                            result = await node.execute(sample_state)

                            # Should return unstructured result
                            assert "conditions_result" in result
                            result_data = result["conditions_result"]
                            assert result_data["status"] == "unstructured"
                            assert "response" in result_data

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
                                    "total_conditions": 3,
                                    "overall_condition_risk": "medium",
                                    "confidence_score": 0.92,
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
                                "system_prompt": "You are an expert conditions analyst",
                                "user_prompt": "Analyze conditions in this contract",
                                "metadata": {"model": "gpt-4"},
                            }

                            await node.execute(sample_state)

                            # Verify progress callback was called
                            mock_callback.assert_called()

    @pytest.mark.asyncio
    async def test_execute_with_complex_conditions(self, node, sample_state):
        """Test execution with complex conditions context"""
        # Enhance sample state with more complex conditions
        sample_state["extracted_entity"]["conditions"] = [
            {
                "type": "finance",
                "deadline": "2024-02-15",
                "description": "Subject to finance approval",
                "amount": 800000,
            },
            {
                "type": "inspection",
                "deadline": "2024-02-10",
                "description": "Subject to building and pest inspection",
            },
            {
                "type": "sale",
                "deadline": "2024-02-20",
                "description": "Subject to sale of existing property",
                "timeframe": "30 days",
            },
            {
                "type": "title",
                "deadline": "2024-02-25",
                "description": "Subject to clear title search",
            },
            {
                "type": "special",
                "deadline": "2024-02-28",
                "description": "Subject to council approval for subdivision",
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
                        # Mock successful LLM response with detailed conditions analysis
                        mock_llm = AsyncMock()
                        mock_llm.generate_content.return_value = MagicMock(
                            success=True,
                            parsed_data=MagicMock(
                                model_dump=lambda: {
                                    "total_conditions": 5,
                                    "finance_conditions": 1,
                                    "inspection_conditions": 1,
                                    "sale_conditions": 1,
                                    "title_conditions": 1,
                                    "special_conditions_count": 1,
                                    "overall_condition_risk": "high",
                                    "confidence_score": 0.95,
                                    "critical_deadlines": [
                                        "2024-02-10",
                                        "2024-02-15",
                                        "2024-02-20",
                                    ],
                                    "risk_factors": [
                                        "subdivision_approval",
                                        "clear_title",
                                        "finance_approval",
                                    ],
                                    "compliance_issues": ["council_approval_required"],
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
                                "system_prompt": "You are an expert conditions analyst",
                                "user_prompt": "Analyze conditions in this contract",
                                "metadata": {"model": "gpt-4"},
                            }

                            result = await node.execute(sample_state)

                            # Verify detailed conditions analysis
                            assert "conditions_result" in result
                            result_data = result["conditions_result"]
                            assert result_data["status"] == "completed"
                            assert result_data["total_conditions"] == 5
                            assert result_data["overall_condition_risk"] == "high"
                            assert "risk_factors" in result_data
                            assert "compliance_issues" in result_data

    @pytest.mark.asyncio
    async def test_execute_with_no_conditions(self, node, sample_state):
        """Test execution when no conditions are present"""
        # Remove conditions from sample state
        sample_state["extracted_entity"]["conditions"] = []

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
                        # Mock successful LLM response for no conditions
                        mock_llm = AsyncMock()
                        mock_llm.generate_content.return_value = MagicMock(
                            success=True,
                            parsed_data=MagicMock(
                                model_dump=lambda: {
                                    "total_conditions": 0,
                                    "finance_conditions": 0,
                                    "inspection_conditions": 0,
                                    "sale_conditions": 0,
                                    "special_conditions_count": 0,
                                    "overall_condition_risk": "low",
                                    "confidence_score": 1.0,
                                    "critical_deadlines": [],
                                    "notes": "No conditions found in contract",
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
                                "system_prompt": "You are an expert conditions analyst",
                                "user_prompt": "Analyze conditions in this contract",
                                "metadata": {"model": "gpt-4"},
                            }

                            result = await node.execute(sample_state)

                            # Verify analysis of no conditions
                            assert "conditions_result" in result
                            result_data = result["conditions_result"]
                            assert result_data["status"] == "completed"
                            assert result_data["total_conditions"] == 0
                            assert result_data["overall_condition_risk"] == "low"
                            assert "notes" in result_data
