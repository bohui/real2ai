"""
Unit tests for AnalyzeWarrantiesNode
"""

import pytest
from datetime import datetime, UTC
from unittest.mock import AsyncMock, patch, MagicMock

from app.agents.nodes.step2_section_analysis.analyze_warranties_node import (
    WarrantiesNode,
)
from app.agents.subflows.step2_section_analysis_workflow import Step2AnalysisState


class TestAnalyzeWarrantiesNode:
    """Test suite for AnalyzeWarrantiesNode"""

    @pytest.fixture
    def node(self):
        """Create node instance for testing"""
        return WarrantiesNode(progress_range=(40, 50))

    @pytest.fixture
    def sample_state(self):
        """Sample Step2AnalysisState for testing"""
        return Step2AnalysisState(
            contract_text="Sample contract text for warranties analysis",
            extracted_entity
                "content_hash": "test_hash_warranties",
                "document": {"content_hash": "test_hash_warranties"},
                "warranties": [
                    {"type": "title", "description": "Clear title warranty"},
                    {"type": "possession", "description": "Quiet possession warranty"},
                ],
                "property": {"type": "residential", "condition": "existing"},
            },
            legal_requirements_matrix={
                "NSW": {"purchase_agreement": ["warranties_disclosure"]}
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
        assert node.progress_range == (40, 50)

    @pytest.mark.asyncio
    async def test_execute_successful_analysis(self, node, sample_state):
        """Test successful warranties analysis"""
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
                                    "total_warranties": 2,
                                    "title_warranties": 1,
                                    "possession_warranties": 1,
                                    "implied_warranties": ["fitness_for_purpose"],
                                    "overall_warranty_coverage": "comprehensive",
                                    "confidence_score": 0.88,
                                    "risk_level": "low",
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
                                "system_prompt": "You are an expert warranties analyst",
                                "user_prompt": "Analyze warranties in this contract",
                                "metadata": {"model": "gpt-4"},
                            }

                            result = await node.execute(sample_state)

                            # Verify result structure
                            assert "warranties_result" in result
                            result_data = result["warranties_result"]
                            assert result_data["analyzer"] == "warranties"
                            assert result_data["status"] == "completed"
                            assert "timestamp" in result_data
                            assert result_data["total_warranties"] == 2

    @pytest.mark.asyncio
    async def test_execute_with_existing_persisted_result(self, node, sample_state):
        """Test short-circuiting when result already exists"""
        with patch(
            "app.services.repositories.contracts_repository.ContractsRepository"
        ) as mock_repo:
            # Mock repository to return existing result
            mock_repo_instance = MagicMock()
            mock_repo_instance.get_contract_by_content_hash.return_value = MagicMock(
                warranties={"existing": "warranties_result"}
            )
            mock_repo.return_value = mock_repo_instance

            result = await node.execute(sample_state)

            # Should return existing result without LLM processing
            assert "warranties_result" in result
            assert result["warranties_result"] == {"existing": "warranties_result"}

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
                                "system_prompt": "You are an expert warranties analyst",
                                "user_prompt": "Analyze warranties in this contract",
                                "metadata": {"model": "gpt-4"},
                            }

                            result = await node.execute(sample_state)

                            # Should return fallback result
                            assert "warranties_result" in result
                            result_data = result["warranties_result"]
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
            assert "warranties_result" in result
            result_data = result["warranties_result"]
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
                                    "total_warranties": 2,
                                    "overall_warranty_coverage": "comprehensive",
                                    "confidence_score": 0.88,
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
                                "system_prompt": "You are an expert warranties analyst",
                                "user_prompt": "Analyze warranties in this contract",
                                "metadata": {"model": "gpt-4"},
                            }

                            await node.execute(sample_state)

                            # Verify progress callback was called
                            mock_callback.assert_called()

    @pytest.mark.asyncio
    async def test_execute_with_complex_warranties(self, node, sample_state):
        """Test execution with complex warranties context"""
        # Enhance sample state with more complex warranties
        sample_state["extracted_entity"warranties"] = [
            {
                "type": "title",
                "description": "Clear title warranty",
                "scope": "comprehensive",
            },
            {
                "type": "possession",
                "description": "Quiet possession warranty",
                "duration": "perpetual",
            },
            {
                "type": "fitness",
                "description": "Fitness for purpose warranty",
                "implied": True,
            },
            {
                "type": "habitability",
                "description": "Habitable condition warranty",
                "standards": "NSW_building_code",
            },
            {
                "type": "environmental",
                "description": "Environmental compliance warranty",
                "certifications": ["bushfire", "flood"],
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
                        # Mock successful LLM response with detailed warranties analysis
                        mock_llm = AsyncMock()
                        mock_llm.generate_content.return_value = MagicMock(
                            success=True,
                            parsed_data=MagicMock(
                                model_dump=lambda: {
                                    "total_warranties": 5,
                                    "title_warranties": 1,
                                    "possession_warranties": 1,
                                    "fitness_warranties": 1,
                                    "habitability_warranties": 1,
                                    "environmental_warranties": 1,
                                    "implied_warranties": [
                                        "fitness_for_purpose",
                                        "merchantable_quality",
                                    ],
                                    "overall_warranty_coverage": "comprehensive",
                                    "confidence_score": 0.95,
                                    "risk_level": "low",
                                    "compliance_areas": [
                                        "building_code",
                                        "environmental",
                                        "title",
                                    ],
                                    "warranty_strengths": [
                                        "clear_scope",
                                        "comprehensive_coverage",
                                    ],
                                    "potential_gaps": ["future_legislation_changes"],
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
                                "system_prompt": "You are an expert warranties analyst",
                                "user_prompt": "Analyze warranties in this contract",
                                "metadata": {"model": "gpt-4"},
                            }

                            result = await node.execute(sample_state)

                            # Verify detailed warranties analysis
                            assert "warranties_result" in result
                            result_data = result["warranties_result"]
                            assert result_data["status"] == "completed"
                            assert result_data["total_warranties"] == 5
                            assert (
                                result_data["overall_warranty_coverage"]
                                == "comprehensive"
                            )
                            assert "compliance_areas" in result_data
                            assert "warranty_strengths" in result_data
                            assert "potential_gaps" in result_data

    @pytest.mark.asyncio
    async def test_execute_with_no_warranties(self, node, sample_state):
        """Test execution when no warranties are present"""
        # Remove warranties from sample state
        sample_state["extracted_entity"]["warranties"] = []

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
                        # Mock successful LLM response for no warranties
                        mock_llm = AsyncMock()
                        mock_llm.generate_content.return_value = MagicMock(
                            success=True,
                            parsed_data=MagicMock(
                                model_dump=lambda: {
                                    "total_warranties": 0,
                                    "title_warranties": 0,
                                    "possession_warranties": 0,
                                    "implied_warranties": [
                                        "fitness_for_purpose",
                                        "merchantable_quality",
                                    ],
                                    "overall_warranty_coverage": "minimal",
                                    "confidence_score": 1.0,
                                    "risk_level": "medium",
                                    "notes": "No explicit warranties found, only implied warranties apply",
                                    "recommendations": [
                                        "consider_adding_explicit_warranties"
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
                                "system_prompt": "You are an expert warranties analyst",
                                "user_prompt": "Analyze warranties in this contract",
                                "metadata": {"model": "gpt-4"},
                            }

                            result = await node.execute(sample_state)

                            # Verify analysis of no warranties
                            assert "warranties_result" in result
                            result_data = result["warranties_result"]
                            assert result_data["status"] == "completed"
                            assert result_data["total_warranties"] == 0
                            assert result_data["overall_warranty_coverage"] == "minimal"
                            assert "notes" in result_data
                            assert "recommendations" in result_data
