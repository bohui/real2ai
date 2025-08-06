"""
API endpoints for semantic analysis workflows
Provides REST API access to image semantic analysis capabilities
"""

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from fastapi.responses import JSONResponse
from typing import Dict, Any, List, Optional
import logging
import uuid
from datetime import datetime, UTC

from app.services.semantic_analysis_service import SemanticAnalysisService
from app.services.document_service import DocumentService
from app.models.contract_state import AustralianState, ContractType
from app.prompts.schema.image_semantics_schema import ImageType
from app.core.config import get_settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/semantic-analysis", tags=["semantic-analysis"])


# Service dependencies
async def get_semantic_analysis_service():
    """Get initialized semantic analysis service"""
    service = SemanticAnalysisService()
    await service.initialize()
    return service


async def get_document_service():
    """Get initialized document service"""
    service = DocumentService()
    await service.initialize()
    return service


@router.post("/analyze-document")
async def analyze_document_semantics(
    file: UploadFile = File(...),
    australian_state: str = Form(...),
    contract_type: str = Form(...),
    user_type: str = Form(default="buyer"),
    analysis_focus: str = Form(default="comprehensive"),
    risk_categories: str = Form(default=""),
    user_experience_level: str = Form(default="novice"),
    image_type: Optional[str] = Form(default=None),
    semantic_service: SemanticAnalysisService = Depends(get_semantic_analysis_service),
    document_service: DocumentService = Depends(get_document_service),
):
    """
    Analyze a single document/image for semantic meaning and property risks
    
    **Parameters:**
    - **file**: Image or PDF file to analyze
    - **australian_state**: Australian state (NSW, VIC, QLD, etc.)
    - **contract_type**: Contract type (PURCHASE_AGREEMENT, LEASE_AGREEMENT)
    - **user_type**: User role (buyer, seller, investor, etc.)
    - **analysis_focus**: Focus area (infrastructure, environmental, boundaries, comprehensive)
    - **risk_categories**: Comma-separated risk categories to focus on
    - **user_experience_level**: User experience (novice, intermediate, expert)
    - **image_type**: Optional image type hint (sewer_service_diagram, site_plan, etc.)
    
    **Returns:**
    - Comprehensive semantic analysis with risks and recommendations
    
    **Example Usage:**
    ```bash
    curl -X POST "http://localhost:8000/api/v1/semantic-analysis/analyze-document" \
         -F "file=@sewer_service_plan.jpg" \
         -F "australian_state=NSW" \
         -F "contract_type=PURCHASE_AGREEMENT" \
         -F "analysis_focus=infrastructure"
    ```
    """
    if not file:
        raise HTTPException(status_code=400, detail="No file provided")

    try:
        # Validate parameters
        try:
            state = AustralianState(australian_state.upper())
            contract_type_enum = ContractType(contract_type.upper())
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Invalid parameter: {str(e)}")

        # Parse risk categories
        risk_categories_list = (
            [cat.strip() for cat in risk_categories.split(",")]
            if risk_categories
            else []
        )

        # Parse image type if provided
        image_type_enum = None
        if image_type:
            try:
                image_type_enum = ImageType(image_type.upper())
            except ValueError:
                logger.warning(
                    f"Invalid image type provided: {image_type}, will auto-detect"
                )

        # Generate unique document ID for tracking
        document_id = str(uuid.uuid4())

        # Upload file to storage first
        upload_result = await document_service.upload_file(
            file=file,
            user_id="api_user",  # In real implementation, get from authentication
            contract_type=contract_type_enum,
        )

        storage_path = upload_result["storage_path"]
        filename = upload_result["original_filename"]
        file_type = (
            upload_result["content_type"].split("/")[-1]
            if upload_result.get("content_type")
            else "unknown"
        )

        # Prepare contract context
        contract_context = {
            "australian_state": state,
            "contract_type": contract_type_enum,
            "user_type": user_type,
            "user_experience_level": user_experience_level,
            "document_type": image_type or "diagram",
            "analysis_timestamp": datetime.now(UTC).isoformat(),
        }

        # Prepare analysis options
        analysis_options = {
            "analysis_focus": analysis_focus,
            "risk_categories": risk_categories_list,
        }

        # Perform semantic analysis
        result = await semantic_service.analyze_document_semantics(
            storage_path=storage_path,
            file_type=file_type,
            filename=filename,
            contract_context=contract_context,
            analysis_options=analysis_options,
            document_id=document_id,
        )

        # Add API metadata
        result["api_metadata"] = {
            "endpoint": "/analyze-document",
            "document_id": document_id,
            "upload_info": {
                "original_filename": filename,
                "file_size": upload_result["file_size"],
                "storage_path": storage_path,
            },
            "request_parameters": {
                "australian_state": state.value,
                "contract_type": contract_type_enum.value,
                "analysis_focus": analysis_focus,
                "risk_categories": risk_categories_list,
            },
        }

        return JSONResponse(content=result)

    except Exception as e:
        logger.error(f"Document semantic analysis failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@router.post("/analyze-contract-diagrams")
async def analyze_contract_diagrams(
    files: List[UploadFile] = File(...),
    australian_state: str = Form(...),
    contract_type: str = Form(...),
    property_address: Optional[str] = Form(default=None),
    user_type: str = Form(default="buyer"),
    user_experience_level: str = Form(default="novice"),
    document_service: DocumentService = Depends(get_document_service),
):
    """
    Analyze multiple diagrams from a property contract
    
    **Parameters:**
    - **files**: Multiple image/PDF files representing property diagrams
    - **australian_state**: Australian state (NSW, VIC, QLD, etc.)
    - **contract_type**: Contract type (PURCHASE_AGREEMENT, LEASE_AGREEMENT)
    - **property_address**: Optional property address for context
    - **user_type**: User role (buyer, seller, investor, etc.)
    - **user_experience_level**: User experience (novice, intermediate, expert)
    
    **Returns:**
    - Consolidated analysis of all contract diagrams with integrated risk assessment
    
    **Example Usage:**
    ```bash
    curl -X POST "http://localhost:8000/api/v1/semantic-analysis/analyze-contract-diagrams" \
         -F "files=@sewer_plan.jpg" \
         -F "files=@site_plan.pdf" \
         -F "files=@flood_map.png" \
         -F "australian_state=NSW" \
         -F "contract_type=PURCHASE_AGREEMENT" \
         -F "property_address=123 Main St, Sydney NSW 2000"
    ```
    """
    if not files or len(files) == 0:
        raise HTTPException(status_code=400, detail="No files provided")

    if len(files) > 10:  # Reasonable limit
        raise HTTPException(
            status_code=400, detail="Too many files provided (maximum 10)"
        )

    try:
        # Validate parameters
        try:
            state = AustralianState(australian_state.upper())
            contract_type_enum = ContractType(contract_type.upper())
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Invalid parameter: {str(e)}")

        # Generate unique document ID for tracking
        document_id = str(uuid.uuid4())

        # Upload all files and collect storage paths
        diagram_storage_paths = []
        upload_info = []

        for i, file in enumerate(files):
            upload_result = await document_service.upload_file(
                file=file,
                user_id="api_user",  # In real implementation, get from authentication
                contract_type=contract_type_enum,
            )

            diagram_storage_paths.append(upload_result["storage_path"])
            upload_info.append(
                {
                    "index": i,
                    "original_filename": upload_result["original_filename"],
                    "file_size": upload_result["file_size"],
                    "storage_path": upload_result["storage_path"],
                }
            )

        # Prepare contract context
        contract_context = {
            "australian_state": state,
            "contract_type": contract_type_enum,
            "user_type": user_type,
            "user_experience_level": user_experience_level,
            "property_address": property_address,
            "analysis_timestamp": datetime.now(UTC).isoformat(),
            "total_diagrams": len(files),
        }

        # Perform contract diagram analysis
        result = await document_service.analyze_contract_diagrams(
            diagram_storage_paths=diagram_storage_paths,
            contract_context=contract_context,
            document_id=document_id,
        )

        # Add API metadata
        result["api_metadata"] = {
            "endpoint": "/analyze-contract-diagrams",
            "document_id": document_id,
            "upload_info": upload_info,
            "request_parameters": {
                "australian_state": state.value,
                "contract_type": contract_type_enum.value,
                "total_files": len(files),
            },
        }

        return JSONResponse(content=result)

    except Exception as e:
        logger.error(f"Contract diagram analysis failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@router.post("/process-complete-contract")
async def process_complete_contract(
    main_contract: UploadFile = File(...),
    diagram_files: List[UploadFile] = File(...),
    australian_state: str = Form(...),
    contract_type: str = Form(...),
    property_address: Optional[str] = Form(default=None),
    user_type: str = Form(default="buyer"),
    user_experience_level: str = Form(default="novice"),
    force_ocr: bool = Form(default=False),
    document_service: DocumentService = Depends(get_document_service),
):
    """
    Complete contract processing including text extraction and semantic analysis
    
    **Parameters:**
    - **main_contract**: Main contract document (PDF/Word)
    - **diagram_files**: Property diagram files (images/PDFs)
    - **australian_state**: Australian state (NSW, VIC, QLD, etc.)
    - **contract_type**: Contract type (PURCHASE_AGREEMENT, LEASE_AGREEMENT)
    - **property_address**: Optional property address for context
    - **user_type**: User role (buyer, seller, investor, etc.)
    - **user_experience_level**: User experience (novice, intermediate, expert)
    - **force_ocr**: Force OCR even for text-based documents
    
    **Returns:**
    - Complete contract analysis including text extraction, semantic analysis, and integrated recommendations
    
    **Example Usage:**
    ```bash
    curl -X POST "http://localhost:8000/api/v1/semantic-analysis/process-complete-contract" \
         -F "main_contract=@purchase_agreement.pdf" \
         -F "diagram_files=@sewer_plan.jpg" \
         -F "diagram_files=@site_plan.pdf" \
         -F "australian_state=NSW" \
         -F "contract_type=PURCHASE_AGREEMENT" \
         -F "property_address=123 Main St, Sydney NSW 2000"
    ```
    """
    if not main_contract:
        raise HTTPException(status_code=400, detail="No main contract provided")

    if not diagram_files or len(diagram_files) == 0:
        raise HTTPException(status_code=400, detail="No diagram files provided")

    try:
        # Validate parameters
        try:
            state = AustralianState(australian_state.upper())
            contract_type_enum = ContractType(contract_type.upper())
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Invalid parameter: {str(e)}")

        # Generate unique document ID for tracking
        document_id = str(uuid.uuid4())

        # Upload main contract
        main_upload = await document_service.upload_file(
            file=main_contract,
            user_id="api_user",  # In real implementation, get from authentication
            contract_type=contract_type_enum,
        )

        # Upload diagram files
        diagram_storage_paths = []
        diagram_upload_info = []

        for i, file in enumerate(diagram_files):
            upload_result = await document_service.upload_file(
                file=file, user_id="api_user", contract_type=contract_type_enum
            )

            diagram_storage_paths.append(upload_result["storage_path"])
            diagram_upload_info.append(
                {
                    "index": i,
                    "original_filename": upload_result["original_filename"],
                    "file_size": upload_result["file_size"],
                    "storage_path": upload_result["storage_path"],
                }
            )

        # Prepare contract context
        contract_context = {
            "australian_state": state,
            "contract_type": contract_type_enum,
            "user_type": user_type,
            "user_experience_level": user_experience_level,
            "property_address": property_address,
            "analysis_timestamp": datetime.now(UTC).isoformat(),
            "total_diagrams": len(diagram_files),
        }

        # Prepare processing options
        processing_options = {
            "force_ocr": force_ocr,
            "enable_semantic_analysis": True,
            "comprehensive_analysis": True,
        }

        # Perform complete contract processing
        result = await document_service.process_contract_with_semantic_analysis(
            main_document_path=main_upload["storage_path"],
            diagram_paths=diagram_storage_paths,
            contract_context=contract_context,
            document_id=document_id,
            processing_options=processing_options,
        )

        # Add API metadata
        result["api_metadata"] = {
            "endpoint": "/process-complete-contract",
            "document_id": document_id,
            "main_contract_info": {
                "original_filename": main_upload["original_filename"],
                "file_size": main_upload["file_size"],
                "storage_path": main_upload["storage_path"],
            },
            "diagram_files_info": diagram_upload_info,
            "request_parameters": {
                "australian_state": state.value,
                "contract_type": contract_type_enum.value,
                "total_diagrams": len(diagram_files),
                "force_ocr": force_ocr,
            },
        }

        return JSONResponse(content=result)

    except Exception as e:
        logger.error(f"Complete contract processing failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")


@router.get("/capabilities")
async def get_semantic_analysis_capabilities(
    semantic_service: SemanticAnalysisService = Depends(get_semantic_analysis_service),
):
    """
    Get semantic analysis service capabilities

    **Returns:**
    - Service capabilities including supported image types, analysis options, and features
    """
    try:
        capabilities = await semantic_service.get_analysis_capabilities()

        # Add API-specific information
        capabilities["api_endpoints"] = [
            {
                "endpoint": "/analyze-document",
                "description": "Analyze single document for semantic meaning",
                "method": "POST",
                "supports_upload": True,
            },
            {
                "endpoint": "/analyze-contract-diagrams",
                "description": "Analyze multiple contract diagrams",
                "method": "POST",
                "supports_multiple_files": True,
            },
            {
                "endpoint": "/process-complete-contract",
                "description": "Complete contract processing with text and semantic analysis",
                "method": "POST",
                "supports_mixed_files": True,
            },
            {
                "endpoint": "/capabilities",
                "description": "Get service capabilities",
                "method": "GET",
            },
            {"endpoint": "/health", "description": "Health check", "method": "GET"},
        ]

        capabilities["usage_examples"] = {
            "sewer_diagram_analysis": {
                "description": "Analyze sewer service diagram for infrastructure risks",
                "parameters": {
                    "analysis_focus": "infrastructure",
                    "risk_categories": "infrastructure,construction",
                    "expected_results": "Sewer pipe locations, building restrictions, access requirements",
                },
            },
            "multi_diagram_analysis": {
                "description": "Comprehensive property risk assessment from multiple diagrams",
                "parameters": {
                    "files": "sewer_plan.jpg, site_plan.pdf, flood_map.png",
                    "expected_results": "Consolidated risk assessment, professional consultation recommendations",
                },
            },
            "complete_contract_processing": {
                "description": "Full contract analysis with text extraction and semantic analysis",
                "parameters": {
                    "main_contract": "purchase_agreement.pdf",
                    "diagrams": "Multiple property diagrams",
                    "expected_results": "Integrated analysis with contract-diagram consistency checks",
                },
            },
        }

        return JSONResponse(content=capabilities)

    except Exception as e:
        logger.error(f"Failed to get capabilities: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Could not retrieve capabilities: {str(e)}"
        )


@router.get("/health")
async def health_check(
    semantic_service: SemanticAnalysisService = Depends(get_semantic_analysis_service),
):
    """
    Health check for semantic analysis service

    **Returns:**
    - Service health status and dependency information
    """
    try:
        health_status = await semantic_service.health_check()

        # Add API-specific health information
        health_status["api_status"] = "healthy"
        health_status["endpoints_available"] = [
            "/analyze-document",
            "/analyze-contract-diagrams",
            "/process-complete-contract",
            "/capabilities",
            "/health",
        ]

        return JSONResponse(content=health_status)

    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return JSONResponse(
            status_code=503,
            content={
                "service": "SemanticAnalysisAPI",
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now(UTC).isoformat(),
            },
        )


@router.get("/supported-image-types")
async def get_supported_image_types():
    """
    Get list of supported image types for semantic analysis

    **Returns:**
    - List of supported image types with descriptions
    """
    image_types = [
        {
            "type": "sewer_service_diagram",
            "description": "Sewer service connection diagrams showing pipe locations and specifications",
            "typical_risks": [
                "Infrastructure conflicts",
                "Building restrictions",
                "Access requirements",
            ],
        },
        {
            "type": "site_plan",
            "description": "Overall property site plans showing buildings, boundaries, and access",
            "typical_risks": [
                "Setback compliance",
                "Access adequacy",
                "Development constraints",
            ],
        },
        {
            "type": "flood_map",
            "description": "Flood risk maps showing flood zones and water flow patterns",
            "typical_risks": [
                "Flood damage",
                "Insurance implications",
                "Building restrictions",
            ],
        },
        {
            "type": "survey_diagram",
            "description": "Property survey diagrams with boundaries and measurements",
            "typical_risks": [
                "Boundary disputes",
                "Encroachments",
                "Area discrepancies",
            ],
        },
        {
            "type": "bushfire_map",
            "description": "Bushfire risk maps showing fire hazard areas",
            "typical_risks": [
                "Fire damage",
                "Building standards",
                "Insurance requirements",
            ],
        },
        {
            "type": "zoning_map",
            "description": "Planning and zoning maps showing land use restrictions",
            "typical_risks": [
                "Development restrictions",
                "Height limits",
                "Use limitations",
            ],
        },
        {
            "type": "utility_plan",
            "description": "Utility infrastructure plans showing services and connections",
            "typical_risks": [
                "Service conflicts",
                "Access requirements",
                "Connection costs",
            ],
        },
        {
            "type": "strata_plan",
            "description": "Strata development plans showing unit boundaries and common areas",
            "typical_risks": [
                "Unit boundary issues",
                "Common property disputes",
                "Body corporate fees",
            ],
        },
    ]

    return JSONResponse(
        content={
            "supported_image_types": image_types,
            "auto_detection": "Service can automatically detect image type from filename and context",
            "manual_override": "Image type can be manually specified in analysis requests",
        }
    )


# Include router in main application
# This would be added to the main FastAPI app like:
# app.include_router(semantic_analysis.router, prefix="/api/v1")
