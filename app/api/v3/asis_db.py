import os
import uuid
import asyncio
from fastapi import APIRouter, UploadFile, File, HTTPException, Form
from fastapi.responses import StreamingResponse
from io import BytesIO
from pathlib import Path
from datetime import datetime
from app.models.document import Document
from app.models.project import Project
from app.models.member import Member
from app.repositories.document_repository import document_repository, DocumentRepository
from app.core.mysql_config import get_mysql_db

from app.services.background_asis_services import run_as_is_analysis
from app.api.v2.jobs import job_store, update_job_status

router = APIRouter()

@router.post("/as-is/start")
async def start_as_is_analysis(
    file: UploadFile = File(..., description="분석할 RFP PDF 파일"),
    project_id: int = Form(None, description="프로젝트 ID"),
    member_id: int = Form(None, description="멤버 ID"),
    document_id: str = Form(None, description="문서 ID")
):
    """
    As-Is 분석 작업 시작 - Job ID, status 반환
    """
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="PDF 파일만 업로드 가능합니다.")
    try:
        # Job ID 생성
        job_id = str(uuid.uuid4())
        print(f"\n=== 새로운 As-Is 작업 시작 ===")
        print(f"Job ID: {job_id}")
        print(f"파일명: {file.filename}")
        print(f"Project ID: {project_id}")
        print(f"Member ID: {member_id}")
        print(f"Document ID: {document_id}")
        
        # 파일 내용 읽기
        pdf_content = await file.read()
        
        # 초기 작업 상태 설정
        job_store[job_id] = {
            "job_name": "ASIS",
            "status": "PROCESSING",
            "message": "As-Is 분석을 시작합니다.",
            "result": None,
            "error": None,
            "project_id": project_id,
            "member_id": member_id,
            "document_id": document_id,
            "start_time": datetime.now().isoformat()
        }
        
        # 비동기 작업 시작
        asyncio.create_task(process_as_is_background(pdf_content, job_id))
        
        return {
            "job_id": job_id,
            "job_name": "ASIS",
            "status": "PROCESSING",
            "message": "as-is 분석을 시작합니다."
        }
    
    except Exception as e:
        # 에러 발생 시 job_store 업데이트
        if 'job_id' in locals():
            update_job_status(
                job_id=job_id,
                status="FAILED",
                result=None,
                error=str(e)
            )
        raise HTTPException(
            status_code=500,
            detail=f"요구사항 분석 시작 실패: {str(e)}"
        )

async def generate_doc_id(type_prefix: str, document_repository: DocumentRepository) -> str:
    """Generate an incremental document ID with the given prefix"""
    try:
        # Find the latest document ID with the given prefix
        doc_id = await document_repository.find_latest_doc_id_by_prefix(type_prefix)
        next_number = 1

        if doc_id:
            # Extract the number part from the latest ID (e.g., "ASIS-000123" -> "000123")
            try:
                number_part = doc_id.split("-")[1]
                print(f"Number part: {number_part}")
                next_number = int(number_part) + 1
            except (IndexError, ValueError) as e:
                raise ValueError(f"Invalid docId format: {doc_id}")

        # Format the new ID with leading zeros
        return f"{type_prefix}-{next_number:06d}"
    except Exception as e:
        raise Exception(f"Failed to generate document ID: {str(e)}")

async def save_analysis_result_as_document(pdf_content: bytes, project_id: int, member_id: int, document_id: str, document_repository: DocumentRepository) -> Document:
    """Save the analysis result as a document with docTypeIdx = 8"""
    try:
        # Create upload directory if it doesn't exist
        base_upload_path = Path("uploads")
        base_upload_path.mkdir(parents=True, exist_ok=True)
        
        # Generate filename with timestamp
        timestamp = int(datetime.now().timestamp() * 1000)
        filename = f"{timestamp}_as_is_analysis.pdf"
        file_path = base_upload_path / filename
        
        # Save the PDF file
        with open(file_path, "wb") as f:
            f.write(pdf_content)
        
        # Create and save document
        doc = Document()
        doc.doc_id = await generate_doc_id("ASIS", document_repository)
        doc.name = filename
        doc.path = str(file_path)
        doc.created_date = datetime.now()
        doc.is_member_upload = False
        doc.member_id = member_id
        doc.project_id = project_id
        
        return await document_repository.save(doc)
    
    except Exception as e:
        raise Exception(f"Failed to save analysis result as document: {str(e)}")

async def process_as_is_background(pdf_content: bytes, job_id: str):
    """백그라운드에서 As-Is 분석 처리"""
    try:
        # PDF 처리 및 분석
        result_pdf = await asyncio.to_thread(run_as_is_analysis, pdf_content)

        # Get job details
        job = job_store[job_id]
        project_id = job.get("project_id")
        member_id = job.get("member_id")
        document_id = job.get("document_id")
        
        # Save analysis result as document
        if project_id and member_id:
            async for db in get_mysql_db():
                document_repository = DocumentRepository(db)
                saved_doc = await save_analysis_result_as_document(
                    result_pdf,
                    project_id,
                    member_id,
                    document_id,
                    document_repository
                )
                result = {
                    "document": saved_doc,
                    "pdf_content": result_pdf
                }
                break
        else:
            result = result_pdf
        
        # 작업 완료 상태 업데이트
        update_job_status(
            job_id=job_id,
            status="COMPLETED",
            error=None,
            message="As-Is 분석이 완료되었습니다."
        )
        
    except Exception as e:
        # 실패 상태로 업데이트
        update_job_status(
            job_id=job_id,
            status="FAILED",
            result=None,
            error=str(e),
            message=f"As-Is 분석 실패: {str(e)}"
        )