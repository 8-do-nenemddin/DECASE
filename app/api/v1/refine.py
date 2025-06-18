# app/routers/requirement_extraction.py

import os
import json
from fastapi import APIRouter, UploadFile, File, HTTPException, Form
from app.schemas.requirement import RefineResponse # 응답 모델 확인 필요
from app.agents.srs.requirements_extract_agent import extract_requirement_sentences_agent
from app.agents.srs.requirements_refine_agent import name_classify_describe_requirements_agent
from app.services.file_processing_service import extract_pages_as_documents, create_chunks_from_documents
from app.core.config import INPUT_DIR, OUTPUT_JSON_DIR, CHUNK_SIZE, CHUNK_OVERLAP

router = APIRouter()

os.makedirs(INPUT_DIR, exist_ok=True)
os.makedirs(OUTPUT_JSON_DIR, exist_ok=True)

@router.post("/refine", response_model=RefineResponse)
async def extract_requirements_endpoint(
    pdf_file: UploadFile = File(..., description="요구사항이 포함된 PDF 파일"),
    output_json_filename: str = Form("extracted_requirements.json", description="출력 JSON 파일명")
):
    """
    RFP 파일을 업로드 받아 요구사항을 추출하고 정제합니다.
    정제된 요구사항은 JSON 파일로 저장됩니다.
    """
    if not pdf_file.filename or not pdf_file.filename.endswith(".pdf"): # 파일명 존재 여부도 체크
        raise HTTPException(status_code=400, detail="PDF 파일만 업로드 가능하며, 파일명이 있어야 합니다.")

    # PDF 파일 내용을 한 번만 읽어서 변수에 저장
    pdf_content = await pdf_file.read()
    await pdf_file.close() # 파일 핸들 닫기

    # 임시 저장 경로 (처음 저장하는 경로, file_processing_service에서 사용할 경로)
    # 이 경로는 extract_pages_as_documents 함수가 파일 시스템 경로를 필요로 하기 때문에 사용
    temp_pdf_path = os.path.join(INPUT_DIR, f"temp_uploaded_{pdf_file.filename}")
    try:
        with open(temp_pdf_path, "wb") as f:
            f.write(pdf_content) # 읽어둔 내용을 파일에 씀
    except Exception as e:
        # 임시 파일 저장 실패 시 생성된 파일 삭제 시도
        if os.path.exists(temp_pdf_path):
            os.remove(temp_pdf_path)
        raise HTTPException(status_code=500, detail=f"임시 PDF 파일 저장 실패: {str(e)}")

    # 출력 JSON 파일 경로 설정
    safe_output_filename = os.path.basename(output_json_filename)
    if not safe_output_filename.endswith(".json"): # 확장자 확인 및 추가
        safe_output_filename = f"{os.path.splitext(safe_output_filename)[0]}.json"
    output_path = os.path.join(OUTPUT_JSON_DIR, safe_output_filename)

    try:
        pages_as_docs = extract_pages_as_documents(temp_pdf_path) # 저장된 임시 파일 경로 사용
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
                        all_classified_requirements.append(classified_req)
            else:
                print(f"  청크 {i+1} (페이지: {page_num})에서 식별된 요구사항 문장이 없습니다.")
        
        if not all_classified_requirements:
            print("\n최종적으로 식별 및 분류된 요구사항이 없습니다.")
            # 요구사항이 없을 경우에도 응답 모델에 맞는 메시지와 빈 파일명을 반환
            return RefineResponse(
                message="요구사항을 찾을 수 없습니다.",
                output_json_file="" # 또는 적절한 기본값
            )
        
        print(f"\n--- 총 {len(all_classified_requirements)}개의 개별 요구사항 정보 생성 완료 ---")
        # output_path (절대 경로)에 JSON 파일 저장
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(all_classified_requirements, f, ensure_ascii=False, indent=4)
        print(f"결과가 '{output_path}' 파일에 저장되었습니다.")

    except Exception as e:
        # 처리 중 발생한 다른 모든 예외에 대해 HTTP 예외 반환
        raise HTTPException(status_code=500, detail=f"요구사항 추출 처리 중 오류 발생: {str(e)}")
    finally:
        # 작업 완료 후 임시 PDF 파일 삭제
        if os.path.exists(temp_pdf_path):
            try:
                os.remove(temp_pdf_path)
                print(f"임시 파일 '{temp_pdf_path}' 삭제 완료.")
            except Exception as e_del:
                print(f"임시 파일 '{temp_pdf_path}' 삭제 실패: {e_del}")


    return RefineResponse(
        message="요구사항 추출 및 정제가 완료되었습니다.", # 성공 메시지 수정
        output_json_file=output_path # 저장된 JSON 파일의 전체 경로 반환
    )