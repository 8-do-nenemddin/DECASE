import os
import json
import uuid
import asyncio
from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.concurrency import run_in_threadpool
from concurrent.futures import ThreadPoolExecutor
from app.schemas.requirement import ProcessResponse
from app.graph.rfp_graph import get_rfp_graph_app
from app.services.background_processing_service import process_requirements_in_memory
from app.core.config import OPENAI_API_KEY, LLM_MODEL
from app.agents.srs.requirements_extract_agent import extract_requirement_sentences_agent
from app.agents.srs.requirements_refine_agent import name_classify_describe_requirements_agent
from app.services.file_processing_service import extract_pages_as_documents, create_chunks_from_documents
from app.core.config import INPUT_DIR, OUTPUT_JSON_DIR, CHUNK_SIZE, CHUNK_OVERLAP
from app.api.v2.jobs import job_store, update_job_status
from datetime import datetime
from app.services.requirement_service import RequirementService
from app.core.mysql_config import get_mysql_db
from app.models import Document, Member, Project
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.repositories.document_repository import DocumentRepository

router = APIRouter()
compiled_app = get_rfp_graph_app()

# 전역 스레드 풀 생성
thread_pool = ThreadPoolExecutor(max_workers=4)

os.makedirs(INPUT_DIR, exist_ok=True)

@router.post("/srs-agent/start")
async def start_srs_analysis(
    file: UploadFile = File(..., description="분석할 RFP PDF 파일"),
    project_id: int = Form(None, description="프로젝트 ID"),
    member_id: int = Form(None, description="멤버 ID"),
    document_id: str = Form(None, description="문서 ID")
):
    """
    요구사항 분석 작업 시작 - Job ID 반환
    """
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="PDF 파일만 업로드 가능합니다.")

    try:
        # Job ID 생성
        job_id = str(uuid.uuid4())
        
        # 파일 내용 읽기
        pdf_content = await file.read()
        
        # 초기 작업 상태 설정
        job_store[job_id] = {
            "job_name": "SRS",
            "status": "PROCESSING",
            "message": "요구사항 분석을 시작합니다.",
            "result": None,
            "error": None,
            "project_id": project_id,
            "member_id": member_id,
            "document_id": document_id,
            "start_time": datetime.now().isoformat()
        }
        
        # 비동기 작업 시작
        asyncio.create_task(process_srs_background(pdf_content, job_id, file.filename))
        
        return {
            "job_id": job_id,
            "job_name": "SRS",
            "status": "PROCESSING",
            "message": "요구사항 분석을 시작합니다."
        }
        
    except Exception as e:
        import traceback
        error_traceback = traceback.format_exc()
        error_message = f"요구사항 분석 시작 실패:\n{str(e)}\n\n상세 에러:\n{error_traceback}"
        print(error_message)
        
        # 에러 발생 시 job_store 업데이트
        if 'job_id' in locals():
            update_job_status(
                job_id=job_id,
                status="FAILED",
                result=None,
                error=error_message
            )
        raise HTTPException(
            status_code=500,
            detail=f"요구사항 분석 시작 실패: {str(e)}"
        )


