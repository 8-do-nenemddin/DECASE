# app/routers/process.py
import os
import traceback
from fastapi import APIRouter, HTTPException, BackgroundTasks, UploadFile, File, Form
from typing import List, Dict, Any

from app.schemas.requirement import FileProcessRequest, ProcessResponse, RequirementAnalysisState
from app.services.file_processing_service import load_requirements_from_json, save_results_to_json, convert_json_to_csv
from app.graph.rfp_graph import get_rfp_graph_app

router = APIRouter()
compiled_app = get_rfp_graph_app() # 컴파일된 LangGraph 앱 인스턴스 로드

# 임시 파일 저장 경로 (실제 운영 환경에서는 적절한 경로 및 관리 방식 필요)
TEMP_INPUT_DIR = "app/docs"  # FastAPI 앱이 input 폴더에 직접 쓰도록 하기보다 임시 폴더 사용
TEMP_OUTPUT_DIR = "app/output" # FastAPI 앱이 output 폴더에 직접 쓰도록 하기보다 임시 폴더 사용

os.makedirs(TEMP_INPUT_DIR, exist_ok=True)
os.makedirs(TEMP_OUTPUT_DIR, exist_ok=True)


def background_process_and_save(
    input_file_path: str,
    output_json_path: str,
    output_csv_path: str
):
    """
    백그라운드에서 LangGraph를 사용하여 요구사항을 처리하고 결과를 저장하는 함수.
    """
    print(f"백그라운드 처리 시작: 입력 {input_file_path}")
    requirements_to_process = load_requirements_from_json(input_file_path)
    processed_count = 0
    error_list = []

    if not requirements_to_process:
        print("처리할 요구사항이 없습니다.")
        # 여기서 에러 상태를 파일이나 DB에 기록할 수 있습니다.
        return

    all_final_results: List[Dict[str, Any]] = []
    total_requirements = len(requirements_to_process)

    for i, req_data in enumerate(requirements_to_process):
        print(f"\n[{i+1}/{total_requirements}] 처리 중: '{req_data.get('description', 'N/A')[:70]}...'")
        
        # LangGraph에 전달할 초기 상태 구성
        # RequirementAnalysisState에 정의된 모든 키를 전달하거나,
        # 그래프가 필요로 하는 최소한의 키를 전달합니다.
        # 'module' 키는 LLM 프롬프트용으로 사용되므로, 입력 JSON의 'responsible_module' 값을 사용합니다.
        inputs_for_graph: RequirementAnalysisState = {
            "id": req_data.get("id"),
            "type": req_data.get("type"),
            "description": req_data.get("description", "내용 없음"),
            "detailed_description": req_data.get("detailed_description", "상세 내용 없음"),
            "acceptance_criteria": req_data.get("acceptance_criteria"),
            "responsible_module": req_data.get("responsible_module"), # 원본 필드
            "parent_id": req_data.get("parent_id"),
            "source_pages": req_data.get("source_pages"),
            "module": req_data.get("responsible_module", "모듈 미지정") # LLM 프롬프트용
        }
        # None 값을 가진 키는 제거 (선택적)
        inputs_for_graph = {k: v for k, v in inputs_for_graph.items() if v is not None}


        try:
            final_state = compiled_app.invoke(inputs_for_graph)
            if final_state and "combined_results" in final_state:
                all_final_results.append(final_state["combined_results"])
                processed_count +=1
            else:
                error_msg = f"요구사항 ID '{req_data.get('id')}' 처리 후 'combined_results' 누락."
                print(f"    ⚠️ {error_msg}")
                error_list.append(error_msg)
                # 부분적 에러 결과 추가
                all_final_results.append({
                    **inputs_for_graph, 
                    "error_processing": "combined_results_missing",
                    "category_large": "Error", "category_medium": "Error", "category_small": "Error",
                    "difficulty": "Error", "importance": "Error"
                })
        except Exception as e:
            error_msg = f"요구사항 ID '{req_data.get('id')}' 처리 중 오류: {str(e)}"
            print(f"    ❌ {error_msg}")
            traceback.print_exc()
            error_list.append(error_msg)
            # 전체 에러 결과 추가
            all_final_results.append({
                 **inputs_for_graph,
                "error_processing": str(e),
                "category_large": "Error", "category_medium": "Error", "category_small": "Error",
                "difficulty": "Error", "importance": "Error"
            })

    # 모든 결과를 JSON 파일로 저장
    save_results_to_json(all_final_results, output_json_path)
    print(f"처리된 JSON이 {output_json_path}에 저장되었습니다.")

    # JSON을 CSV로 변환
    try:
        if os.path.exists(output_json_path) and processed_count > 0 : # 에러만 있는 경우가 아니면 변환
             convert_json_to_csv(output_json_path, output_csv_path)
             print(f"CSV 변환 완료: {output_csv_path}")
        elif processed_count == 0 and all_final_results : # 처리된 것은 없으나 결과는 있을 때 (전부 에러)
            print(f"유효하게 처리된 요구사항이 없어 CSV 변환을 건너<0xEB><0x9A><0x84>니다. 에러가 포함된 JSON은 {output_json_path}에 저장되었습니다.")
        else:
            print(f"출력 JSON 파일({output_json_path})이 없거나 처리된 요구사항이 없어 CSV 변환을 건너<0xEB><0x9A><0x84>니다.")

    except Exception as e:
        csv_error_msg = f"CSV 변환 중 오류 발생 ({output_json_path} -> {output_csv_path}): {str(e)}"
        print(f"    ❌ {csv_error_msg}")
        error_list.append(csv_error_msg)
        # 이 경우, 이미 저장된 JSON 파일은 그대로 둡니다.

    # (선택) 처리 완료 후 입력 파일 삭제
    # try:
    #     if os.path.exists(input_file_path):
    #         os.remove(input_file_path)
    #         print(f"임시 입력 파일 {input_file_path} 삭제 완료.")
    # except Exception as e:
    #     print(f"임시 입력 파일 {input_file_path} 삭제 중 오류: {e}")

    print(f"백그라운드 처리 완료. 총 {processed_count}/{total_requirements}건 처리 성공. 오류: {len(error_list)}건.")
    # 여기서 DB에 상태 업데이트, 사용자에게 알림 등의 후속 조치를 할 수 있습니다.


