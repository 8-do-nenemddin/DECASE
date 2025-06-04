import os

from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks

from app.schemas.asis import AsIsReportResponse
from app.services.background_asis_services import run_as_is_analysis_background
from app.core.config import INPUT_DIR, OUTPUT_ASIS_DIR

router = APIRouter()

@router.post("/analyze", response_model=AsIsReportResponse)
async def analyze_as_is(
    background_tasks: BackgroundTasks,
    pdf_file: UploadFile = File(..., description="분석할 RFP PDF 파일"),
):
    if not pdf_file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="PDF 파일만 업로드 가능합니다.")

    temp_pdf_path = os.path.join(INPUT_DIR, f"asis_{pdf_file.filename}")
    try:
        with open(temp_pdf_path, "wb") as buffer:
            buffer.write(await pdf_file.read())
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF 파일 저장 실패: {str(e)}")

    report_filename = f"As_Is_Report_{os.path.splitext(pdf_file.filename)[0]}.md"

    background_tasks.add_task(run_as_is_analysis_background, temp_pdf_path, report_filename)

    return AsIsReportResponse(
        message="PDF 파일 업로드 성공. As-Is 분석 보고서 생성을 백그라운드에서 시작합니다.",
        report_filename=f"서버의 '{OUTPUT_ASIS_DIR}/{report_filename}' 경로에 저장될 예정입니다." 
        # 실제로는 다운로드 가능한 URL이나 작업 ID 반환
    )