async def process_srs_background(pdf_content: bytes, job_id: str, original_filename: str):
    """백그라운드에서 요구사항 분석 처리"""
    try:
        print(f"\n=== 백그라운드 작업 시작 ===")
        print(f"Job ID: {job_id}")
        print(f"파일명: {original_filename}")
        
        # 임시 파일 저장
        unique_id = uuid.UUID(job_id)
        temp_pdf_path = os.path.abspath(os.path.join(INPUT_DIR, f"temp_{unique_id}_{original_filename}"))
        print(f"임시 파일 경로: {temp_pdf_path}")
        
        try:
            print("\n=== PDF 처리 시작 ===")
            # 파일 쓰기를 비동기로 처리
            await asyncio.to_thread(lambda: open(temp_pdf_path, "wb").write(pdf_content))
            
            # PDF 처리 및 요구사항 추출
            pages_as_docs = await asyncio.to_thread(extract_pages_as_documents, temp_pdf_path)
            if not pages_as_docs:
                raise Exception("PDF 문서에서 페이지를 추출할 수 없습니다.")
                
            chunked_docs = await asyncio.to_thread(create_chunks_from_documents, pages_as_docs, CHUNK_SIZE, CHUNK_OVERLAP)
            if not chunked_docs:
                raise Exception("문서 청크를 생성할 수 없습니다.")
            
            all_classified_requirements = []
            print("\n--- 에이전트 1 & 2: 요구사항 식별, 명명, 분류, 상세설명 작업 중 ---")
            
            # 청크 처리를 병렬로 실행
            async def process_chunk(chunk_doc, i):
                chunk_text = chunk_doc.page_content
                page_num = chunk_doc.metadata.get("page_number", "N/A")

                print(f"\n[청크 {i+1}/{len(chunked_docs)} 처리중 (페이지: {page_num})]")
                if len(chunk_text.strip()) < 50:
                    print(f"  청크 {i+1}이 너무 짧아 건너뜁니다.")
                    return []

                req_sentences = await asyncio.to_thread(extract_requirement_sentences_agent, chunk_text)
                chunk_requirements = []
                
                if req_sentences:
                    print(f"  청크 {i+1}에서 식별된 잠재적 요구사항 문장 ({len(req_sentences)}개):")
                    for sent_idx, sentence in enumerate(req_sentences):
                        print(f"    문장 {sent_idx+1}/{len(req_sentences)} 분석 중: '{sentence[:60]}...'")
                        classified_req = await asyncio.to_thread(
                            name_classify_describe_requirements_agent,
                            requirement_sentence=sentence,
                            source_chunk_text=chunk_text,
                            page_number=page_num
                        )
                        if classified_req:
                            requirement_data = {
                                "description_name": classified_req.get("요구사항명", ""),
                                "type": classified_req.get("type", ""),
                                "description_content": classified_req.get("요구사항 상세설명", ""),
                                "target_task": classified_req.get("대상업무", ""),
                                "rfp_page": classified_req.get("RFP", 0),
                                "processing_detail": classified_req.get("요건처리 상세", ""),
                                "raw_text": classified_req.get("출처 문장", "")
                            }
                            chunk_requirements.append(requirement_data)
                return chunk_requirements

            # 모든 청크를 병렬로 처리
            chunk_tasks = [process_chunk(chunk_doc, i) for i, chunk_doc in enumerate(chunked_docs)]
            chunk_results = await asyncio.gather(*chunk_tasks)
            
            # 결과 병합
            for requirements in chunk_results:
                all_classified_requirements.extend(requirements)
            
            if not all_classified_requirements:
                raise Exception("요구사항을 추출할 수 없습니다.")
            
            # 요구사항 처리
            processed_results = await asyncio.to_thread(process_requirements_in_memory, all_classified_requirements, compiled_app)
            
            # 결과 저장
            output_filename = f"processed_{unique_id}_{original_filename}.json"
            output_json_path = os.path.join(OUTPUT_JSON_DIR, output_filename)
            os.makedirs(OUTPUT_JSON_DIR, exist_ok=True)
            
            await asyncio.to_thread(
                lambda: json.dump(processed_results, open(output_json_path, "w", encoding="utf-8"), ensure_ascii=False, indent=4)
            )
            
            # DB에 요구사항 저장
            print("\n=== 요구사항 저장 프로세스 시작 ===")
            await save_requirements_to_db(processed_results, job_store[job_id])
            
        finally:
            # 임시 파일 정리
            if os.path.exists(temp_pdf_path):
                try:
                    await asyncio.to_thread(os.remove, temp_pdf_path)
                    print(f"임시 파일 '{temp_pdf_path}' 삭제 완료.")
                except Exception as e_del:
                    print(f"임시 파일 '{temp_pdf_path}' 삭제 실패: {e_del}")
                    
    except Exception as e:
        import traceback
        error_traceback = traceback.format_exc()
        error_message = f"요구사항 처리 중 오류 발생:\n{str(e)}\n\n상세 에러:\n{error_traceback}"
        print(error_message)
        update_job_status(
            job_id=job_id,
            status="FAILED",
            result=None,
            error=error_message
        )

async def save_requirements_to_db(processed_results, job_info):
    """
    요구사항 리스트를 DB에 저장하는 함수
    """
    async for db in get_mysql_db():
        print(f"DB 연결 성공")
        project_id = job_info.get("project_id")
        member_id = job_info.get("member_id")
        document_id = job_info.get("document_id")

        print(f"ID 정보 - Project: {project_id}, Member: {member_id}, Document: {document_id}")

        if not all([project_id, member_id, document_id]):
            print("ERROR: 필수 ID 누락")
            raise Exception("프로젝트 ID, 멤버 ID, 문서 ID가 필요합니다.")
        
        # 관련 엔티티 조회
        project_query = select(Project).where(Project.project_id == project_id)
        member_query = select(Member).where(Member.member_id == member_id)
        document_query = select(Document).where(Document.doc_id == document_id)

        print(f"\n문서 ID 조회: {document_id}")
        print(f"문서 쿼리: {document_query}")

        project_result = await db.execute(project_query)
        member_result = await db.execute(member_query)
        document_result = await db.execute(document_query)

        project = project_result.scalar_one_or_none()
        member = member_result.scalar_one_or_none()
        document = document_result.scalar_one_or_none()

        print(f"엔티티 조회 결과 - Project: {project is not None}, Member: {member is not None}, Document: {document is not None}")
        
        if document is None:
            print(f"문서를 찾을 수 없습니다. document_id: {document_id}")
        
        if not all([project, member, document]):
            print("ERROR: 엔티티 조회 실패")
            raise Exception("프로젝트, 멤버, 또는 문서를 찾을 수 없습니다.")
        
        # RequirementService를 사용하여 요구사항 저장
        print("\n=== 요구사항 저장 시작 ===")
        requirement_service = RequirementService(db)
        # 요구사항을 순차적으로 저장
        for idx, requirement in enumerate(processed_results, 1):
            print(f"\n요구사항 {idx}/{len(processed_results)} 저장 시도:")
            print(f"요구사항 데이터: {requirement}")
            try:
                await requirement_service.create_requirement(requirement, member, project, document)
                print(f"요구사항 {idx} 저장 성공")
            except Exception as e:
                print(f"ERROR: 요구사항 {idx} 저장 실패 - {str(e)}")
                raise
        print("\n=== 모든 요구사항 저장 완료 ===")
        break
