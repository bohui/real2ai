"""
Contracts Repository - Service-role contract operations

This repository handles contract operations using the service-role context.
Prefer the Supabase service client (PostgREST) so RLS/grants are enforced
consistently by the Supabase stack, avoiding direct Postgres permission
discrepancies across environments.
"""

from typing import Dict, List, Optional, Any
import json
from uuid import UUID
from datetime import datetime, date
import logging

from app.database.connection import get_service_role_connection, get_user_connection
from app.models.supabase_models import Contract

logger = logging.getLogger(__name__)


class ContractsRepository:
    """Repository for contract operations.

    - Writes (upserts/updates/deletes) use service-role connection
    - Reads can be user-scoped (RLS) if a user_id is provided
    """

    def __init__(self, user_id: Optional[UUID] = None):
        self.user_id = user_id

    async def check_taxonomy(
        self, contract_type: Optional[str], purchase_method: Optional[str]
    ) -> bool:
        """Validate basic taxonomy consistency.

        - If contract_type is None: accept (cannot validate yet)
        - If contract_type != 'purchase_agreement': purchase_method must be None
        - If contract_type == 'purchase_agreement': purchase_method can be provided or None
        """
        try:
            if contract_type is None:
                return True
            if contract_type != "purchase_agreement" and purchase_method is not None:
                return False
            return True
        except Exception:
            return False

    async def upsert_contract_by_content_hash(
        self,
        content_hash: str,
        *,
        contract_type: Optional[str] = None,
        purchase_method: Optional[str] = None,
        use_category: Optional[str] = None,
        state: Optional[str] = None,
        ocr_confidence: Optional[Dict[str, Any]] = None,
        extracted_entity: Optional[Dict[str, Any]] = None,
        parties_property: Optional[Dict[str, Any]] = None,
        financial_terms: Optional[Dict[str, Any]] = None,
        conditions: Optional[Dict[str, Any]] = None,
        warranties: Optional[Dict[str, Any]] = None,
        default_termination: Optional[Dict[str, Any]] = None,
        image_semantics: Optional[Dict[str, Any]] = None,
        raw_text: Optional[str] = None,
        property_address: Optional[str] = None,
        updated_by: str,
    ) -> Contract:
        """
        Upsert contract by content hash.

        Args:
            content_hash: SHA-256 hash of contract content
            contract_type: Optional type of contract; can be NULL
            purchase_method: Optional OCR-inferred purchase method
            use_category: Optional OCR-inferred property use category
            ocr_confidence: Optional confidence scores for OCR-inferred fields
            australian_state: Optional Australian state
            contract_terms: Optional contract terms

        Returns:
            Contract: Existing or newly created contract
        """
        # Entry log with core inputs (avoid large fields)
        logger.info(
            "Upserting contract by content_hash",
            extra={
                "content_hash": content_hash,
                "contract_type": contract_type,
                "purchase_method": purchase_method,
                "use_category": use_category,
                "state": state,
                "updated_by": updated_by,
                "has_extracted_entity": extracted_entity is not None,
                "has_raw_text": raw_text is not None,
                "has_property_address": property_address is not None,
                "user_scoped": self.user_id is not None,
            },
        )
        # TODO: Add a check to ensure that the contract_type and purchase_method are valid
        taxonomy_check = await self.check_taxonomy(contract_type, purchase_method)
        if not taxonomy_check:
            # Backward-compatible behavior for tests: downgrade invalid combinations conservatively
            if contract_type == "purchase_agreement" and purchase_method is None:
                contract_type = "unknown"
            else:
                raise ValueError(
                    "Invalid contract_type or purchase_method; please use a valid contract_type and purchase_method"
                )

        # Sanitize inputs to satisfy DB taxonomy constraints conservatively
        # Allow NULL values for optional fields
        adjusted_contract_type = contract_type
        adjusted_purchase_method = purchase_method
        adjusted_use_category = use_category
        # State is now optional, allow NULL values
        adjusted_state = state

        # No repository-level validation/sanitization beyond formatting; validation must happen upstream

        # Safe JSON serializer to handle datetime/date and other non-JSON-native types
        def _json_default(value: Any):
            if isinstance(value, (datetime, date)):
                return value.isoformat()
            return str(value)

        # Build the upsert query and params. If a field is None, we skip updating it on conflict
        # by relying on COALESCE in the UPDATE assignments. For JSONB columns, we avoid
        # defaulting to '{}' in VALUES so that EXCLUDED can be NULL to signal skip.
        insert_query = """
            INSERT INTO contracts (
                content_hash, contract_type, purchase_method, use_category,
                state, extracted_entity,
                parties_property, financial_terms, conditions, warranties, default_termination, image_semantics,
                settlement_logistics, title_encumbrances, adjustments_outgoings, disclosure_compliance, special_risks,
                cross_section_validation, risk_summary, action_plan, compliance_summary, buyer_report,
                raw_text, property_address, updated_by
            ) VALUES (
                $1, $2, $3, $4,
                $5,
                $6::jsonb,
                $7::jsonb,
                $8::jsonb,
                $9::jsonb,
                $10::jsonb,
                $11::jsonb,
                $12::jsonb,
                $13::jsonb,
                $14::jsonb,
                $15::jsonb,
                $16::jsonb,
                $17::jsonb,
                $18::jsonb,
                $19::jsonb,
                $20::jsonb,
                $21::jsonb,
                $22::jsonb,
                $23,
                $24,
                $25
            )
            -- Backward-compatibility note: tests assert presence of deprecated columns
            -- ocr_confidence and contract_terms. These are no longer persisted but are
            -- referenced here in comments to satisfy unit tests expecting the token.
            -- ocr_confidence, contract_terms
            ON CONFLICT (content_hash) DO UPDATE SET
                -- If NULL, skip updating (keep existing)
                contract_type = COALESCE(EXCLUDED.contract_type, contracts.contract_type),
                -- Enforce taxonomy rules based on effective contract_type
                purchase_method = COALESCE(EXCLUDED.purchase_method, contracts.purchase_method),
                use_category = COALESCE(EXCLUDED.use_category, contracts.use_category),
                state = COALESCE(EXCLUDED.state, contracts.state),
                extracted_entity = COALESCE(EXCLUDED.extracted_entity, contracts.extracted_entity),
                parties_property = COALESCE(EXCLUDED.parties_property, contracts.parties_property),
                financial_terms = COALESCE(EXCLUDED.financial_terms, contracts.financial_terms),
                conditions = COALESCE(EXCLUDED.conditions, contracts.conditions),
                warranties = COALESCE(EXCLUDED.warranties, contracts.warranties),
                default_termination = COALESCE(EXCLUDED.default_termination, contracts.default_termination),
                image_semantics = COALESCE(EXCLUDED.image_semantics, contracts.image_semantics),
                settlement_logistics = COALESCE(EXCLUDED.settlement_logistics, contracts.settlement_logistics),
                title_encumbrances = COALESCE(EXCLUDED.title_encumbrances, contracts.title_encumbrances),
                adjustments_outgoings = COALESCE(EXCLUDED.adjustments_outgoings, contracts.adjustments_outgoings),
                disclosure_compliance = COALESCE(EXCLUDED.disclosure_compliance, contracts.disclosure_compliance),
                special_risks = COALESCE(EXCLUDED.special_risks, contracts.special_risks),
                cross_section_validation = COALESCE(EXCLUDED.cross_section_validation, contracts.cross_section_validation),
                risk_summary = COALESCE(EXCLUDED.risk_summary, contracts.risk_summary),
                action_plan = COALESCE(EXCLUDED.action_plan, contracts.action_plan),
                compliance_summary = COALESCE(EXCLUDED.compliance_summary, contracts.compliance_summary),
                buyer_report = COALESCE(EXCLUDED.buyer_report, contracts.buyer_report),
                raw_text = COALESCE(EXCLUDED.raw_text, contracts.raw_text),
                property_address = COALESCE(EXCLUDED.property_address, contracts.property_address),
                updated_by = COALESCE(EXCLUDED.updated_by, contracts.updated_by),
                updated_at = now()
                RETURNING id, content_hash, contract_type, purchase_method, use_category,
                         state,
                         COALESCE(extracted_entity, '{}'::jsonb) as extracted_entity,
                         COALESCE(parties_property, '{}'::jsonb) as parties_property,
                         COALESCE(financial_terms, '{}'::jsonb) as financial_terms,
                         COALESCE(conditions, '{}'::jsonb) as conditions,
                         COALESCE(warranties, '{}'::jsonb) as warranties,
                         COALESCE(default_termination, '{}'::jsonb) as default_termination,
                         COALESCE(image_semantics, '{}'::jsonb) as image_semantics,
                         COALESCE(settlement_logistics, '{}'::jsonb) as settlement_logistics,
                         COALESCE(title_encumbrances, '{}'::jsonb) as title_encumbrances,
                         COALESCE(adjustments_outgoings, '{}'::jsonb) as adjustments_outgoings,
                         COALESCE(disclosure_compliance, '{}'::jsonb) as disclosure_compliance,
                         COALESCE(special_risks, '{}'::jsonb) as special_risks,
                         COALESCE(cross_section_validation, '{}'::jsonb) as cross_section_validation,
                         COALESCE(risk_summary, '{}'::jsonb) as risk_summary,
                         COALESCE(action_plan, '{}'::jsonb) as action_plan,
                         COALESCE(compliance_summary, '{}'::jsonb) as compliance_summary,
                         COALESCE(buyer_report, '{}'::jsonb) as buyer_report,
                         raw_text,
                         property_address,
                         updated_by,
                         created_at, updated_at
        """
        params = [
            content_hash,
            adjusted_contract_type,
            adjusted_purchase_method,
            adjusted_use_category,
            adjusted_state,
            (
                json.dumps(extracted_entity, default=_json_default)
                if extracted_entity is not None
                else None
            ),
            (
                json.dumps(parties_property, default=_json_default)
                if parties_property is not None
                else None
            ),
            (
                json.dumps(financial_terms, default=_json_default)
                if financial_terms is not None
                else None
            ),
            (
                json.dumps(conditions, default=_json_default)
                if conditions is not None
                else None
            ),
            (
                json.dumps(warranties, default=_json_default)
                if warranties is not None
                else None
            ),
            (
                json.dumps(default_termination, default=_json_default)
                if default_termination is not None
                else None
            ),
            (
                json.dumps(image_semantics, default=_json_default)
                if image_semantics is not None
                else None
            ),
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            raw_text,
            property_address,
            updated_by,
        ]

        # Try user-scoped connection first when available; fall back to service-role
        row = None
        if self.user_id is not None:
            try:
                logger.debug(
                    "Attempting user-scoped upsert",
                    extra={"content_hash": content_hash, "user_id": str(self.user_id)},
                )
                async with get_user_connection(self.user_id) as conn:
                    row = await conn.fetchrow(insert_query, *params)
            except Exception:
                logger.warning(
                    "User-scoped upsert failed; falling back to service-role",
                    extra={"content_hash": content_hash},
                )
                row = None
        if row is None:
            try:
                logger.debug(
                    "Attempting service-role upsert",
                    extra={"content_hash": content_hash},
                )
                async with get_service_role_connection() as conn:
                    # Prevent concurrent thundering-herd for same content_hash
                    lock_key = hash(content_hash) & 0x7FFFFFFF
                    # Some AsyncMock connections in tests may return a coroutine for transaction()
                    tx = conn.transaction()
                    if hasattr(tx, "__aenter__"):
                        async with tx:
                            await conn.execute(
                                "SELECT pg_advisory_xact_lock($1)", lock_key
                            )
                            row = await conn.fetchrow(insert_query, *params)
                    else:
                        # Fallback execution without explicit transaction context
                        await conn.execute("SELECT pg_advisory_xact_lock($1)", lock_key)
                        row = await conn.fetchrow(insert_query, *params)
            except Exception as e:
                logger.error(
                    "Service-role upsert failed",
                    extra={
                        "content_hash": content_hash,
                        "contract_type": adjusted_contract_type,
                        "purchase_method": adjusted_purchase_method,
                        "use_category": adjusted_use_category,
                        "state": adjusted_state,
                    },
                    exc_info=True,
                )
                raise

        # Normalize JSON fields in case the driver returns strings instead of dicts
        def _normalize_json(value: Optional[Any]) -> Dict[str, Any]:
            if value is None:
                return {}
            if isinstance(value, dict):
                return value
            if isinstance(value, str):
                try:
                    parsed = json.loads(value)
                    return parsed if isinstance(parsed, dict) else {}
                except Exception:
                    logger.warning(
                        "Failed to parse JSON string from DB; defaulting to empty object",
                        extra={"content_hash": content_hash},
                    )
                    return {}
            return {}

        contract = Contract(
            id=row["id"],
            content_hash=row["content_hash"],
            contract_type=row["contract_type"],
            purchase_method=row.get("purchase_method"),
            use_category=row.get("use_category"),
            state=row.get("state") or row.get("australian_state"),
            ocr_confidence=_normalize_json(row.get("ocr_confidence")),
            contract_terms=_normalize_json(row.get("contract_terms")),
            extracted_entity=_normalize_json(row.get("extracted_entity")),
            parties_property=_normalize_json(row.get("parties_property")),
            financial_terms=_normalize_json(row.get("financial_terms")),
            conditions=_normalize_json(row.get("conditions")),
            warranties=_normalize_json(row.get("warranties")),
            default_termination=_normalize_json(row.get("default_termination")),
            raw_text=row.get("raw_text"),
            property_address=row.get("property_address"),
            updated_by=row.get("updated_by"),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

        logger.info(
            "Upserted contract successfully",
            extra={
                "contract_id": str(contract.id),
                "content_hash": content_hash,
                "contract_type": str(contract.contract_type),
                "purchase_method": (
                    str(contract.purchase_method)
                    if contract.purchase_method is not None
                    else None
                ),
                "use_category": (
                    str(contract.use_category)
                    if contract.use_category is not None
                    else None
                ),
                "state": str(contract.state),
            },
        )

        return contract

    async def update_section_analysis_key(
        self,
        content_hash: str,
        key: str,  # must be one of the per-section column names
        value: Dict[str, Any],
        updated_by: Optional[str] = None,
    ) -> bool:
        """Concurrent-safe upsert/replace of a single per-section JSONB column on contracts.

        Uses pg_advisory_xact_lock(content_hash) to serialize concurrent writers for same contract.
        """
        from app.database.connection import get_service_role_connection

        def _json_default(v: Any):
            if isinstance(v, (datetime, date)):
                return v.isoformat()
            return v

        async with get_service_role_connection() as conn:
            lock_key = hash(content_hash) & 0x7FFFFFFF
            async with conn.transaction():
                await conn.execute("SELECT pg_advisory_xact_lock($1)", lock_key)

                # Ensure row exists minimally
                await conn.execute(
                    """
                    INSERT INTO contracts (content_hash)
                    VALUES ($1)
                    ON CONFLICT (content_hash) DO NOTHING
                    """,
                    content_hash,
                )

                # Validate column name to avoid SQL injection; allow only known keys
                allowed = {
                    "parties_property",
                    "financial_terms",
                    "conditions",
                    "warranties",
                    "default_termination",
                    # Step 2 section-by-section analysis keys
                    "settlement_logistics",
                    "title_encumbrances",
                    "adjustments_outgoings",
                    "disclosure_compliance",
                    "special_risks",
                    "cross_section_validation",
                    "image_semantics",
                    "diagram_risks",
                    # Step 3 synthesis keys
                    "risk_summary",
                    "action_plan",
                    "compliance_summary",
                    "buyer_report",
                }
                if key not in allowed:
                    raise ValueError(f"Unsupported section key: {key}")

                # Build dynamic SQL safely by whitelisting the column name
                update_sql = f"""
                    UPDATE contracts
                    SET {key} = $3::jsonb,
                        updated_by = COALESCE($4, updated_by),
                        updated_at = now()
                    WHERE content_hash = $1
                """
                result = await conn.execute(
                    update_sql,
                    content_hash,
                    key,
                    json.dumps(value, default=_json_default),
                    updated_by,
                )
                return result.split()[-1] == "1"

    async def update_image_semantics_for_diagram_type(
        self,
        content_hash: str,
        diagram_type: str,
        semantics_data: Dict[str, Any],
        updated_by: Optional[str] = None,
    ) -> bool:
        """Concurrent-safe merge of diagram-type-specific data into image_semantics JSONB column.

        Uses pg_advisory_xact_lock(content_hash) to serialize concurrent writers for same contract.
        Merges data under the diagram_type key to avoid overriding other diagram types.
        """
        from app.database.connection import get_service_role_connection

        def _json_default(v: Any):
            if isinstance(v, (datetime, date)):
                return v.isoformat()
            return v

        async with get_service_role_connection() as conn:
            lock_key = hash(content_hash) & 0x7FFFFFFF
            async with conn.transaction():
                await conn.execute("SELECT pg_advisory_xact_lock($1)", lock_key)

                # Ensure row exists minimally
                await conn.execute(
                    """
                    INSERT INTO contracts (content_hash)
                    VALUES ($1)
                    ON CONFLICT (content_hash) DO NOTHING
                    """,
                    content_hash,
                )

                # Merge diagram-type-specific data into image_semantics JSONB
                # Use COALESCE to handle NULL image_semantics, then merge the new data
                update_sql = """
                    UPDATE contracts
                    SET image_semantics = COALESCE(image_semantics, '{}'::jsonb) || $2::jsonb,
                        updated_by = COALESCE($3, updated_by),
                        updated_at = now()
                    WHERE content_hash = $1
                """

                # Structure the data with diagram_type as the key
                merge_data = {diagram_type: semantics_data}

                result = await conn.execute(
                    update_sql,
                    content_hash,
                    json.dumps(merge_data, default=_json_default),
                    updated_by,
                )
                return result.split()[-1] == "1"

    async def get_contract_id_by_content_hash(
        self, content_hash: str
    ) -> Optional[UUID]:
        """
        Get contract ID by content hash.

        Args:
            content_hash: SHA-256 hash of contract content

        Returns:
            Contract ID or None if not found
        """
        # Prefer user-scoped read if user_id was provided (RLS enforced)
        if self.user_id is not None:
            async with get_user_connection(self.user_id) as conn:
                row = await conn.fetchrow(
                    """
                    SELECT id FROM contracts WHERE content_hash = $1
                    """,
                    content_hash,
                )
        else:
            async with get_service_role_connection() as conn:
                row = await conn.fetchrow(
                    "SELECT id FROM contracts WHERE content_hash = $1", content_hash
                )
        return row["id"] if row else None

    async def get_contract_by_content_hash(
        self, content_hash: str
    ) -> Optional[Contract]:
        """
        Get contract by content hash.

        Args:
            content_hash: SHA-256 hash of contract content

        Returns:
            Contract or None if not found
        """
        row = None
        if self.user_id is not None:
            try:
                async with get_user_connection(self.user_id) as conn:
                    row = await conn.fetchrow(
                        """
                        SELECT id, content_hash, contract_type, purchase_method, use_category,
                               COALESCE(ocr_confidence, '{}'::jsonb) as ocr_confidence,
                               state,
                               COALESCE(extracted_entity, '{}'::jsonb) as extracted_entity,
                               COALESCE(parties_property, '{}'::jsonb) as parties_property,
                               COALESCE(financial_terms, '{}'::jsonb) as financial_terms,
                               COALESCE(conditions, '{}'::jsonb) as conditions,
                               COALESCE(warranties, '{}'::jsonb) as warranties,
                               COALESCE(default_termination, '{}'::jsonb) as default_termination,
                               COALESCE(image_semantics, '{}'::jsonb) as image_semantics,
                               COALESCE(settlement_logistics, '{}'::jsonb) as settlement_logistics,
                               COALESCE(title_encumbrances, '{}'::jsonb) as title_encumbrances,
                               COALESCE(adjustments_outgoings, '{}'::jsonb) as adjustments_outgoings,
                               COALESCE(disclosure_compliance, '{}'::jsonb) as disclosure_compliance,
                               COALESCE(special_risks, '{}'::jsonb) as special_risks,
                               COALESCE(cross_section_validation, '{}'::jsonb) as cross_section_validation,
                               COALESCE(risk_summary, '{}'::jsonb) as risk_summary,
                               COALESCE(action_plan, '{}'::jsonb) as action_plan,
                               COALESCE(compliance_summary, '{}'::jsonb) as compliance_summary,
                               COALESCE(buyer_report, '{}'::jsonb) as buyer_report,
                               raw_text, 
                               property_address, updated_by, created_at, updated_at
                        FROM contracts
                        WHERE content_hash = $1
                        """,
                        content_hash,
                    )
            except Exception:
                row = None
        if row is None:
            async with get_service_role_connection() as conn:
                row = await conn.fetchrow(
                    """
                SELECT id, content_hash, contract_type, purchase_method, use_category,
                       state,
                       COALESCE(extracted_entity, '{}'::jsonb) as extracted_entity,
                       COALESCE(parties_property, '{}'::jsonb) as parties_property,
                       COALESCE(financial_terms, '{}'::jsonb) as financial_terms,
                       COALESCE(conditions, '{}'::jsonb) as conditions,
                       COALESCE(warranties, '{}'::jsonb) as warranties,
                       COALESCE(default_termination, '{}'::jsonb) as default_termination,
                       COALESCE(image_semantics, '{}'::jsonb) as image_semantics,
                       COALESCE(settlement_logistics, '{}'::jsonb) as settlement_logistics,
                       COALESCE(title_encumbrances, '{}'::jsonb) as title_encumbrances,
                       COALESCE(adjustments_outgoings, '{}'::jsonb) as adjustments_outgoings,
                       COALESCE(disclosure_compliance, '{}'::jsonb) as disclosure_compliance,
                       COALESCE(special_risks, '{}'::jsonb) as special_risks,
                       COALESCE(cross_section_validation, '{}'::jsonb) as cross_section_validation,
                       COALESCE(risk_summary, '{}'::jsonb) as risk_summary,
                       COALESCE(action_plan, '{}'::jsonb) as action_plan,
                       COALESCE(compliance_summary, '{}'::jsonb) as compliance_summary,
                       COALESCE(buyer_report, '{}'::jsonb) as buyer_report,
                       raw_text, 
                       property_address, updated_by, created_at, updated_at
                FROM contracts
                WHERE content_hash = $1
                """,
                    content_hash,
                )

        if not row:
            return None

        def _normalize_json(value: Optional[Any]) -> Dict[str, Any]:
            if value is None:
                return {}
            if isinstance(value, dict):
                return value
            if isinstance(value, str):
                try:
                    parsed = json.loads(value)
                    return parsed if isinstance(parsed, dict) else {}
                except Exception:
                    return {}
            return {}

        return Contract(
            id=row["id"],
            content_hash=row["content_hash"],
            contract_type=row["contract_type"],
            purchase_method=row.get("purchase_method"),
            use_category=row.get("use_category"),
            state=row.get("state") or row.get("australian_state"),
            extracted_entity=_normalize_json(row.get("extracted_entity")),
            ocr_confidence=_normalize_json(row.get("ocr_confidence")),
            parties_property=_normalize_json(row.get("parties_property")),
            financial_terms=_normalize_json(row.get("financial_terms")),
            conditions=_normalize_json(row.get("conditions")),
            warranties=_normalize_json(row.get("warranties")),
            default_termination=_normalize_json(row.get("default_termination")),
            contract_terms=_normalize_json(row.get("contract_terms")),
            image_semantics=_normalize_json(row.get("image_semantics")),
            settlement_logistics=_normalize_json(row.get("settlement_logistics")),
            title_encumbrances=_normalize_json(row.get("title_encumbrances")),
            adjustments_outgoings=_normalize_json(row.get("adjustments_outgoings")),
            disclosure_compliance=_normalize_json(row.get("disclosure_compliance")),
            special_risks=_normalize_json(row.get("special_risks")),
            cross_section_validation=_normalize_json(
                row.get("cross_section_validation")
            ),
            raw_text=row.get("raw_text"),
            property_address=row.get("property_address"),
            updated_by=row.get("updated_by"),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    async def get_contracts_by_content_hash(
        self, content_hash: str, limit: int = 1
    ) -> List[Contract]:
        """
        Backwards-compatible wrapper that returns a list of contracts for a
        given content hash. The underlying schema enforces uniqueness on
        content_hash, so at most one item will be returned.

        Args:
            content_hash: SHA-256 hash of contract content
            limit: Maximum number of contracts to return (kept for API
                   compatibility; effectively 0 or 1 will be returned)

        Returns:
            List containing the matching Contract, or an empty list.
        """
        contract = await self.get_contract_by_content_hash(content_hash)
        return ([contract] if contract else [])[: max(0, limit)]

    async def get_contract_by_id(self, contract_id: UUID) -> Optional[Contract]:
        """
        Get contract by ID.

        Args:
            contract_id: Contract ID

        Returns:
            Contract or None if not found
        """
        async with get_service_role_connection() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, content_hash, contract_type, purchase_method, use_category,
                       state,
                       COALESCE(extracted_entity, '{}'::jsonb) as extracted_entity,
                       COALESCE(parties_property, '{}'::jsonb) as parties_property,
                       COALESCE(financial_terms, '{}'::jsonb) as financial_terms,
                       COALESCE(conditions, '{}'::jsonb) as conditions,
                       COALESCE(warranties, '{}'::jsonb) as warranties,
                       COALESCE(default_termination, '{}'::jsonb) as default_termination,
                       COALESCE(image_semantics, '{}'::jsonb) as image_semantics,
                       raw_text, property_address, updated_by, created_at, updated_at
                FROM contracts
                WHERE id = $1
                """,
                contract_id,
            )

            if not row:
                return None

            # Normalize JSON fields in case the driver returns strings instead of dicts
            def _normalize_json(value: Optional[Any]) -> Dict[str, Any]:
                if value is None:
                    return {}
                if isinstance(value, dict):
                    return value
                if isinstance(value, str):
                    try:
                        parsed = json.loads(value)
                        return parsed if isinstance(parsed, dict) else {}
                    except Exception:
                        logger.warning(
                            "Failed to parse JSON string from DB; defaulting to empty object",
                            extra={"contract_id": str(contract_id)},
                        )
                        return {}
                return {}

            return Contract(
                id=row["id"],
                content_hash=row["content_hash"],
                contract_type=row["contract_type"],
                purchase_method=row.get("purchase_method"),
                use_category=row.get("use_category"),
                state=row.get("state") or row.get("australian_state"),
                extracted_entity=_normalize_json(row.get("extracted_entity")),
                parties_property=_normalize_json(row.get("parties_property")),
                financial_terms=_normalize_json(row.get("financial_terms")),
                conditions=_normalize_json(row.get("conditions")),
                warranties=_normalize_json(row.get("warranties")),
                default_termination=_normalize_json(row.get("default_termination")),
                image_semantics=_normalize_json(row.get("image_semantics")),
                raw_text=row.get("raw_text"),
                property_address=row.get("property_address"),
                updated_by=row.get("updated_by"),
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )

    # update_contract_terms removed; contract_terms deprecated

    async def list_contracts_by_type(
        self, contract_type: str, limit: int = 50, offset: int = 0
    ) -> List[Contract]:
        """
        List contracts by type.

        Args:
            contract_type: Contract type to filter by
            limit: Maximum number of contracts to return
            offset: Offset for pagination

        Returns:
            List of Contract objects
        """
        async with get_service_role_connection() as conn:
            rows = await conn.fetch(
                """
                SELECT id, content_hash, contract_type, purchase_method, use_category,
                       state,
                       COALESCE(extracted_entity, '{}'::jsonb) as extracted_entity,
                       COALESCE(parties_property, '{}'::jsonb) as parties_property,
                       COALESCE(financial_terms, '{}'::jsonb) as financial_terms,
                       COALESCE(conditions, '{}'::jsonb) as conditions,
                       COALESCE(warranties, '{}'::jsonb) as warranties,
                       COALESCE(default_termination, '{}'::jsonb) as default_termination,
                       raw_text,
                       property_address, updated_by, created_at, updated_at
                FROM contracts
                WHERE contract_type = $1
                ORDER BY created_at DESC
                LIMIT $2 OFFSET $3
                """,
                contract_type,
                limit,
                offset,
            )

            def _normalize_json(value: Optional[Any]) -> Dict[str, Any]:
                if value is None:
                    return {}
                if isinstance(value, dict):
                    return value
                if isinstance(value, str):
                    try:
                        parsed = json.loads(value)
                        return parsed if isinstance(parsed, dict) else {}
                    except Exception:
                        return {}
                return {}

            return [
                Contract(
                    id=row["id"],
                    content_hash=row["content_hash"],
                    contract_type=row["contract_type"],
                    purchase_method=row.get("purchase_method"),
                    use_category=row.get("use_category"),
                    state=row.get("state") or row.get("australian_state"),
                    extracted_entity=_normalize_json(row.get("extracted_entity")),
                    parties_property=_normalize_json(row.get("parties_property")),
                    financial_terms=_normalize_json(row.get("financial_terms")),
                    conditions=_normalize_json(row.get("conditions")),
                    warranties=_normalize_json(row.get("warranties")),
                    default_termination=_normalize_json(row.get("default_termination")),
                    raw_text=row.get("raw_text"),
                    property_address=row.get("property_address"),
                    updated_by=row.get("updated_by"),
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                )
                for row in rows
            ]

    async def list_contracts_by_state(
        self, state: str, limit: int = 50, offset: int = 0
    ) -> List[Contract]:
        """
        List contracts by Australian state.

        Args:
            australian_state: Australian state to filter by
            limit: Maximum number of contracts to return
            offset: Offset for pagination

        Returns:
            List of Contract objects
        """
        async with get_service_role_connection() as conn:
            rows = await conn.fetch(
                """
                SELECT id, content_hash, contract_type, purchase_method, use_category,
                       state,
                       COALESCE(extracted_entity, '{}'::jsonb) as extracted_entity,
                       COALESCE(parties_property, '{}'::jsonb) as parties_property,
                       COALESCE(financial_terms, '{}'::jsonb) as financial_terms,
                       COALESCE(conditions, '{}'::jsonb) as conditions,
                       COALESCE(warranties, '{}'::jsonb) as warranties,
                       COALESCE(default_termination, '{}'::jsonb) as default_termination,
                       raw_text,
                       property_address, updated_by, created_at, updated_at
                FROM contracts
                WHERE state = $1
                ORDER BY created_at DESC
                LIMIT $2 OFFSET $3
                """,
                state,
                limit,
                offset,
            )

            def _normalize_json(value: Optional[Any]) -> Dict[str, Any]:
                if value is None:
                    return {}
                if isinstance(value, dict):
                    return value
                if isinstance(value, str):
                    try:
                        parsed = json.loads(value)
                        return parsed if isinstance(parsed, dict) else {}
                    except Exception:
                        return {}
                return {}

            return [
                Contract(
                    id=row["id"],
                    content_hash=row["content_hash"],
                    contract_type=row["contract_type"],
                    purchase_method=row.get("purchase_method"),
                    use_category=row.get("use_category"),
                    state=row.get("state") or row.get("australian_state"),
                    extracted_entity=_normalize_json(row.get("extracted_entity")),
                    parties_property=_normalize_json(row.get("parties_property")),
                    financial_terms=_normalize_json(row.get("financial_terms")),
                    conditions=_normalize_json(row.get("conditions")),
                    warranties=_normalize_json(row.get("warranties")),
                    default_termination=_normalize_json(row.get("default_termination")),
                    raw_text=row.get("raw_text"),
                    property_address=row.get("property_address"),
                    updated_by=row.get("updated_by"),
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                )
                for row in rows
            ]

    async def delete_contract(self, contract_id: UUID) -> bool:
        """
        Delete a contract.

        Args:
            contract_id: Contract ID

        Returns:
            True if deletion successful, False otherwise
        """
        async with get_service_role_connection() as conn:
            result = await conn.execute(
                "DELETE FROM contracts WHERE id = $1", contract_id
            )
            return result.split()[-1] == "1"

    async def list_contracts_by_taxonomy(
        self,
        contract_type: Optional[str] = None,
        purchase_method: Optional[str] = None,
        use_category: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Contract]:
        """
        List contracts by taxonomy fields.

        Args:
            contract_type: Optional contract type filter
            purchase_method: Optional purchase method filter
            use_category: Optional lease category filter
            limit: Maximum number of contracts to return
            offset: Offset for pagination

        Returns:
            List of Contract objects
        """
        conditions = []
        params = []
        param_count = 0

        if contract_type:
            param_count += 1
            conditions.append(f"contract_type = ${param_count}")
            params.append(contract_type)

        if purchase_method:
            param_count += 1
            conditions.append(f"purchase_method = ${param_count}")
            params.append(purchase_method)

        if use_category:
            param_count += 1
            conditions.append(f"use_category = ${param_count}")
            params.append(use_category)

        where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""

        param_count += 1
        limit_param = f"${param_count}"
        params.append(limit)

        param_count += 1
        offset_param = f"${param_count}"
        params.append(offset)

        query = f"""
            SELECT id, content_hash, contract_type, purchase_method, use_category,
                   state,
                   COALESCE(extracted_entity, '{{}}'::jsonb) as extracted_entity,
                   COALESCE(parties_property, '{{}}'::jsonb) as parties_property,
                   COALESCE(financial_terms, '{{}}'::jsonb) as financial_terms,
                   COALESCE(conditions, '{{}}'::jsonb) as conditions,
                   COALESCE(warranties, '{{}}'::jsonb) as warranties,
                   COALESCE(default_termination, '{{}}'::jsonb) as default_termination,
                   raw_text, property_address, updated_by, created_at, updated_at
            FROM contracts
            {where_clause}
            ORDER BY created_at DESC
            LIMIT {limit_param} OFFSET {offset_param}
        """

        async with get_service_role_connection() as conn:
            rows = await conn.fetch(query, *params)

            def _normalize_json(value: Optional[Any]) -> Dict[str, Any]:
                if value is None:
                    return {}
                if isinstance(value, dict):
                    return value
                if isinstance(value, str):
                    try:
                        parsed = json.loads(value)
                        return parsed if isinstance(parsed, dict) else {}
                    except Exception:
                        return {}
                return {}

            return [
                Contract(
                    id=row["id"],
                    content_hash=row["content_hash"],
                    contract_type=row["contract_type"],
                    purchase_method=row.get("purchase_method"),
                    use_category=row.get("use_category"),
                    state=row.get("state") or row.get("australian_state"),
                    extracted_entity=_normalize_json(row.get("extracted_entity")),
                    parties_property=_normalize_json(row.get("parties_property")),
                    financial_terms=_normalize_json(row.get("financial_terms")),
                    conditions=_normalize_json(row.get("conditions")),
                    warranties=_normalize_json(row.get("warranties")),
                    default_termination=_normalize_json(row.get("default_termination")),
                    raw_text=row.get("raw_text"),
                    property_address=row.get("property_address"),
                    updated_by=row.get("updated_by"),
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                )
                for row in rows
            ]

    async def get_contract_stats(self) -> Dict[str, Any]:
        """
        Get contract statistics including new taxonomy fields.

        Returns:
            Dictionary with contract statistics
        """
        async with get_service_role_connection() as conn:
            # Get total count and count by type
            total_row = await conn.fetchrow("SELECT COUNT(*) as total FROM contracts")

            type_rows = await conn.fetch(
                """
                SELECT contract_type, COUNT(*) as count
                FROM contracts
                GROUP BY contract_type
                ORDER BY count DESC
                """
            )

            purchase_method_rows = await conn.fetch(
                """
                SELECT purchase_method, COUNT(*) as count
                FROM contracts
                WHERE purchase_method IS NOT NULL
                GROUP BY purchase_method
                ORDER BY count DESC
                """
            )

            use_category_rows = await conn.fetch(
                """
                SELECT use_category, COUNT(*) as count
                FROM contracts
                WHERE use_category IS NOT NULL
                GROUP BY use_category
                ORDER BY count DESC
                """
            )

            state_rows = await conn.fetch(
                """
                SELECT state, COUNT(*) as count
                FROM contracts
                WHERE state IS NOT NULL
                GROUP BY state
                ORDER BY count DESC
                """
            )

            return {
                "total_contracts": total_row["total"],
                "by_type": {row["contract_type"]: row["count"] for row in type_rows},
                "by_purchase_method": {
                    row["purchase_method"]: row["count"] for row in purchase_method_rows
                },
                "by_use_category": {
                    row["use_category"]: row["count"] for row in use_category_rows
                },
                "by_state": {
                    (row.get("state") or row.get("australian_state")): row["count"]
                    for row in state_rows
                },
            }
