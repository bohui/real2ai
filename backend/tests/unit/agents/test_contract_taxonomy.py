"""
Tests for contract type taxonomy system.

Tests the contract classification system from contract-type-taxonomy-story.md:
- Contract type validation and cross-field dependencies
- OCR inference for purchase_method and use_category
- Context propagation for analysis workflows
"""

import pytest
from unittest.mock import Mock, patch
from typing import Dict, Any

from app.schema.enums import ContractType, PurchaseMethod, UseCategory, AustralianState
from app.schema.contract_analysis import ContractTaxonomy, ContractAnalysisContext
from app.agents.tools.domain.contract_extraction import infer_contract_taxonomy


class TestContractTaxonomy:
    """Test contract taxonomy validation and dependencies"""

    def test_contract_taxonomy_validation_purchase_agreement(self):
        """Test purchase agreement requires purchase_method, may have use_category"""
        # Valid purchase agreement without use_category
        taxonomy = ContractTaxonomy(
            contract_type=ContractType.PURCHASE_AGREEMENT,
            purchase_method=PurchaseMethod.AUCTION,
            use_category=None,
        )
        assert taxonomy.validate_taxonomy() is True

        # Valid purchase agreement with use_category
        taxonomy = ContractTaxonomy(
            contract_type=ContractType.PURCHASE_AGREEMENT,
            purchase_method=PurchaseMethod.AUCTION,
            use_category=UseCategory.COMMERCIAL,
        )
        assert taxonomy.validate_taxonomy() is True

        # Invalid - missing purchase_method
        taxonomy = ContractTaxonomy(
            contract_type=ContractType.PURCHASE_AGREEMENT,
            purchase_method=None,
            use_category=None,
        )
        assert taxonomy.validate_taxonomy() is False

    def test_contract_taxonomy_validation_lease_agreement(self):
        """Test lease agreement may have use_category, must not have purchase_method"""
        # Valid lease agreement with use_category
        taxonomy = ContractTaxonomy(
            contract_type=ContractType.LEASE_AGREEMENT,
            purchase_method=None,
            use_category=UseCategory.RESIDENTIAL,
        )
        assert taxonomy.validate_taxonomy() is True

        # Valid lease agreement without use_category
        taxonomy = ContractTaxonomy(
            contract_type=ContractType.LEASE_AGREEMENT,
            purchase_method=None,
            use_category=None,
        )
        assert taxonomy.validate_taxonomy() is True

        # Invalid - has purchase_method
        taxonomy = ContractTaxonomy(
            contract_type=ContractType.LEASE_AGREEMENT,
            purchase_method=PurchaseMethod.AUCTION,
            use_category=UseCategory.RESIDENTIAL,
        )
        assert taxonomy.validate_taxonomy() is False

    def test_contract_taxonomy_validation_option_to_purchase(self):
        """Test option to purchase should have neither field"""
        # Valid option to purchase
        taxonomy = ContractTaxonomy(
            contract_type=ContractType.OPTION_TO_PURCHASE,
            purchase_method=None,
            use_category=None,
        )
        assert taxonomy.validate_taxonomy() is True

        # Invalid - has purchase_method
        taxonomy = ContractTaxonomy(
            contract_type=ContractType.OPTION_TO_PURCHASE,
            purchase_method=PurchaseMethod.STANDARD,
            use_category=None,
        )
        assert taxonomy.validate_taxonomy() is False

        # Invalid - has use_category
        taxonomy = ContractTaxonomy(
            contract_type=ContractType.OPTION_TO_PURCHASE,
            purchase_method=None,
            use_category=UseCategory.COMMERCIAL,
        )
        assert taxonomy.validate_taxonomy() is False

    def test_contract_taxonomy_validation_unknown(self):
        """Test unknown allows any combination"""
        # All combinations should be valid for unknown
        taxonomy = ContractTaxonomy(
            contract_type=ContractType.UNKNOWN, purchase_method=None, use_category=None
        )
        assert taxonomy.validate_taxonomy() is True

        taxonomy = ContractTaxonomy(
            contract_type=ContractType.UNKNOWN,
            purchase_method=PurchaseMethod.AUCTION,
            use_category=None,
        )
        assert taxonomy.validate_taxonomy() is True

        taxonomy = ContractTaxonomy(
            contract_type=ContractType.UNKNOWN,
            purchase_method=None,
            use_category=UseCategory.COMMERCIAL,
        )
        assert taxonomy.validate_taxonomy() is True

    def test_contract_taxonomy_validation_for_intake_purchase_agreement(self):
        """Test intake validation allows purchase_method=None for purchase agreements"""
        # Valid during intake - purchase_method will be inferred by OCR
        taxonomy = ContractTaxonomy(
            contract_type=ContractType.PURCHASE_AGREEMENT,
            purchase_method=None,
            use_category=None,
        )
        assert taxonomy.validate_taxonomy_for_intake() is True

        # Valid during intake with both fields
        taxonomy = ContractTaxonomy(
            contract_type=ContractType.PURCHASE_AGREEMENT,
            purchase_method=PurchaseMethod.AUCTION,
            use_category=UseCategory.COMMERCIAL,
        )
        assert taxonomy.validate_taxonomy_for_intake() is True

    def test_contract_taxonomy_validation_for_intake_lease_agreement(self):
        """Test intake validation for lease agreements"""
        # Valid lease agreement
        taxonomy = ContractTaxonomy(
            contract_type=ContractType.LEASE_AGREEMENT,
            purchase_method=None,
            use_category=UseCategory.RESIDENTIAL,
        )
        assert taxonomy.validate_taxonomy_for_intake() is True

        # Invalid - has purchase_method
        taxonomy = ContractTaxonomy(
            contract_type=ContractType.LEASE_AGREEMENT,
            purchase_method=PurchaseMethod.AUCTION,
            use_category=UseCategory.RESIDENTIAL,
        )
        assert taxonomy.validate_taxonomy_for_intake() is False


