"""
LayoutSummariseNode - Clean text and extract basic contract information

This node takes the text extraction result, cleans up full text, extracts
basic taxonomy and key terms using an LLM with a schema-driven output parser,
and upserts the contract record by content hash.
"""

from typing import Dict, Any, Optional
import re
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

            # Split full_text into chunks by page delimiter if needed to avoid token limits
            MAX_CHUNK_CHARACTERS = 32768

            def _split_into_page_blocks(text: str) -> list[str]:
                pattern = re.compile(r"^--- Page \d+ ---\n", re.MULTILINE)
                blocks: list[str] = []
                matches = list(pattern.finditer(text))
                if not matches:
                    return [text]
                # Include any preface content before the first page marker
                cursor = 0
                if matches[0].start() > 0:
                    blocks.append(text[0 : matches[0].start()])
                    cursor = matches[0].start()
                for i, m in enumerate(matches):
                    start = m.start()
                    end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
                    blocks.append(text[start:end])
                    cursor = end
                if cursor < len(text):
                    blocks.append(text[cursor:])
                return blocks

            def _chunk_blocks_by_size(blocks: list[str], max_len: int) -> list[str]:
                chunks: list[str] = []
                current: list[str] = []
                current_len = 0
                for block in blocks:
                    block_len = len(block)
                    if block_len > max_len:
                        # Fallback: split oversized block by newline boundaries under max_len
                        self._log_warning(
                            "Single page block exceeds max chunk size; splitting by length",
                            extra={
                                "document_id": document_id,
                                "block_length": block_len,
                                "max_len": max_len,
                            },
                        )
                        start = 0
                        while start < block_len:
                            end = min(start + max_len, block_len)
                            # Try to cut at the last newline within range to avoid mid-line splits
                            newline_pos = block.rfind("\n", start, end)
                            if newline_pos != -1 and newline_pos > start:
                                end = newline_pos + 1
                            part = block[start:end]
                            if current_len + len(part) > max_len and current:
                                chunks.append("".join(current))
                                current = []
                                current_len = 0
                            current.append(part)
                            current_len += len(part)
                            if current_len >= max_len:
                                chunks.append("".join(current))
                                current = []
                                current_len = 0
                            start = end
                        continue

                    if current_len + block_len <= max_len:
                        current.append(block)
                        current_len += block_len
                    else:
                        if current:
                            chunks.append("".join(current))
                        current = [block]
                        current_len = block_len
                if current:
                    chunks.append("".join(current))
                return chunks

            if len(full_text) > MAX_CHUNK_CHARACTERS:
                page_blocks = _split_into_page_blocks(full_text)
                chunks = _chunk_blocks_by_size(page_blocks, MAX_CHUNK_CHARACTERS)
            else:
                chunks = [full_text]

            self._log_info(
                "Layout summarise chunking prepared",
                extra={
                    "document_id": document_id,
                    "num_chunks": len(chunks),
                    "max_chunk_chars": MAX_CHUNK_CHARACTERS,
                },
            )

            # Render and call LLM for each chunk
            from app.clients.factory import get_openai_client, get_gemini_client

            summaries: list[ContractLayoutSummary] = []
            for idx, chunk_text in enumerate(chunks):
                context = {
                    "full_text": chunk_text,
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

                response: Optional[str] = None
                try:
                    openai_client = await get_openai_client()
                    response = await openai_client.generate_content(
                        rendered_prompt, system_prompt=system_prompt
                    )
                except Exception as e:
                    self._log_error(
                        f"Error generating content from OpenAI for layout summarise (chunk {idx + 1}/{len(chunks)}): {e}",
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
                            f"Error generating content from Gemini for layout summarise (chunk {idx + 1}/{len(chunks)}): {e}",
                            exc_info=True,
                        )
                        response = None

                if not response:
                    return self._handle_error(
                        state,
                        ValueError("No response from LLM"),
                        "Failed to obtain layout summary from model",
                        {"document_id": document_id, "chunk_index": idx},
                    )

                parsing_result = output_parser.parse_with_retry(response)
                if not parsing_result.success or not parsing_result.parsed_data:
                    return self._handle_error(
                        state,
                        ValueError("Parsing failed"),
                        "Failed to parse layout summary output",
                        {
                            "document_id": document_id,
                            "chunk_index": idx,
                            "parsing_errors": parsing_result.parsing_errors,
                        },
                    )

                summaries.append(parsing_result.parsed_data)

            # Merge chunked summaries
            def _first_non_empty(values: list[Any]) -> Any:
                for v in values:
                    if v is None:
                        continue
                    if isinstance(v, str) and v.strip() == "":
                        continue
                    if isinstance(v, dict) and not v:
                        continue
                    return v
                return None

            merged_raw_text = "".join([s.raw_text for s in summaries])
            merged_contract_type = _first_non_empty(
                [getattr(s, "contract_type", None) for s in summaries]
            )
            merged_purchase_method = _first_non_empty(
                [getattr(s, "purchase_method", None) for s in summaries]
            )
            merged_use_category = _first_non_empty(
                [getattr(s, "use_category", None) for s in summaries]
            )
            merged_australian_state = _first_non_empty(
                [getattr(s, "australian_state", None) for s in summaries]
            )
            merged_property_address = _first_non_empty(
                [getattr(s, "property_address", None) for s in summaries]
            )
            merged_contract_terms = (
                _first_non_empty(
                    [getattr(s, "contract_terms", None) for s in summaries]
                )
                or {}
            )
            merged_ocr_confidence = (
                _first_non_empty(
                    [getattr(s, "ocr_confidence", None) for s in summaries]
                )
                or {}
            )

            # Fallbacks for required fields
            if merged_contract_type is None:
                from app.schema.enums import ContractType as _ContractType

                merged_contract_type = _ContractType.unknown

            summary = ContractLayoutSummary(
                raw_text=merged_raw_text,
                contract_type=merged_contract_type,
                purchase_method=merged_purchase_method,
                use_category=merged_use_category,
                australian_state=merged_australian_state,
                contract_terms=merged_contract_terms,
                property_address=merged_property_address,
                ocr_confidence=merged_ocr_confidence,
            )

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
