# app/routers/description.py
import os
import traceback
import uuid # 고유 파일명 생성을 위해 추가
from fastapi import APIRouter, HTTPException, BackgroundTasks, UploadFile, File, Form
from typing import List, Dict, Any
from app.schemas.description import DescriptionGenerationBatchResponse # 응답 모델
# 파일 처리 서비스는 app/services/ 에 있다고 가정 (폴더 구조에 따라 경로 조정)
from app.services.file_processing_service import load_requirements_from_json, save_results_to_json
from app.agents.description_agent import get_detailed_description_from_llm

router = APIRouter()

# 임시 파일 저장 및 출력 경로 (다른 라우터와 공유 가능하도록 app.core.config 등에서 관리하는 것이 좋음)
TEMP_INPUT_DIR = os.path.join(os.getcwd(), "temp_input_desc_agent")
TEMP_OUTPUT_DIR = os.path.join(os.getcwd(), "temp_output_desc_agent")

os.makedirs(TEMP_INPUT_DIR, exist_ok=True)
os.makedirs(TEMP_OUTPUT_DIR, exist_ok=True)

def _process_description_generation_for_file(input_filepath: str, output_filepath: str):
    """
    백그라운드에서 실행될 상세 설명 생성 및 파일 저장 로직.
    description_agent.ipynb의 메인 실행 로직과 유사합니다.
    """
    print(f"백그라운드 상세 설명 생성 시작: {input_filepath} -> {output_filepath}")
    error_count = 0
    processed_count = 0
    total_requirements = 0
    try:
        requirements = load_requirements_from_json(input_filepath)
        total_requirements = len(requirements)

        if not requirements:
            print(f"경고: {input_filepath}에서 처리할 요구사항을 찾을 수 없습니다.")
            # 작업 상태를 어딘가에 기록 (예: DB, 로그 파일)
            return

        for i, req in enumerate(requirements):
            req_id_for_log = req.get('id', f'index_{i}')
            print(f"  [{processed_count+error_count+1}/{total_requirements}] 상세 설명 생성 시작: ID '{req_id_for_log}'")
            desc = req.get("description")
            # description_agent.ipynb는 'raw_text_snippet'과 'responsible_module'을 사용합니다.
            snippet = req.get("raw_text_snippet")
            module = req.get("responsible_module")

            if desc: # 핵심 필드인 description이 있는 경우에만 처리
                try:
                    detailed_desc_text = get_detailed_description_from_llm(desc, snippet, module)
                    req["detailed_description"] = detailed_desc_text
                    processed_count +=1
                except Exception as e_item:
                    error_msg = f"요구사항 ID '{req.get('id', 'N/A')}' 상세 설명 생성 실패: {str(e_item)}"
                    print(error_msg)
                    req["detailed_description"] = error_msg # 에러 메시지를 필드에 기록
                    req["error_in_description_generation"] = True
                    error_count +=1
            else:
                warning_msg = f"요구사항 ID '{req.get('id', 'N/A')}'에 'description' 필드가 없어 상세 설명을 생성할 수 없습니다."
                print(warning_msg)
                req["detailed_description"] = warning_msg
                req["error_in_description_generation"] = True # 에러 플래그로 간주
                error_count +=1

        save_results_to_json(requirements, output_filepath)
        print(f"상세 설명 추가 완료. {processed_count}건 처리, {error_count}건 오류. 결과 파일: {output_filepath}")

    except Exception as e:
        print(f"상세 설명 일괄 처리 중 심각한 오류 발생: {e}")
        traceback.print_exc()
        # 전체 작업 실패 상태 기록
    finally:
        # 백그라운드 작업 완료 후 임시 입력 파일 삭제 (선택 사항)
        if os.path.exists(input_filepath):
            try:
                os.remove(input_filepath)
                print(f"임시 입력 파일 {input_filepath} 삭제 완료.")
            except Exception as e_del:
                print(f"임시 입력 파일 {input_filepath} 삭제 중 오류: {e_del}")


@router.post("/generate-detailed-descriptions-upload/", response_model=DescriptionGenerationBatchResponse)
async def generate_descriptions_upload_endpoint(
    background_tasks: BackgroundTasks,
    input_file: UploadFile = File(..., description="상세 설명을 추가할 요구사항 목록 JSON 파일"),
    output_filename_user: str = Form("detailed_requirements.json", description="결과 JSON 파일명 (예: my_output.json)")
):
    """
    업로드된 JSON 파일 내의 각 요구사항에 대해 상세 설명을 생성하고,
    결과를 서버에 지정된 파일명으로 저장합니다. 처리는 백그라운드에서 수행됩니다.
    """
    if not input_file.filename: # 파일명이 없는 경우 처리
        raise HTTPException(status_code=400, detail="업로드된 파일명이 존재하지 않습니다.")

    if not input_file.filename.endswith(".json"):
        raise HTTPException(status_code=400, detail="잘못된 파일 형식입니다. JSON 파일을 업로드해주세요.")

    # 입력 파일 저장 (고유한 임시 파일명 사용)
    unique_id = uuid.uuid4()
    temp_input_filename = f"uploaded_{unique_id}_{input_file.filename}"
    temp_input_filepath = os.path.join(TEMP_INPUT_DIR, temp_input_filename)

    try:
        with open(temp_input_filepath, "wb") as buffer:
            content = await input_file.read()
            buffer.write(content)
        print(f"입력 파일 임시 저장: {temp_input_filepath}")
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"입력 파일 '{input_file.filename}' 저장 실패: {str(e)}")
    finally:
        await input_file.close()

    # 출력 파일명 정제 (보안 및 편의)
    safe_output_filename = os.path.basename(output_filename_user)
    if not safe_output_filename.endswith(".json"):
        safe_output_filename = f"{os.path.splitext(safe_output_filename)[0]}.json"
    if not safe_output_filename: # 사용자가 확장자만 입력했거나 빈 문자열일 경우
        safe_output_filename = f"detailed_output_{unique_id}.json"

    final_output_filepath = os.path.join(TEMP_OUTPUT_DIR, safe_output_filename)

    # 백그라운드 작업 추가
    background_tasks.add_task(
        _process_description_generation_for_file,
        temp_input_filepath,
        final_output_filepath
    )

    return DescriptionGenerationBatchResponse(
        message="파일 업로드 성공. 백그라운드에서 상세 설명 생성을 시작합니다.",
        input_filename=input_file.filename, # 원본 파일명 반환
        output_filename=safe_output_filename, # 서버에 저장될 파일명
        total_requirements_in_file=0, # 실제 처리는 백그라운드에서 이루어지므로, 초기값 또는 로드 후 업데이트
        processed_requirements=0,
        errors_count=0
    )