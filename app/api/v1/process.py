import os
import json
import uuid  # <<< 1. uuid 임포트
from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException, UploadFile, File
# <<< 2. run_in_threadpool 임포트 및 BackgroundTasks 제거
from fastapi.concurrency import run_in_threadpool
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

os.makedirs(INPUT_DIR, exist_ok=True)


@router.post("/srs-agent", response_model=ProcessResponse)
async def process_rfp_file_endpoint(
    # background_tasks: BackgroundTasks, # <<< 3. 불필요하므로 제거
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

    # <<< 4. 고유 ID 생성으로 파일명 충돌 방지 >>>
    unique_id = uuid.uuid4()
    original_filename = file.filename
    
    # <<< 5. 무거운 동기 작업을 별도 스레드에서 실행 >>>
    try:
        # extract_pdf_to_json 함수와 그 인자들을 run_in_threadpool에 전달
        extracted_requirements = await run_in_threadpool(
            extract_pdf_to_json_sync, file, unique_id
        )
    except Exception as e:
        # 스레드풀에서 발생한 예외 처리
        raise HTTPException(status_code=500, detail=f"요구사항 추출 스레드 오류: {str(e)}")


    if not extracted_requirements:
        return ProcessResponse(message="요구사항을 찾을 수 없습니다.", requirements=[])

    # 이 부분은 비교적 빠르므로 그대로 두거나, 마찬가지로 스레드풀에서 실행 가능
    processed_results = process_requirements_in_memory(extracted_requirements, compiled_app)
    
    # 고유 ID를 사용해 결과 파일 저장
    output_filename = f"processed_{unique_id}_{original_filename}.json"
    output_json_path = os.path.join(OUTPUT_JSON_DIR, output_filename)
    os.makedirs(OUTPUT_JSON_DIR, exist_ok=True)

    try:
        with open(output_json_path, "w", encoding="utf-8") as json_file:
            json.dump(processed_results, json_file, ensure_ascii=False, indent=4)
        print(f"처리된 결과가 JSON 파일로 저장되었습니다: {output_json_path}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"JSON 파일 저장 실패: {str(e)}")
    
    return ProcessResponse(
        message="요구사항 분석이 완료되었습니다.",
        requirements=processed_results
    )

def extract_pdf_to_json_sync(
    pdf_file: UploadFile,
    unique_id: uuid.UUID
) -> List[Dict[str, Any]]:
    """
    RFP 파일을 처리하여 요구사항 JSON 목록을 반환하는 동기 함수.
    """
    original_filename = pdf_file.filename
    pdf_content = pdf_file.file.read() # 동기 함수에서는 .file.read() 사용

    # 고유 ID를 사용한 임시 저장 경로
    temp_pdf_path = os.path.abspath(os.path.join(INPUT_DIR, f"temp_{unique_id}_{original_filename}"))
    print(f"임시 파일 저장 경로: {temp_pdf_path}")

    try:
        with open(temp_pdf_path, "wb") as f:
            f.write(pdf_content)
        
        # --- 이하 로직은 기존과 거의 동일 ---
        pages_as_docs = extract_pages_as_documents(temp_pdf_path)
        chunked_docs = create_chunks_from_documents(pages_as_docs, CHUNK_SIZE, CHUNK_OVERLAP)
        
        all_classified_requirements = []
        print("\n--- 에이전트 1 & 2: 요구사항 식별, 명명, 분류, 상세설명 작업 중 ---")
        for i, chunk_doc in enumerate(chunked_docs):
            chunk_text = chunk_doc.page_content
            page_num = chunk_doc.metadata.get("page_number", "N/A")

            print(f"\n[청크 {i+1}/{len(chunked_docs)} 처리중 (페이지: {page_num})]")
            if len(chunk_text.strip()) < 50:
                print(f"  청크 {i+1}이 너무 짧아 건너뜁니다.")
                continue
            
            req_sentences = extract_requirement_sentences_agent(chunk_text)
            
            if req_sentences:
                print(f"  청크 {i+1}에서 식별된 잠재적 요구사항 문장 ({len(req_sentences)}개):")
                for sent_idx, sentence in enumerate(req_sentences):
                    print(f"    문장 {sent_idx+1}/{len(req_sentences)} 분석 중: '{sentence[:60]}...'")
                    classified_req = name_classify_describe_requirements_agent(
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
                        all_classified_requirements.append(requirement_data)
        
        return all_classified_requirements

    finally:
        if os.path.exists(temp_pdf_path):
            try:
                os.remove(temp_pdf_path)
                print(f"임시 파일 '{temp_pdf_path}' 삭제 완료.")
            except Exception as e_del:
                print(f"임시 파일 '{temp_pdf_path}' 삭제 실패: {e_del}")