@router.post("/process-rfp-file/", response_model=ProcessResponse)
async def process_rfp_file_endpoint(
    background_tasks: BackgroundTasks,
    input_file: UploadFile = File(..., description="분석할 요구사항이 담긴 JSON 파일"),
    output_json_filename: str = Form("processed_requirements.json", description="출력될 JSON 파일명"),
    output_csv_filename: str = Form("final_srs.csv", description="출력될 CSV 파일명")
):
    """
    RFP JSON 파일을 업로드 받아 요구사항을 분석하고, 
    처리된 JSON 파일과 최종 SRS CSV 파일을 생성합니다.
    실제 처리는 백그라운드에서 수행됩니다.
    """
    if not input_file.filename.endswith(".json"):
        raise HTTPException(status_code=400, detail="잘못된 파일 형식입니다. JSON 파일을 업로드해주세요.")

    # 입력 파일 저장
    temp_input_file_path = os.path.join(TEMP_INPUT_DIR, f"input_{input_file.filename}")
    try:
        with open(temp_input_file_path, "wb") as buffer:
            buffer.write(await input_file.read())
        print(f"입력 파일 임시 저장: {temp_input_file_path}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"입력 파일 저장 실패: {str(e)}")

    # 출력 파일 경로 설정 (보안을 위해 파일명 검증/정제 필요)
    # 여기서는 간단히 TEMP_OUTPUT_DIR 사용
    safe_output_json_filename = os.path.basename(output_json_filename) # 경로 조작 방지
    safe_output_csv_filename = os.path.basename(output_csv_filename)   # 경로 조작 방지
    
    final_output_json_path = os.path.join(TEMP_OUTPUT_DIR, safe_output_json_filename)
    final_output_csv_path = os.path.join(TEMP_OUTPUT_DIR, safe_output_csv_filename)

    # 백그라운드 작업 추가
    background_tasks.add_task(
        background_process_and_save,
        temp_input_file_path,
        final_output_json_path,
        final_output_csv_path
    )

    return ProcessResponse(
        message="파일 업로드 성공. 백그라운드에서 요구사항 분석 및 파일 생성을 시작합니다.",
        output_json_file=f"결과는 서버의 '{final_output_json_path}' 경로에 저장될 예정입니다.", # 실제로는 다운로드 URL 제공 등이 필요
        output_csv_file=f"결과는 서버의 '{final_output_csv_path}' 경로에 저장될 예정입니다.",
        total_processed=0, # 초기값, 실제 처리는 백그라운드에서
        errors=[]
    )

# (선택 사항) 결과 파일 다운로드 엔드포인트 (실제 운영 시 보안 및 권한 확인 필요)
# from fastapi.responses import FileResponse
# @router.get("/download/{filename}")
# async def download_file(filename: str):
#     file_path = os.path.join(TEMP_OUTPUT_DIR, filename)
#     if os.path.exists(file_path):
#         return FileResponse(path=file_path, filename=filename, media_type='application/octet-stream')
#     raise HTTPException(status_code=404, detail="파일을 찾을 수 없습니다.")