"""
Example: Using the Unified Artifact System

This example demonstrates how workflows can be updated to use the unified
artifact storage system, eliminating duplication and providing a single
interface for the main contract analysis workflow.
"""

from typing import Dict, Any, List
from app.services.repositories.artifacts_repository import ArtifactsRepository


class UnifiedWorkflowExample:
    """
    Example showing how workflows use the unified artifact system.
    """
    
    def __init__(self):
        self.artifacts_repo = ArtifactsRepository()
    
    async def main_workflow_example(
        self, 
        content_hmac: str, 
        page_data: List[Dict[str, Any]]
    ):
        """
        Example: Main document processing workflow using unified storage.
        
        Before: Used separate insert_page_artifact() and insert_diagram_artifact()
        After: Uses unified methods with type discrimination
        """
        
        # Store text pages with layout information
        for page in page_data:
            await self.artifacts_repo.insert_unified_page_artifact(
                content_hmac=content_hmac,
                algorithm_version=1,
                params_fingerprint="main_workflow_v1",
                page_number=page["page_number"],
                page_text_uri=page["text_uri"],
                page_text_sha256=page["text_hash"],
                content_type="text",  # Traditional text processing
                layout=page["layout_data"],  # PyMuPDF layout
                metrics={
                    "word_count": page["word_count"],
                    "confidence": page["extraction_confidence"]
                }
            )
        
        # Store extracted diagrams  
        for diagram in page_data:
            if diagram.get("diagrams"):
                for diag in diagram["diagrams"]:
                    await self.artifacts_repo.insert_unified_visual_artifact(
                        content_hmac=content_hmac,
                        algorithm_version=1,
                        params_fingerprint="main_workflow_v1",
                        page_number=diagram["page_number"],
                        diagram_key=diag["diagram_key"],
                        artifact_type="diagram",  # Traditional diagram
                        diagram_meta={
                            "type": diag["diagram_type"],
                            "confidence": diag["confidence"],
                            "extraction_method": "main_workflow"
                        }
                    )

    async def external_ocr_workflow_example(
        self, 
        content_hmac: str, 
        ocr_files: List[Dict[str, Any]]
    ):
        """
        Example: External OCR workflow using unified storage.
        
        Before: Used separate insert_page_jpg_artifact() and insert_page_json_artifact()
        After: Uses unified methods with type discrimination
        """
        
        for ocr_file in ocr_files:
            page_number = ocr_file["page_number"]
            
            # Store JPG page image as visual artifact
            if ocr_file.get("jpg_uri"):
                await self.artifacts_repo.insert_unified_visual_artifact(
                    content_hmac=content_hmac,
                    algorithm_version=1,
                    params_fingerprint="external_ocr_v1",
                    page_number=page_number,
                    diagram_key=f"page_image_{page_number}",
                    artifact_type="image_jpg",  # External OCR image
                    image_uri=ocr_file["jpg_uri"],
                    image_sha256=ocr_file["jpg_hash"],
                    image_metadata={
                        "source": "external_ocr",
                        "width": ocr_file.get("width"),
                        "height": ocr_file.get("height")
                    }
                )
            
            # Store JSON metadata as page artifact
            if ocr_file.get("json_uri"):
                await self.artifacts_repo.insert_unified_page_artifact(
                    content_hmac=content_hmac,
                    algorithm_version=1,
                    params_fingerprint="external_ocr_v1",
                    page_number=page_number,
                    page_text_uri=ocr_file["json_uri"],
                    page_text_sha256=ocr_file["json_hash"],
                    content_type="json_metadata",  # External OCR metadata
                    metrics=ocr_file.get("stats", {})
                )
            
            # Store markdown content as page artifact
            if ocr_file.get("markdown_uri"):
                await self.artifacts_repo.insert_unified_page_artifact(
                    content_hmac=content_hmac,
                    algorithm_version=1,
                    params_fingerprint="external_ocr_v1",
                    page_number=page_number,
                    page_text_uri=ocr_file["markdown_uri"],
                    page_text_sha256=ocr_file["markdown_hash"],
                    content_type="markdown",  # External OCR markdown
                    metrics={
                        "word_count": ocr_file.get("word_count", 0),
                        "extraction_method": "external_ocr"
                    }
                )

    async def contract_analysis_workflow_example(self, content_hmac: str):
        """
        Example: Main contract analysis workflow using unified retrieval.
        
        Before: Had to check multiple tables and understand workflow differences
        After: Single interface gets all artifacts regardless of source
        """
        
        # Get comprehensive summary of what's available
        summary = await self.artifacts_repo.get_document_processing_summary(
            content_hmac=content_hmac,
            algorithm_version=1,
            params_fingerprint="any"  # Gets artifacts from any workflow
        )
        
        print(f"Document processed by workflows: {summary['processing_workflows']}")
        print(f"Total pages available: {summary['page_artifacts']['total_pages']}")
        print(f"Total visual artifacts: {summary['visual_artifacts']['total_visuals']}")
        
        # Get all page content (text, markdown, JSON metadata)
        all_pages = await self.artifacts_repo.get_all_page_artifacts(
            content_hmac=content_hmac,
            algorithm_version=1,
            params_fingerprint="any"
        )
        
        # Separate by content type for different processing
        text_pages = [p for p in all_pages if p.content_type == "text"]
        markdown_pages = [p for p in all_pages if p.content_type == "markdown"]
        metadata_pages = [p for p in all_pages if p.content_type == "json_metadata"]
        
        print(f"Found {len(text_pages)} text pages, {len(markdown_pages)} markdown pages, {len(metadata_pages)} metadata pages")
        
        # Get all visual content (diagrams and images)
        all_visuals = await self.artifacts_repo.get_all_visual_artifacts(
            content_hmac=content_hmac,
            algorithm_version=1,
            params_fingerprint="any"
        )
        
        # Separate by artifact type for different processing
        diagrams = [v for v in all_visuals if v.artifact_type == "diagram"]
        jpg_images = [v for v in all_visuals if v.artifact_type == "image_jpg"]
        
        print(f"Found {len(diagrams)} diagrams, {len(jpg_images)} JPG images")
        
        # Contract analysis can now process all available content
        # without needing to understand which workflow created what
        
        return {
            "summary": summary,
            "content": {
                "text_pages": len(text_pages),
                "markdown_pages": len(markdown_pages),
                "metadata_pages": len(metadata_pages),
                "diagrams": len(diagrams),
                "images": len(jpg_images)
            },
            "total_artifacts": len(all_pages) + len(all_visuals)
        }

    async def intelligent_artifact_selection_example(self, content_hmac: str):
        """
        Example: Intelligent artifact selection based on quality and availability.
        
        The unified system enables smart selection of the best available artifacts
        for contract analysis without workflow-specific logic.
        """
        
        # Get summary to understand what's available
        summary = await self.artifacts_repo.get_document_processing_summary(
            content_hmac=content_hmac,
            algorithm_version=1,
            params_fingerprint="any"
        )
        
        # Intelligent selection logic
        selected_artifacts = {
            "text_source": None,
            "visual_source": None,
            "rationale": []
        }
        
        # Prefer markdown over text if available (better structure)
        if summary["page_artifacts"]["by_type"]["markdown"] > 0:
            selected_artifacts["text_source"] = "markdown"
            selected_artifacts["rationale"].append("Using markdown for better structure")
        elif summary["page_artifacts"]["by_type"]["text"] > 0:
            selected_artifacts["text_source"] = "text"
            selected_artifacts["rationale"].append("Using extracted text")
        
        # Prefer diagrams over images for analysis (already processed)
        if summary["visual_artifacts"]["by_type"]["diagrams"] > 0:
            selected_artifacts["visual_source"] = "diagrams"
            selected_artifacts["rationale"].append("Using processed diagrams")
        elif summary["visual_artifacts"]["by_type"]["jpg_images"] > 0:
            selected_artifacts["visual_source"] = "jpg_images"
            selected_artifacts["rationale"].append("Using raw page images")
        
        # Get the selected artifacts
        if selected_artifacts["text_source"]:
            pages = await self.artifacts_repo.get_all_page_artifacts(
                content_hmac, 1, "any"
            )
            text_artifacts = [
                p for p in pages 
                if p.content_type == selected_artifacts["text_source"]
            ]
        
        if selected_artifacts["visual_source"]:
            visuals = await self.artifacts_repo.get_all_visual_artifacts(
                content_hmac, 1, "any"
            )
            if selected_artifacts["visual_source"] == "diagrams":
                visual_artifacts = [v for v in visuals if v.artifact_type == "diagram"]
            else:
                visual_artifacts = [v for v in visuals if v.artifact_type == "image_jpg"]
        
        return {
            "selection": selected_artifacts,
            "workflows_detected": summary["processing_workflows"],
            "artifacts_selected": {
                "text_count": len(text_artifacts) if selected_artifacts["text_source"] else 0,
                "visual_count": len(visual_artifacts) if selected_artifacts["visual_source"] else 0
            }
        }


