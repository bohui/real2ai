from typing import Dict, Any

from .base_node import Step2NodeBase
from app.agents.subflows.step2_section_analysis_workflow import Step2AnalysisState


class PrepareContextNode(Step2NodeBase):
    async def execute(self, state: Step2AnalysisState) -> Step2AnalysisState:
        updates: Dict[str, Any] = {}

        try:
            entities_extraction = (state or {}).get("entities_extraction") or {}

            # Hoist section seeds and retrieval index from Step 1 entities into Step 2 state
            try:
                seeds = (entities_extraction or {}).get("section_seeds") or {}
                if seeds:
                    updates["section_seeds"] = seeds
                    retrieval_index_id = seeds.get("retrieval_index_id")
                    if retrieval_index_id:
                        updates["retrieval_index_id"] = retrieval_index_id
                    self.logger.info(
                        "Hoisted section_seeds and retrieval_index_id for Step 2",
                        extra={
                            "has_snippets": bool((seeds or {}).get("snippets")),
                            "has_retrieval_instructions": bool(
                                (seeds or {}).get("retrieval_instructions")
                            ),
                            "retrieval_index_id": retrieval_index_id,
                        },
                    )
            except Exception as hoist_err:
                self._log_warning(f"Failed to hoist section seeds: {hoist_err}")

            # Derive legal requirements matrix if not provided
            if not (
                state.get("legal_requirements_matrix")
                or updates.get("legal_requirements_matrix")
            ):
                try:
                    meta = (entities_extraction or {}).get("metadata") or {}

                    contract_type = state.get("contract_type") or meta.get(
                        "contract_type"
                    )
                    purchase_method = state.get("purchase_method") or meta.get(
                        "purchase_method"
                    )
                    use_category = state.get("use_category") or meta.get("use_category")
                    property_condition = state.get("property_condition") or meta.get(
                        "property_condition"
                    )

                    if all(
                        [
                            contract_type,
                            purchase_method,
                            use_category,
                            property_condition,
                        ]
                    ):
                        try:
                            from app.agents.tools.domain.legal_requirements import (
                                derive_legal_requirements,
                            )

                            derived = derive_legal_requirements.invoke(
                                {
                                    "contract_type": str(
                                        getattr(contract_type, "value", contract_type)
                                    ),
                                    "purchase_method": str(
                                        getattr(
                                            purchase_method, "value", purchase_method
                                        )
                                    ),
                                    "use_category": str(
                                        getattr(use_category, "value", use_category)
                                    ),
                                    "property_condition": str(
                                        getattr(
                                            property_condition,
                                            "value",
                                            property_condition,
                                        )
                                    ),
                                }
                            )
                            if isinstance(derived, dict) and derived:
                                updates["legal_requirements_matrix"] = derived
                                self.logger.info(
                                    "Derived legal_requirements_matrix for Step 2",
                                    extra={
                                        "keys": list(derived.keys())[:10],
                                    },
                                )
                        except Exception as derive_err:
                            self._log_warning(
                                f"Failed to derive legal requirements matrix: {derive_err}"
                            )
                    else:
                        self.logger.info(
                            "Skipping legal requirements derivation due to missing metadata",
                            extra={
                                "has_contract_type": bool(contract_type),
                                "has_purchase_method": bool(purchase_method),
                                "has_use_category": bool(use_category),
                                "has_property_condition": bool(property_condition),
                            },
                        )
                except Exception as legal_err:
                    self._log_warning(f"Legal requirements setup failed: {legal_err}")

        except Exception as e:
            return self._handle_node_error(state, e, "Failed during Step 2 preparation")

        # Emit progress and return updates
        await self.emit_progress(
            state, self.progress_range[1], "Prepared Step 2 context"
        )
        return updates