class TestOCRInference:
    """Test OCR inference for contract taxonomy"""

    def test_infer_purchase_method_auction(self):
        """Test inference of auction purchase method"""
        document_text = """
        CONTRACT OF SALE
        
        This contract is for the sale by auction of property located at 123 Main Street.
        The highest bidder at the auction will be deemed the purchaser.
        Reserve price has been set at $500,000.
        The auctioneer will conduct the bidding process.
        """

        result = infer_contract_taxonomy.invoke(
            {"document_text": document_text, "user_contract_type": "purchase_agreement"}
        )

        assert result["contract_type"] == "purchase_agreement"
        assert result["purchase_method"] == "auction"
        assert result["use_category"] is None
        assert result["confidence_scores"]["purchase_method"] > 0.7
        assert "auction" in str(result["inference_evidence"]["purchase_method"]).lower()

    def test_infer_purchase_method_off_plan(self):
        """Test inference of off-plan purchase method"""
        document_text = """
        OFF THE PLAN PURCHASE AGREEMENT
        
        This agreement is for the purchase of property to be constructed.
        Building works to be commenced within 12 months.
        Completion certificate required before settlement.
        Plan of subdivision attached as Schedule A.
        """

        result = infer_contract_taxonomy.invoke(
            {"document_text": document_text, "user_contract_type": "purchase_agreement"}
        )

        assert result["contract_type"] == "purchase_agreement"
        assert result["purchase_method"] == "off_plan"
        assert result["use_category"] is None
        assert result["confidence_scores"]["purchase_method"] > 0.7

    def test_infer_purchase_method_private_treaty(self):
        """Test inference of private treaty purchase method"""
        document_text = """
        PURCHASE AGREEMENT - PRIVATE TREATY
        
        This sale is by private treaty between vendor and purchaser.
        Direct negotiation has resulted in this agreement.
        No auction or tender process was conducted.
        """

        result = infer_contract_taxonomy.invoke(
            {"document_text": document_text, "user_contract_type": "purchase_agreement"}
        )

        assert result["contract_type"] == "purchase_agreement"
        assert result["purchase_method"] == "private_treaty"
        assert result["use_category"] is None

    def test_infer_purchase_method_standard_default(self):
        """Test default to standard purchase method"""
        document_text = """
        CONTRACT OF SALE
        
        Vendor and Purchaser agree to the following terms.
        Purchase price: $750,000
        Settlement date: 30 days from contract date
        """

        result = infer_contract_taxonomy.invoke(
            {"document_text": document_text, "user_contract_type": "purchase_agreement"}
        )

        assert result["contract_type"] == "purchase_agreement"
        assert result["purchase_method"] == "standard"
        assert result["use_category"] is None
        assert (
            result["confidence_scores"]["purchase_method"] == 0.6
        )  # Default confidence

    def test_infer_purchase_agreement_with_use_category(self):
        """Test inference of use_category for purchase agreement"""
        document_text = """
        COMMERCIAL PURCHASE AGREEMENT
        
        This contract is for the sale by auction of commercial property.
        The highest bidder at the auction will be deemed the purchaser.
        Business premises suitable for office space and commercial activities.
        """

        result = infer_contract_taxonomy.invoke(
            {"document_text": document_text, "user_contract_type": "purchase_agreement"}
        )

        assert result["contract_type"] == "purchase_agreement"
        assert result["purchase_method"] == "auction"
        assert result["use_category"] == "commercial"
        assert result["confidence_scores"]["purchase_method"] > 0.7
        assert result["confidence_scores"]["use_category"] > 0.7

    def test_infer_use_category_residential(self):
        """Test inference of residential lease category"""
        document_text = """
        RESIDENTIAL TENANCY AGREEMENT
        
        This lease is for residential premises only.
        The dwelling shall be used as a private residence.
        Suitable for house rental purposes.
        """

        result = infer_contract_taxonomy.invoke(
            {"document_text": document_text, "user_contract_type": "lease_agreement"}
        )

        assert result["contract_type"] == "lease_agreement"
        assert result["purchase_method"] is None
        assert result["use_category"] == "residential"
        assert result["confidence_scores"]["use_category"] > 0.7

    def test_infer_use_category_commercial(self):
        """Test inference of commercial lease category"""
        document_text = """
        COMMERCIAL LEASE AGREEMENT
        
        These business premises are leased for commercial purposes.
        Suitable for office space and commercial activities.
        Commercial tenancy terms apply.
        """

        result = infer_contract_taxonomy.invoke(
            {"document_text": document_text, "user_contract_type": "lease_agreement"}
        )

        assert result["contract_type"] == "lease_agreement"
        assert result["purchase_method"] is None
        assert result["use_category"] == "commercial"
        assert result["confidence_scores"]["use_category"] > 0.7

    def test_infer_use_category_retail(self):
        """Test inference of retail lease category"""
        document_text = """
        RETAIL LEASE AGREEMENT
        
        This shop lease covers retail premises in the shopping centre.
        Retail tenancy laws apply to this agreement.
        Store rental for retail business operations.
        """

        result = infer_contract_taxonomy.invoke(
            {"document_text": document_text, "user_contract_type": "lease_agreement"}
        )

        assert result["contract_type"] == "lease_agreement"
        assert result["purchase_method"] is None
        assert result["use_category"] == "retail"

    def test_infer_option_to_purchase_no_inference(self):
        """Test option to purchase doesn't infer additional fields"""
        document_text = """
        OPTION TO PURCHASE AGREEMENT
        
        This option grants the right to purchase the property.
        Option period expires in 6 months.
        Exercise price is set at $600,000.
        """

        result = infer_contract_taxonomy.invoke(
            {"document_text": document_text, "user_contract_type": "option_to_purchase"}
        )

        assert result["contract_type"] == "option_to_purchase"
        assert result["purchase_method"] is None
        assert result["use_category"] is None
        assert result["confidence_scores"] == {}

    def test_invalid_contract_type(self):
        """Test handling of invalid contract type"""
        document_text = "Sample contract text"

        result = infer_contract_taxonomy.invoke(
            {"document_text": document_text, "user_contract_type": "invalid_type"}
        )

        assert "error" in result
        assert "Invalid contract_type" in result["error"]


