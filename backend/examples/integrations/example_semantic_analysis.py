"""
Example usage of the extract_image_semantics method in GeminiOCRService
Demonstrates how to analyze property diagrams for semantic meaning and risk assessment
"""

import asyncio
from app.services.gemini_ocr_service import GeminiOCRService
from app.prompts.schema.diagram_analysis.image_semantics_schema import DiagramType
from app.agents.states.contract_state import AustralianState, ContractType


class SemanticAnalysisExample:
    """Example class demonstrating image semantic analysis"""

    def __init__(self):
        self.ocr_service = GeminiOCRService()

    async def setup(self):
        """Initialize the OCR service"""
        await self.ocr_service.initialize()

    async def analyze_sewer_diagram(self, image_path: str):
        """
        Example: Analyzing a sewer service diagram

        This example shows how to extract semantic meaning from a sewer diagram,
        focusing on infrastructure elements like pipe locations, depths, and
        impact on property development.
        """
        print("=== Sewer Service Diagram Analysis ===")

        # Read the image file
        with open(image_path, "rb") as file:
            file_content = file.read()

        # Contract context for NSW property purchase
        contract_context = {
            "australian_state": AustralianState.NSW,
            "contract_type": ContractType.PURCHASE_AGREEMENT,
            "property_type": "residential",
            "document_type": "sewer_service_diagram",
        }

        # Perform semantic analysis
        result = await self.ocr_service.extract_image_semantics(
            file_content=file_content,
            file_type="jpg",  # or png, pdf, etc.
            filename="sewer_service_plan.jpg",
            image_type=DiagramType.SEWER_SERVICE_DIAGRAM,
            contract_context=contract_context,
            analysis_focus="infrastructure",  # Focus on infrastructure elements
            risk_categories=["infrastructure", "construction", "access"],
        )

        # Display results
        self._print_analysis_results(result, "Sewer Service Diagram")

        return result

    async def analyze_site_plan(self, image_path: str):
        """
        Example: Analyzing a site plan

        This example shows comprehensive analysis of a site plan including
        boundaries, buildings, access, and development constraints.
        """
        print("\n=== Site Plan Analysis ===")

        with open(image_path, "rb") as file:
            file_content = file.read()

        contract_context = {
            "australian_state": AustralianState.VIC,
            "contract_type": ContractType.PURCHASE_AGREEMENT,
            "property_type": "residential",
            "document_type": "site_plan",
        }

        result = await self.ocr_service.extract_image_semantics(
            file_content=file_content,
            file_type="pdf",
            filename="site_plan.pdf",
            image_type=DiagramType.SITE_PLAN,
            contract_context=contract_context,
            analysis_focus="comprehensive",  # Comprehensive analysis
            risk_categories=["boundaries", "access", "development", "compliance"],
        )

        self._print_analysis_results(result, "Site Plan")
        return result

    async def analyze_flood_map(self, image_path: str):
        """
        Example: Analyzing a flood risk map

        This example focuses on environmental risks, specifically flood zones
        and their impact on property development and insurance.
        """
        print("\n=== Flood Map Analysis ===")

        with open(image_path, "rb") as file:
            file_content = file.read()

        contract_context = {
            "australian_state": AustralianState.QLD,
            "contract_type": ContractType.PURCHASE_AGREEMENT,
            "property_type": "residential",
            "document_type": "flood_map",
        }

        result = await self.ocr_service.extract_image_semantics(
            file_content=file_content,
            file_type="png",
            filename="flood_risk_map.png",
            image_type=DiagramType.FLOOD_MAP,
            contract_context=contract_context,
            analysis_focus="environmental",  # Focus on environmental risks
            risk_categories=["environmental", "insurance", "development"],
        )

        self._print_analysis_results(result, "Flood Map")
        return result

    async def analyze_unknown_diagram(self, image_path: str):
        """
        Example: Auto-detecting image type and analyzing

        This example shows how the service can auto-detect image types
        and perform appropriate analysis.
        """
        print("\n=== Auto-Detected Diagram Analysis ===")

        with open(image_path, "rb") as file:
            file_content = file.read()

        contract_context = {
            "australian_state": AustralianState.NSW,
            "contract_type": ContractType.PURCHASE_AGREEMENT,
            "property_type": "residential",
        }

        # Don't specify image_type - let the service auto-detect
        result = await self.ocr_service.extract_image_semantics(
            file_content=file_content,
            file_type="jpg",
            filename="property_diagram.jpg",  # Filename used for auto-detection
            image_type=None,  # Auto-detect
            contract_context=contract_context,
            analysis_focus="comprehensive",
        )

        detected_type = result.get("image_type_detected", "unknown")
        print(f"Auto-detected image type: {detected_type}")

        self._print_analysis_results(result, "Auto-Detected Diagram")
        return result

    def _print_analysis_results(self, result: dict, analysis_type: str):
        """Helper method to print analysis results in a readable format"""
        print(f"\n--- {analysis_type} Results ---")

        # Service information
        print(f"Service: {result.get('service', 'Unknown')}")
        print(f"Version: {result.get('service_version', 'Unknown')}")
        print(f"File: {result.get('file_processed', 'Unknown')}")
        print(f"Analysis Focus: {result.get('analysis_focus', 'Unknown')}")

        semantic_analysis = result.get("semantic_analysis")
        if semantic_analysis:
            print(f"\n📊 Semantic Summary:")
            print(
                f"   {semantic_analysis.get('semantic_summary', 'No summary available')}"
            )

            print(f"\n🏠 Property Impact:")
            print(
                f"   {semantic_analysis.get('property_impact_summary', 'No impact summary available')}"
            )

            # Key findings
            key_findings = semantic_analysis.get("key_findings", [])
            if key_findings:
                print(f"\n🔍 Key Findings:")
                for i, finding in enumerate(key_findings, 1):
                    print(f"   {i}. {finding}")

            # Areas of concern
            concerns = semantic_analysis.get("areas_of_concern", [])
            if concerns:
                print(f"\n⚠️  Areas of Concern:")
                for i, concern in enumerate(concerns, 1):
                    print(f"   {i}. {concern}")

            # Infrastructure elements
            infrastructure = semantic_analysis.get("infrastructure_elements", [])
            if infrastructure:
                print(f"\n🏗️  Infrastructure Elements ({len(infrastructure)}):")
                for elem in infrastructure[:3]:  # Show first 3
                    print(
                        f"   • {elem.get('element_type', 'Unknown')}: {elem.get('description', 'No description')}"
                    )
                if len(infrastructure) > 3:
                    print(f"   ... and {len(infrastructure) - 3} more")

            # Areas of concern surface potential risks at semantics stage
            risks = semantic_analysis.get("areas_of_concern", [])
            if risks:
                print(f"\n🚨 Areas of Concern ({len(risks)}):")
                for risk in risks[:3]:  # Show first 3
                    print(f"   • {risk}")
                if len(risks) > 3:
                    print(f"   ... and {len(risks) - 3} more")

            # Suggested follow-up
            followup = semantic_analysis.get("suggested_followup", [])
            if followup:
                print(f"\n📋 Suggested Follow-up:")
                for i, action in enumerate(followup, 1):
                    print(f"   {i}. {action}")

            print(
                f"\n✅ Analysis Confidence: {semantic_analysis.get('analysis_confidence', 'Unknown')}"
            )

        # Error handling
        if result.get("error"):
            print(f"\n❌ Error: {result['error']}")
            print(f"   Error Type: {result.get('error_type', 'Unknown')}")

        print("-" * 60)


