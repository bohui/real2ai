"""
Unit tests for AnalyzeFinancialTermsNode
"""

import pytest
from datetime import datetime, UTC
from unittest.mock import AsyncMock, patch, MagicMock

from app.agents.nodes.step2_section_analysis.analyze_financial_terms_node import (
    FinancialTermsNode,
)
from app.agents.subflows.step2_section_analysis_workflow import Step2AnalysisState


class TestAnalyzeFinancialTermsNode:
    """Test suite for AnalyzeFinancialTermsNode"""

    @pytest.fixture
    def node(self):
        """Create node instance for testing"""
        mock_workflow = MagicMock()
        mock_workflow.extraction_config = MagicMock()
        return FinancialTermsNode(progress_range=(20, 30), workflow=mock_workflow)

    @pytest.fixture
    def sample_state(self):
        """Sample Step2AnalysisState for testing"""
        return Step2AnalysisState(
            contract_text="Sample contract text for financial analysis",
            extracted_entity
                "content_hash": "test_hash_456",
                "document": {"content_hash": "test_hash_456"},
                "financial": {"purchase_price": 800000, "deposit_amount": 80000},
                "conditions": [{"type": "finance", "deadline": "2024-02-15"}],
            },
            legal_requirements_matrix={
                "NSW": {"purchase_agreement": ["financial_disclosure"]}
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
        assert node.progress_range == (20, 30)

    @pytest.mark.asyncio
    async def test_execute_successful_analysis(self, node, sample_state):
        """Test successful financial terms analysis"""
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
                                    "purchase_price": {
                                        "price_numeric": 800000,
                                        "currency": "AUD",
                                    },
                                    "deposit_amount": {
                                        "amount": 80000,
                                        "percentage": 10,
                                    },
                                    "confidence_score": 0.95,
                                    "overall_risk_level": "low",
                                    "calculation_accuracy_score": 0.98,
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
                                "system_prompt": "You are an expert financial analyst",
                                "user_prompt": "Analyze financial terms in this contract",
                                "metadata": {"model": "gpt-4"},
                            }

                            result = await node.execute(sample_state)

                            # Verify result structure
                            assert "financial_terms_result" in result
                            result_data = result["financial_terms_result"]
                            assert result_data["analyzer"] == "financial_terms"
                            assert result_data["status"] == "completed"
                            assert "timestamp" in result_data
                            assert result_data["confidence_score"] == 0.95

    @pytest.mark.asyncio
    async def test_execute_with_existing_persisted_result(self, node, sample_state):
        """Test short-circuiting when result already exists"""
        with patch(
            "app.services.repositories.contracts_repository.ContractsRepository"
        ) as mock_repo:
            # Mock repository to return existing result
            mock_repo_instance = MagicMock()
            mock_repo_instance.get_contract_by_content_hash.return_value = MagicMock(
                financial_terms={"existing": "financial_result"}
            )
            mock_repo.return_value = mock_repo_instance

            result = await node.execute(sample_state)

            # Should return existing result without LLM processing
            assert "financial_terms_result" in result
            assert result["financial_terms_result"] == {"existing": "financial_result"}

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
                                "system_prompt": "You are an expert financial analyst",
                                "user_prompt": "Analyze financial terms in this contract",
                                "metadata": {"model": "gpt-4"},
                            }

                            result = await node.execute(sample_state)

                            # Should return fallback result
                            assert "financial_terms_result" in result
                            result_data = result["financial_terms_result"]
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
            assert "financial_terms_result" in result
            result_data = result["financial_terms_result"]
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
                                    "purchase_price": {"price_numeric": 800000},
                                    "confidence_score": 0.95,
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
                                "system_prompt": "You are an expert financial analyst",
                                "user_prompt": "Analyze financial terms in this contract",
                                "metadata": {"model": "gpt-4"},
                            }

                            result = await node.execute(sample_state)

                            # Should still return result even if persistence fails
                            assert "financial_terms_result" in result
                            result_data = result["financial_terms_result"]
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
                            "Unstructured financial analysis"
                        )
                        mock_llm_service.return_value = mock_llm

                        # Mock prompt manager
                        with patch.object(
                            node, "prompt_manager"
                        ) as mock_prompt_manager:
                            mock_prompt_manager.render_composed.return_value = {
                                "system_prompt": "You are an expert financial analyst",
                                "user_prompt": "Analyze financial terms in this contract",
                                "metadata": {"model": "gpt-4"},
                            }

                            result = await node.execute(sample_state)

                            # Should return unstructured result
                            assert "financial_terms_result" in result
                            result_data = result["financial_terms_result"]
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
                                    "purchase_price": {"price_numeric": 800000},
                                    "confidence_score": 0.95,
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
                                "system_prompt": "You are an expert financial analyst",
                                "user_prompt": "Analyze financial terms in this contract",
                                "metadata": {"model": "gpt-4"},
                            }

                            await node.execute(sample_state)

                            # Verify progress callback was called
                            mock_callback.assert_called()

    @pytest.mark.asyncio
    async def test_execute_with_financial_context(self, node, sample_state):
        """Test execution with rich financial context"""
        # Enhance sample state with more financial context
        sample_state["extracted_entity"financial"] = {
            "purchase_price": 800000,
            "deposit_amount": 80000,
            "stamp_duty": 32000,
            "settlement_date": "2024-03-15",
            "payment_terms": "30 days",
        }

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
                        # Mock successful LLM response with detailed financial analysis
                        mock_llm = AsyncMock()
                        mock_llm.generate_content.return_value = MagicMock(
                            success=True,
                            parsed_data=MagicMock(
                                model_dump=lambda: {
                                    "purchase_price": {
                                        "price_numeric": 800000,
                                        "currency": "AUD",
                                    },
                                    "deposit_amount": {
                                        "amount": 80000,
                                        "percentage": 10,
                                    },
                                    "stamp_duty": {"amount": 32000, "calculated": True},
                                    "total_cost": {
                                        "amount": 912000,
                                        "breakdown": "detailed",
                                    },
                                    "confidence_score": 0.98,
                                    "overall_risk_level": "low",
                                    "calculation_accuracy_score": 0.99,
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
                                "system_prompt": "You are an expert financial analyst",
                                "user_prompt": "Analyze financial terms in this contract",
                                "metadata": {"model": "gpt-4"},
                            }

                            result = await node.execute(sample_state)

                            # Verify detailed financial analysis
                            assert "financial_terms_result" in result
                            result_data = result["financial_terms_result"]
                            assert result_data["status"] == "completed"
                            assert result_data["calculation_accuracy_score"] == 0.99
                            assert "total_cost" in result_data
