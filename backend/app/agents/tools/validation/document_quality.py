"""
Document quality validation tools
"""

from typing import Dict, Any
from langchain.tools import tool
import re

from app.prompts.schema.workflow_outputs import DocumentQualityMetrics


@tool
def validate_document_quality(
    document_text: str, document_metadata: Dict[str, Any]
) -> DocumentQualityMetrics:
    """
    Comprehensive document quality assessment for contract analysis

    Args:
        document_text: Extracted text from the document
        document_metadata: Metadata about document extraction process

    Returns:
        DocumentQualityMetrics with detailed quality assessment
    """

    if not document_text or len(document_text.strip()) < 50:
        return DocumentQualityMetrics(
            text_quality_score=0.0,
            completeness_score=0.0,
            readability_score=0.0,
            key_terms_coverage=0.0,
            extraction_confidence=0.0,
            issues_identified=["Document text is too short or empty"],
            improvement_suggestions=[
                "Verify document was properly extracted",
                "Check document format and quality",
            ],
        )

    # Calculate text quality metrics
    text_quality = _assess_text_quality(document_text)
    completeness = _assess_document_completeness(document_text)
    readability = _assess_readability(document_text)
    key_terms_coverage = _assess_key_terms_coverage(document_text)

    # Extract confidence from metadata
    extraction_confidence = document_metadata.get("extraction_confidence", 0.5)

    # Identify issues
    issues = []
    suggestions = []

    if text_quality < 0.7:
        issues.append("Poor text quality - possible OCR issues")
        suggestions.append("Consider re-scanning document at higher resolution")

    if completeness < 0.8:
        issues.append("Document appears incomplete")
        suggestions.append("Verify all pages were captured and processed")

    if readability < 0.6:
        issues.append("Document text is difficult to parse")
        suggestions.append("Manual review may be required for accurate analysis")

    if key_terms_coverage < 0.5:
        issues.append("Few contract-specific terms found")
        suggestions.append("Verify this is a property contract document")

    return DocumentQualityMetrics(
        text_quality_score=text_quality,
        completeness_score=completeness,
        readability_score=readability,
        key_terms_coverage=key_terms_coverage,
        extraction_confidence=extraction_confidence,
        issues_identified=issues,
        improvement_suggestions=suggestions,
    )


def _assess_text_quality(text: str) -> float:
    """Assess the quality of extracted text"""
    if not text:
        return 0.0

    score = 1.0

    # Check for garbled characters
    garbled_ratio = len(re.findall(r"[^\w\s.,;:!?()-]", text)) / len(text)
    if garbled_ratio > 0.1:
        score -= garbled_ratio

    # Check for proper sentence structure
    sentences = re.split(r"[.!?]+", text)
    valid_sentences = [
        s for s in sentences if len(s.split()) > 3 and len(s.split()) < 100
    ]
    sentence_ratio = len(valid_sentences) / max(1, len(sentences))
    score *= sentence_ratio

    return max(0.0, min(1.0, score))


def _assess_document_completeness(text: str) -> float:
    """Assess document completeness based on expected sections"""
    text_lower = text.lower()

    # Expected sections in a property contract
    expected_sections = [
        ["vendor", "seller"],
        ["purchaser", "buyer"],
        ["property", "land", "premises"],
        ["price", "consideration", "amount"],
        ["settlement", "completion"],
        ["conditions", "terms"],
    ]

    sections_found = 0
    for section_terms in expected_sections:
        if any(term in text_lower for term in section_terms):
            sections_found += 1

    return sections_found / len(expected_sections)


def _assess_readability(text: str) -> float:
    """Assess text readability and structure"""
    if not text:
        return 0.0

    # Calculate basic readability metrics
    sentences = re.split(r"[.!?]+", text)
    words = text.split()

    if not sentences or not words:
        return 0.0

    avg_sentence_length = len(words) / len(sentences)

    # Ideal sentence length for contracts: 15-25 words
    if 15 <= avg_sentence_length <= 25:
        sentence_score = 1.0
    elif avg_sentence_length < 15:
        sentence_score = avg_sentence_length / 15
    else:
        sentence_score = max(0.3, 25 / avg_sentence_length)

    # Check for proper capitalization
    capitalized_sentences = [
        s for s in sentences if s.strip() and s.strip()[0].isupper()
    ]
    capitalization_score = len(capitalized_sentences) / max(1, len(sentences))

    return (sentence_score + capitalization_score) / 2


def _assess_key_terms_coverage(text: str) -> float:
    """Assess coverage of key contract terms"""
    text_lower = text.lower()

    # Key terms expected in property contracts
    key_terms = [
        "contract",
        "agreement",
        "purchase",
        "sale",
        "property",
        "vendor",
        "purchaser",
        "buyer",
        "seller",
        "settlement",
        "deposit",
        "price",
        "completion",
        "title",
        "transfer",
        "conditions",
        "warranties",
        "disclosure",
        "inspection",
    ]

    terms_found = sum(1 for term in key_terms if term in text_lower)

    return terms_found / len(key_terms)