# Example usage scenarios
async def run_examples():
    """Run all semantic analysis examples"""

    example = SemanticAnalysisExample()
    await example.setup()

    print("🔍 Image Semantic Analysis Examples")
    print("=" * 60)

    # Example file paths (these would be real files in practice)
    example_files = {
        "sewer_diagram": "path/to/sewer_service_diagram.jpg",
        "site_plan": "path/to/site_plan.pdf",
        "flood_map": "path/to/flood_map.png",
        "unknown_diagram": "path/to/property_diagram.jpg",
    }

    try:
        # Example 1: Sewer diagram analysis
        print("Example 1: Analyzing sewer service diagram for infrastructure risks...")
        # await example.analyze_sewer_diagram(example_files["sewer_diagram"])
        print("   (Skipped - no sample file provided)")

        # Example 2: Site plan analysis
        print("\nExample 2: Comprehensive site plan analysis...")
        # await example.analyze_site_plan(example_files["site_plan"])
        print("   (Skipped - no sample file provided)")

        # Example 3: Flood map analysis
        print("\nExample 3: Environmental risk analysis from flood map...")
        # await example.analyze_flood_map(example_files["flood_map"])
        print("   (Skipped - no sample file provided)")

        # Example 4: Auto-detection
        print("\nExample 4: Auto-detecting diagram type...")
        # await example.analyze_unknown_diagram(example_files["unknown_diagram"])
        print("   (Skipped - no sample file provided)")

        print("\n✅ All examples completed successfully!")
        print("\nTo run with real files:")
        print("1. Place image files in the specified paths")
        print("2. Update the file paths in example_files dictionary")
        print("3. Uncomment the await statements")

    except Exception as e:
        print(f"\n❌ Example failed: {str(e)}")


# Test scenarios for different use cases
class SemanticAnalysisTestScenarios:
    """Test scenarios for semantic analysis functionality"""

    @staticmethod
    def create_sewer_diagram_test_case():
        """Test case for sewer diagram analysis"""
        return {
            "name": "Sewer Main Under Property",
            "description": "225mm concrete sewer main running east-west under building envelope",
            "expected_elements": [
                {
                    "type": "sewer_pipe",
                    "properties": ["diameter", "depth", "material", "ownership"],
                    "risks": ["construction_impact", "access_requirements"],
                }
            ],
            "expected_risks": [
                {
                    "type": "Construction Impact",
                    "severity": "medium",
                    "evidence": "sewer_main_location",
                }
            ],
            "key_assertions": [
                "Infrastructure elements should be identified",
                "Building envelope impact should be assessed",
                "Maintenance access requirements should be noted",
                "Foundation design implications should be flagged",
            ],
        }

    @staticmethod
    def create_flood_map_test_case():
        """Test case for flood map analysis"""
        return {
            "name": "Property in 1:100 Year Flood Zone",
            "description": "Property partially affected by 1 in 100 year flood event",
            "expected_elements": [
                {
                    "type": "flood_zone",
                    "properties": ["flood_level", "probability", "affected_area"],
                    "risks": ["insurance_impact", "building_restrictions"],
                }
            ],
            "expected_risks": [
                {
                    "type": "Flood Risk",
                    "severity": "high",
                    "evidence": "flood_zone_boundary",
                }
            ],
            "key_assertions": [
                "Flood zone boundaries should be identified",
                "Building restrictions should be noted",
                "Insurance implications should be flagged",
                "Development constraints should be assessed",
            ],
        }


if __name__ == "__main__":
    # Run the examples
    asyncio.run(run_examples())
