"""
LayoutSummariseNode - Clean text and extract basic contract information

This node takes the text extraction result, cleans up full text, extracts
basic taxonomy and key terms using an LLM with a schema-driven output parser,
and upserts the contract record by content hash.
"""

from typing import Dict, Any, Optional
from datetime import datetime, timezone

from app.agents.subflows.document_processing_workflow import DocumentProcessingState
from .base_node import DocumentProcessingNodeBase


class LayoutSummariseNode(DocumentProcessingNodeBase):
    def __init__(self):
        super().__init__("layout_summarise")

    async def execute(self, state: DocumentProcessingState) -> DocumentProcessingState:
        start_time = datetime.now(timezone.utc)
        self._record_execution()

        try:
            document_id = state.get("document_id")
            text_extraction_result = state.get("text_extraction_result")

            if not document_id:
                return self._handle_error(
                    state,
                    ValueError("Missing document_id"),
                    "Document ID is required",
                    {"operation": "layout_summarise"},
                )

            if not text_extraction_result or not text_extraction_result.success:
                return self._handle_error(
                    state,
                    ValueError("No valid text extraction result"),
                    "Text extraction result is missing or unsuccessful",
                    {
                        "document_id": document_id,
                        "has_extraction_result": bool(text_extraction_result),
                        "extraction_success": (
                            text_extraction_result.success
                            if text_extraction_result
                            else False
                        ),
                    },
                )

            # Get context values
            australian_state = state.get("australian_state") or state.get(
                "processed_summary", {}
            ).get("australian_state")
            if not australian_state:
                # Try to resolve from document record
                try:
                    from app.services.repositories.documents_repository import (
                        DocumentsRepository,
                    )
                    from uuid import UUID

                    docs_repo = DocumentsRepository()
                    document = await docs_repo.get_document(UUID(document_id))
                    if document and getattr(document, "australian_state", None):
                        australian_state = document.australian_state
                except Exception:
                    pass
            contract_type_hint = state.get("contract_type")
            purchase_method_hint = state.get("purchase_method")
            use_category_hint = state.get("use_category")

            full_text = text_extraction_result.full_text or ""
            if not full_text:
                return self._handle_error(
                    state,
                    ValueError("Empty full_text"),
                    "Full text is empty; cannot summarise layout",
                    {"document_id": document_id},
                )

            # Prepare prompt manager and output parser
            from app.core.prompts.manager import get_prompt_manager
            from app.core.prompts.output_parser import create_parser
            from app.prompts.schema.contract_layout_summary_schema import (
                ContractLayoutSummary,
            )

            prompt_manager = get_prompt_manager()
            await prompt_manager.initialize()

            output_parser = create_parser(ContractLayoutSummary)

            # Render prompt via composition and include format instructions automatically
            context = {
                "full_text": full_text,
                "australian_state": australian_state,
                "document_type": state.get("document_type"),
                "contract_type_hint": contract_type_hint,
                "purchase_method_hint": purchase_method_hint,
                "use_category_hint": use_category_hint,
            }

            composition = await prompt_manager.render_composed(
                composition_name="layout_summarise_only",
                context=context,
                output_parser=output_parser,
            )
            system_prompt = composition.get("system_prompt", "")
            rendered_prompt = composition.get("user_prompt", "")

            # Generate response via clients with fallback
            from app.clients.factory import get_openai_client, get_gemini_client

            response: Optional[str] = None
            # Try OpenAI first
            try:
                openai_client = await get_openai_client()
                response = await openai_client.generate_content(
                    rendered_prompt, system_prompt=system_prompt
                )
            except Exception as e:
                self._log_error(
                    f"Error generating content from OpenAI for layout summarise: {e}",
                    exc_info=True,
                )
                response = None

            if not response:
                try:
                    gemini_client = await get_gemini_client()
                    response = await gemini_client.generate_content(
                        rendered_prompt, system_prompt=system_prompt
                    )
                except Exception as e:
                    self._log_error(
                        f"Error generating content from Gemini for layout summarise: {e}",
                        exc_info=True,
                    )
                    response = None

            if not response:
                return self._handle_error(
                    state,
                    ValueError("No response from LLM"),
                    "Failed to obtain layout summary from model",
                    {"document_id": document_id},
                )

            # Parse response
            parsing_result = output_parser.parse_with_retry(response)
            if not parsing_result.success or not parsing_result.parsed_data:
                return self._handle_error(
                    state,
                    ValueError("Parsing failed"),
                    "Failed to parse layout summary output",
                    {
                        "document_id": document_id,
                        "parsing_errors": parsing_result.parsing_errors,
                    },
                )

            summary = parsing_result.parsed_data

            # Upsert into contracts by content hash
            content_hash = state.get("content_hash")
            if not content_hash:
                # Try document metadata fetched earlier
                metadata = state.get("_document_metadata") or {}
                # content_hash may have been set in fetch_document_node
                content_hash = state.get("content_hmac") or metadata.get("content_hash")

            if not content_hash:
                self._log_warning(
                    "Missing content_hash; skipping contract upsert",
                    extra={"document_id": document_id},
                )
            else:
                from app.services.repositories.contracts_repository import (
                    ContractsRepository,
                )

                contracts_repo = ContractsRepository()
                await contracts_repo.upsert_contract_by_content_hash(
                    content_hash=content_hash,
                    contract_type=str(
                        summary.contract_type.value
                        if hasattr(summary.contract_type, "value")
                        else summary.contract_type
                    ),
                    purchase_method=(
                        str(summary.purchase_method.value)
                        if getattr(summary, "purchase_method", None)
                        and hasattr(summary.purchase_method, "value")
                        else getattr(summary, "purchase_method", None)
                    ),
                    use_category=(
                        str(summary.use_category.value)
                        if getattr(summary, "use_category", None)
                        and hasattr(summary.use_category, "value")
                        else getattr(summary, "use_category", None)
                    ),
                    ocr_confidence=summary.ocr_confidence,
                    australian_state=(
                        str(summary.australian_state.value)
                        if getattr(summary, "australian_state", None)
                        and hasattr(summary.australian_state, "value")
                        else getattr(summary, "australian_state", None)
                        or australian_state
                    ),
                    contract_terms=summary.contract_terms,
                )

            # Update state with cleaned text to be available for build_summary
            updated_state = state.copy()
            try:
                # Replace full_text with cleaned text for downstream usage
                ter = updated_state.get("text_extraction_result")
                if ter and hasattr(ter, "full_text"):
                    ter.full_text = summary.raw_text
                    updated_state["text_extraction_result"] = ter
            except Exception:
                # Best effort; ignore failures
                pass

            duration = (datetime.now(timezone.utc) - start_time).total_seconds()
            self._record_success(duration)
            self._log_info(
                f"Layout summarisation complete for document {document_id}",
                extra={
                    "document_id": document_id,
                    "duration_seconds": duration,
                    "updated_contract": bool(content_hash),
                },
            )

            return updated_state

        except Exception as e:
            return self._handle_error(
                state,
                e,
                f"Failed to summarise layout: {str(e)}",
                {
                    "document_id": state.get("document_id"),
                    "operation": "layout_summarise",
                },
            )