class TestContextPropagation:
    """Test context propagation for analysis workflows"""

    def test_create_purchase_agreement_context(self):
        """Test creating context for purchase agreement"""
        context = ContractAnalysisContext.create_context(
            contract_type=ContractType.PURCHASE_AGREEMENT,
            purchase_method=PurchaseMethod.AUCTION,
            document_id="doc-123",
            australian_state=AustralianState.NSW,
            purchase_method_confidence=0.92,
        )

        assert context.contract.contract_type == ContractType.PURCHASE_AGREEMENT
        assert context.contract.purchase_method == PurchaseMethod.AUCTION
        assert context.contract.use_category is None
        assert context.document["id"] == "doc-123"
        assert context.document["australian_state"] == "NSW"
        assert context.ocr["purchase_method_confidence"] == 0.92
        assert context.ocr["use_category_confidence"] is None

    def test_create_lease_agreement_context(self):
        """Test creating context for lease agreement"""
        context = ContractAnalysisContext.create_context(
            contract_type=ContractType.LEASE_AGREEMENT,
            use_category=UseCategory.COMMERCIAL,
            document_id="doc-456",
            australian_state=AustralianState.VIC,
            use_category_confidence=0.85,
        )

        assert context.contract.contract_type == ContractType.LEASE_AGREEMENT
        assert context.contract.purchase_method is None
        assert context.contract.use_category == UseCategory.COMMERCIAL
        assert context.document["id"] == "doc-456"
        assert context.document["australian_state"] == "VIC"
        assert context.ocr["purchase_method_confidence"] is None
        assert context.ocr["use_category_confidence"] == 0.85

    def test_create_option_to_purchase_context(self):
        """Test creating context for option to purchase"""
        context = ContractAnalysisContext.create_context(
            contract_type=ContractType.OPTION_TO_PURCHASE,
            document_id="doc-789",
            australian_state=AustralianState.QLD,
        )

        assert context.contract.contract_type == ContractType.OPTION_TO_PURCHASE
        assert context.contract.purchase_method is None
        assert context.contract.use_category is None
        assert context.document["id"] == "doc-789"
        assert context.document["australian_state"] == "QLD"
        assert context.ocr["purchase_method_confidence"] is None
        assert context.ocr["use_category_confidence"] is None

    def test_context_serialization(self):
        """Test context can be serialized and deserialized"""
        context = ContractAnalysisContext.create_context(
            contract_type=ContractType.PURCHASE_AGREEMENT,
            purchase_method=PurchaseMethod.OFF_PLAN,
            document_id="doc-test",
            australian_state=AustralianState.WA,
            purchase_method_confidence=0.88,
        )

        # Test model_dump (serialization)
        serialized = context.model_dump()

        assert isinstance(serialized, dict)
        assert serialized["contract"]["contract_type"] == "purchase_agreement"
        assert serialized["contract"]["purchase_method"] == "off_plan"
        assert serialized["ocr"]["purchase_method_confidence"] == 0.88

        # Test deserialization
        new_context = ContractAnalysisContext.model_validate(serialized)
        assert new_context.contract.contract_type == ContractType.PURCHASE_AGREEMENT
        assert new_context.contract.purchase_method == PurchaseMethod.OFF_PLAN


@pytest.mark.integration
class TestTaxonomyIntegration:
    """Integration tests for the complete taxonomy system"""

    def test_end_to_end_purchase_agreement_workflow(self):
        """Test complete workflow for purchase agreement with auction inference"""
        # This would test the full workflow from document upload to analysis
        # with contract type taxonomy inference
        pass

    def test_end_to_end_lease_agreement_workflow(self):
        """Test complete workflow for lease agreement with category inference"""
        # This would test the full workflow for lease agreements
        pass

    def test_routing_based_on_taxonomy(self):
        """Test that analysis routing works correctly based on inferred taxonomy"""
        # Test that different prompts/analysis paths are used based on
        # contract_type, purchase_method, and use_category
        pass
