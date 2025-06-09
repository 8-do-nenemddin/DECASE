import os
import json
from typing import List, Dict, Any

from fastapi import APIRouter, HTTPException, BackgroundTasks, UploadFile, File, Form

from app.schemas.requirement import ProcessResponse
from app.graph.rfp_graph import get_rfp_graph_app
from app.services.background_processing_service import process_requirements_in_memory
from app.core.config import OPENAI_API_KEY, LLM_MODEL

from app.agents.requirements_extract_agent import extract_requirement_sentences_agent
from app.agents.requirements_refine_agent import name_classify_describe_requirements_agent
from app.services.file_processing_service import extract_pages_as_documents, create_chunks_from_documents
from app.core.config import INPUT_DIR, OUTPUT_JSON_DIR, CHUNK_SIZE, CHUNK_OVERLAP

router = APIRouter()
compiled_app = get_rfp_graph_app()

# 입력 디렉토리 생성
os.makedirs(INPUT_DIR, exist_ok=True)


@router.post("/srs-agent", response_model=ProcessResponse)
async def process_rfp_file_endpoint(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="RFP pdf 파일")
):
    """
    RFP pdf 파일을 업로드 받아 요구사항을 분석해 JSON으로 결과를 반환합니다.
    """
    print(f"\n=== API 설정 정보 ===")
    print(f"OpenAI API Key: {OPENAI_API_KEY[:8]}...{OPENAI_API_KEY[-4:] if OPENAI_API_KEY else 'Not Set'}")
    print(f"LLM Model: {LLM_MODEL}")
    print(f"===================\n")

    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="잘못된 파일 형식입니다. PDF 파일을 업로드해주세요.")

    # PDF 파일을 JSON 형태로 변환
    extracted_requirements = await extract_pdf_to_json(file)
    print(extracted_requirements)

    if not extracted_requirements:
        return ProcessResponse(
            message="요구사항을 찾을 수 없습니다.",
            output_json_file="",
            output_csv_file="",
            errors=[]
        )

    # 백그라운드에서 요구사항 처리
    processed_results = process_requirements_in_memory(extracted_requirements, compiled_app)
    
    return ProcessResponse(
        message="요구사항 분석이 완료되었습니다.",
        requirements=processed_results
    )

async def extract_pdf_to_json(
    pdf_file: UploadFile = File(..., description="요구사항이 포함된 PDF 파일")
) -> List[Dict[str, Any]]:
    """
    RFP 파일을 업로드 받아 JSON 형태로 변환합니다.
    """
    if not pdf_file.filename or not pdf_file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="PDF 파일만 업로드 가능하며, 파일명이 있어야 합니다.")

    # PDF 파일 내용을 읽기
    pdf_content = await pdf_file.read()
    await pdf_file.close()

    # 임시 저장 경로 (절대 경로 사용)
    temp_pdf_path = os.path.abspath(os.path.join(INPUT_DIR, f"temp_uploaded_{pdf_file.filename}"))
    print(f"임시 파일 저장 경로: {temp_pdf_path}")  # 디버깅용 로그

    try:
        with open(temp_pdf_path, "wb") as f:
            f.write(pdf_content)
    except Exception as e:
        if os.path.exists(temp_pdf_path):
            os.remove(temp_pdf_path)
        raise HTTPException(status_code=500, detail=f"임시 PDF 파일 저장 실패: {str(e)}")

    try:
        pages_as_docs = extract_pages_as_documents(temp_pdf_path)
        chunked_docs = create_chunks_from_documents(pages_as_docs, CHUNK_SIZE, CHUNK_OVERLAP)
        
        all_classified_requirements = []
        print("\n--- 에이전트 1 & 2: 요구사항 식별, 명명, 분류, 상세설명 작업 중 ---")
        for i, chunk_doc in enumerate(chunked_docs):
            chunk_text = chunk_doc.page_content
            page_num = chunk_doc.metadata.get("page_number", "N/A")

            print(f"\n[청크 {i+1}/{len(chunked_docs)} 처리중 (페이지: {page_num}, 길이: {len(chunk_text)}자)]")
            if len(chunk_text.strip()) < 50:
                print(f"  청크 {i+1}이 너무 짧아 건너뜁니다.")
                continue
            
            req_sentences = extract_requirement_sentences_agent(chunk_text)
            
            if req_sentences:
                print(f"  청크 {i+1} (페이지: {page_num})에서 식별된 잠재적 요구사항 문장 ({len(req_sentences)}개):")
                for sent_idx, sentence in enumerate(req_sentences):
                    print(f"    문장 {sent_idx+1}/{len(req_sentences)} 분석 중: '{sentence[:60]}...'")
                    classified_req = name_classify_describe_requirements_agent(
                        requirement_sentence=sentence,
                        source_chunk_text=chunk_text,
                        page_number=page_num
                    )
                    if classified_req:
                        # 요구사항 데이터 구조 통일
                        requirement_data = {
                            "description_name": classified_req.get("요구사항명", ""),
                            "type": classified_req.get("type", ""),
                            "description_content": classified_req.get("요구사항 상세설명", ""),
                            "target_task": classified_req.get("대상업무", ""),
                            "rfp_page": classified_req.get("RFP", 0),
                            "processing_detail": classified_req.get("요건처리 상세", ""),
                            "raw_text": classified_req.get("출처 문장", "")
                        }
                        all_classified_requirements.append(requirement_data)
            else:
                print(f"  청크 {i+1} (페이지: {page_num})에서 식별된 요구사항 문장이 없습니다.")
        
        if not all_classified_requirements:
            print("\n최종적으로 식별 및 분류된 요구사항이 없습니다.")
            return []

        print(f"\n--- 총 {len(all_classified_requirements)}개의 개별 요구사항 정보 생성 완료 ---")
        return all_classified_requirements

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"요구사항 추출 처리 중 오류 발생: {str(e)}")
    finally:
        if os.path.exists(temp_pdf_path):
            try:
                os.remove(temp_pdf_path)
                print(f"임시 파일 '{temp_pdf_path}' 삭제 완료.")
            except Exception as e_del:
                print(f"임시 파일 '{temp_pdf_path}' 삭제 실패: {e_del}")