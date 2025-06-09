import os
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
from io import BytesIO

from app.services.background_asis_services import run_as_is_analysis

router = APIRouter()

@router.post("/as-is")
async def analyze_as_is(
    file: UploadFile = File(..., description="분석할 RFP PDF 파일"),
):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="PDF 파일만 업로드 가능합니다.")

    try:
        # Read the PDF content
        pdf_content = await file.read()
        
        # Process the PDF and get the analysis report as PDF
        result_pdf = run_as_is_analysis(pdf_content)
        
        # Create a BytesIO object for the response
        pdf_buffer = BytesIO(result_pdf)
        
        # Return the PDF as a streaming response
        return StreamingResponse(
            pdf_buffer,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=as_is_analysis_report.pdf"
            }
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF 분석 실패: {str(e)}")