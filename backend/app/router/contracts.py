"""Contract analysis router."""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from fastapi.responses import JSONResponse
import logging

from app.core.auth import get_current_user, User
from app.core.database import get_database_client
from app.schema.contract import ContractAnalysisRequest, ContractAnalysisResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/contracts", tags=["contracts"])


@router.post("/analyze", response_model=ContractAnalysisResponse)
async def start_contract_analysis(
    request: ContractAnalysisRequest,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    db_client=Depends(get_database_client),
):
    """Start contract analysis"""

    try:
        # Ensure database client is initialized
        if not hasattr(db_client, '_client') or db_client._client is None:
            await db_client.initialize()
            
        # Check user credits
        if user.credits_remaining <= 0 and user.subscription_status == "free":
            raise HTTPException(
                status_code=402,
                detail="No credits remaining. Please upgrade your subscription.",
            )

        # Get document
        doc_result = (
            db_client.table("documents")
            .select("*")
            .eq("id", request.document_id)
            .eq("user_id", user.id)
            .execute()
        )

        if not doc_result.data:
            raise HTTPException(status_code=404, detail="Document not found")

        document = doc_result.data[0]

        # Create contract record
        contract_data = {
            "document_id": request.document_id,
            "contract_type": document.get("contract_type", "purchase_agreement"),
            "australian_state": user.australian_state,
            "user_id": user.id,
        }

        contract_result = (
            db_client.table("contracts").insert(contract_data).execute()
        )
        contract_id = contract_result.data[0]["id"]

        # Create analysis record
        analysis_data = {
            "contract_id": contract_id,
            "user_id": user.id,
            "agent_version": "1.0",
            "status": "pending",
        }

        analysis_result = (
            db_client.table("contract_analyses").insert(analysis_data).execute()
        )
        analysis_id = analysis_result.data[0]["id"]

        # Start background analysis
        from app.tasks.background_tasks import analyze_contract_background
        background_tasks.add_task(
            analyze_contract_background,
            contract_id,
            analysis_id,
            user.id,
            document,
            request.analysis_options,
        )

        return ContractAnalysisResponse(
            contract_id=contract_id,
            analysis_id=analysis_id,
            status="pending",
            estimated_completion_minutes=2,
        )

    except HTTPException:
        # Re-raise HTTPExceptions (validation errors) without modification
        raise
    except Exception as e:
        logger.error(f"Contract analysis error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{contract_id}/analysis")
async def get_contract_analysis(
    contract_id: str, user: User = Depends(get_current_user), db_client=Depends(get_database_client)
):
    """Get contract analysis results"""

    try:
        # Ensure database client is initialized
        if not hasattr(db_client, '_client') or db_client._client is None:
            await db_client.initialize()
            
        # Get analysis results
        result = (
            db_client.table("contract_analyses")
            .select("*")
            .eq("contract_id", contract_id)
            .execute()
        )

        if not result.data:
            raise HTTPException(status_code=404, detail="Analysis not found")

        analysis = result.data[0]

        # Verify user owns this contract
        contract_result = (
            db_client.table("contracts")
            .select("*")
            .eq("id", contract_id)
            .execute()
        )
        if not contract_result.data:
            raise HTTPException(status_code=404, detail="Contract not found")

        contract = contract_result.data[0]
        doc_result = (
            db_client.table("documents")
            .select("*")
            .eq("id", contract["document_id"])
            .eq("user_id", user.id)
            .execute()
        )

        if not doc_result.data:
            raise HTTPException(status_code=403, detail="Access denied")

        return {
            "contract_id": contract_id,
            "analysis_status": analysis["status"],
            "analysis_result": analysis.get("analysis_result", {}),
            "risk_score": analysis.get("risk_score"),
            "processing_time": analysis.get("processing_time"),
            "created_at": analysis["created_at"],
        }

    except HTTPException:
        # Re-raise HTTPExceptions (validation errors) without modification
        raise
    except Exception as e:
        logger.error(f"Get analysis error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{contract_id}/report")
async def download_analysis_report(
    contract_id: str, format: str = "pdf", user: User = Depends(get_current_user), db_client=Depends(get_database_client)
):
    """Download analysis report"""

    try:
        # Get analysis data
        analysis_data = await get_contract_analysis(contract_id, user, db_client)

        if format == "pdf":
            # Generate PDF report (would implement with reportlab or similar)
            from app.tasks.background_tasks import generate_pdf_report
            pdf_content = await generate_pdf_report(analysis_data)
            return JSONResponse(
                content={"download_url": f"/api/contracts/{contract_id}/report.pdf"},
                headers={"Content-Type": "application/json"},
            )
        else:
            return analysis_data

    except Exception as e:
        logger.error(f"Report download error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))