# Usage Examples
async def example_usage():
    """Demonstrate the unified artifact system in action."""
    
    example = UnifiedWorkflowExample()
    content_hmac = "abc123def456..."  # Example content hash
    
    # Simulate main workflow processing
    main_workflow_data = [
        {
            "page_number": 1,
            "text_uri": "supabase://documents/page1.txt",
            "text_hash": "hash1...",
            "word_count": 500,
            "extraction_confidence": 0.95,
            "layout_data": {"columns": 2, "paragraphs": 10},
            "diagrams": [
                {
                    "diagram_key": "site_plan_1",
                    "diagram_type": "site_plan",
                    "confidence": 0.88
                }
            ]
        }
    ]
    
    await example.main_workflow_example(content_hmac, main_workflow_data)
    
    # Simulate external OCR processing
    external_ocr_data = [
        {
            "page_number": 1,
            "jpg_uri": "supabase://documents/page1.jpg",
            "jpg_hash": "jpg_hash1...",
            "json_uri": "supabase://documents/page1_metadata.json",
            "json_hash": "json_hash1...",
            "markdown_uri": "supabase://documents/page1.md",
            "markdown_hash": "md_hash1...",
            "width": 1200,
            "height": 800,
            "word_count": 510,
            "stats": {"confidence": 0.92, "processing_time": 2.5}
        }
    ]
    
    await example.external_ocr_workflow_example(content_hmac, external_ocr_data)
    
    # Contract analysis can now access everything through unified interface
    analysis_result = await example.contract_analysis_workflow_example(content_hmac)
    print("Contract Analysis Result:", analysis_result)
    
    # Intelligent selection chooses the best available artifacts
    selection_result = await example.intelligent_artifact_selection_example(content_hmac)
    print("Intelligent Selection Result:", selection_result)


if __name__ == "__main__":
    import asyncio
    asyncio.run(example_usage())