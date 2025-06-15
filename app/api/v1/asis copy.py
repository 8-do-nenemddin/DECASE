import os
import uuid
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from io import BytesIO

from app.services.background_asis_services import run_as_is_analysis
from app.api.v1.jobs import job_store, update_job_status

router = APIRouter()

@router.post("/as-is/start")
async def start_as_is_analysis(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="분석할 RFP PDF 파일")
):
    """
    As-Is 분석 작업 시작 - Job ID 반환
    """
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="PDF 파일만 업로드 가능합니다.")

    # Job ID 생성
    job_id = str(uuid.uuid4())
    
    # 파일 내용 읽기
    pdf_content = await file.read()
    
    # 초기 작업 상태 설정
    job_store[job_id] = {
        "status": "PROCESSING",
        "message": "As-Is 분석을 시작합니다.",
        "result": None,
        "error": None,
        "attempts": 0
    }
    
    # 백그라운드에서 처리 시작
    background_tasks.add_task(process_as_is_background, pdf_content, job_id)
    
    return {
        "job_id": job_id,
        "message": "As-Is 분석을 시작합니다.",
        "state": "PROCESSING",
        "attempts": 0
    }

@router.get("/as-is/{job_id}/status")
async def get_as_is_status(job_id: str):
    """
    As-Is 분석 상태 조회
    """
    if job_id not in job_store:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = job_store[job_id]
    
    if job["status"] == "COMPLETED" and isinstance(job["result"], bytes):
        # PDF 결과가 있으면 StreamingResponse로 반환
        pdf_buffer = BytesIO(job["result"])
        return StreamingResponse(
            pdf_buffer,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=as_is_analysis_report.pdf"
            }
        )
    
    return {
        "job_id": job_id,
        "state": job["status"],
        "message": job.get("message", ""),
        "result": job.get("result") if job["status"] == "COMPLETED" else None
    }

def process_as_is_background(pdf_content: bytes, job_id: str):
    """백그라운드에서 As-Is 분석 처리"""
    try:
        # PDF 처리 및 분석
        result_pdf = run_as_is_analysis(pdf_content)
        
        # 작업 완료 상태 업데이트
        update_job_status(
            job_id=job_id,
            status="COMPLETED",
            result=result_pdf,
            error=None,
            message="As-Is 분석이 완료되었습니다."
        )
        
    except Exception as e:
<<<<<<<< HEAD:app/api/v1/asis copy.py
        raise HTTPException(status_code=500, detail=f"PDF 파일 저장 실패: {str(e)}")

    report_filename = f"As_Is_Report_{os.path.splitext(pdf_file.filename)[0]}.md"

    background_tasks.add_task(run_as_is_analysis_background, temp_pdf_path, report_filename)

    return AsIsReportResponse(
        message="PDF 파일 업로드 성공. As-Is 분석 보고서 생성을 백그라운드에서 시작합니다.",
        report_filename=f"서버의 '{OUTPUT_ASIS_DIR}/{report_filename}' 경로에 저장될 예정입니다." 
        # 실제로는 다운로드 가능한 URL이나 작업 ID 반환
    )


========
        # 실패 상태로 업데이트
        update_job_status(
            job_id=job_id,
            status="FAILED",
            result=None,
            error=str(e),
            message=f"As-Is 분석 실패: {str(e)}"
        )
>>>>>>>> 39f369a8c2a946843058be1c137ce9d9fe620747:app/api/v1/asis.py
