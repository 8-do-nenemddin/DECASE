import os
import traceback

from typing import List, Dict, Any
from app.schemas.requirement import RequirementAnalysisState
from app.services.file_processing_service import (
    load_requirements_from_json,
    save_results_to_json,
    convert_json_to_csv
)
from app.core.config import (
    INPUT_DIR,
    OUTPUT_CSV_DIR,
    OUTPUT_JSON_DIR
)


os.makedirs(INPUT_DIR, exist_ok=True)
os.makedirs(OUTPUT_CSV_DIR, exist_ok=True)
os.makedirs(OUTPUT_JSON_DIR, exist_ok=True)

def background_process_and_save(
    input_file_path: str,
    output_json_path: str,
    output_csv_path: str,
    compiled_app: Any
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
        print(f"\n[{i+1}/{total_requirements}] 처리 중: '{req_data.get('요구사항 상세설명', 'N/A')[:70]}...'")
        
        # LangGraph에 전달할 초기 상태 구성
        # RequirementAnalysisState에 정의된 모든 키를 전달하거나,
        # 그래프가 필요로 하는 최소한의 키를 전달합니다.
        # 'module' 키는 LLM 프롬프트용으로 사용되므로, 입력 JSON의 'responsible_module' 값을 사용합니다.
        inputs_for_graph: RequirementAnalysisState = {
            "description_name": req_data.get("요구사항명", "내용 없음"),
            "type": req_data.get("type"),
            "description_content": req_data.get("요구사항 상세설명", "상세 내용 없음"),
            "target_task": req_data.get("대상업무"),
            "rfp_page": req_data.get("RFP"),
            "processing_detail": req_data.get("요건처리 상세"),
            "raw_text": req_data.get("출처 문장")
        }
        # None 값을 가진 키는 제거 (선택적)
        inputs_for_graph = {k: v for k, v in inputs_for_graph.items() if v is not None}


        try:
            final_state = compiled_app.invoke(inputs_for_graph)
            if final_state and "combined_results" in final_state:
                all_final_results.append(final_state["combined_results"])
                processed_count +=1
            else:
                error_msg = f"요구사항 '{req_data.get('요구사항명')}' 처리 후 'combined_results' 누락."
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
            error_msg = f"요구사항 '{req_data.get('요구사항명')}' 처리 중 오류: {str(e)}"
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
            print(f"유효하게 처리된 요구사항이 없어 CSV 변환을 건너뛰었습니다. 에러가 포함된 JSON은 {output_json_path}에 저장되었습니다.")
        else:
            print(f"출력 JSON 파일({output_json_path})이 없거나 처리된 요구사항이 없어 CSV 변환을 건너뛰었습니다.")

    except Exception as e:
        csv_error_msg = f"CSV 변환 중 오류 발생 ({output_json_path} -> {output_csv_path}): {str(e)}"
        print(f"    ❌ {csv_error_msg}")
        error_list.append(csv_error_msg)

    print(f"백그라운드 처리 완료. 총 {processed_count}/{total_requirements}건 처리 성공. 오류: {len(error_list)}건.")
    # 여기서 DB에 상태 업데이트, 사용자에게 알림 등의 후속 조치를 할 수 있습니다.
