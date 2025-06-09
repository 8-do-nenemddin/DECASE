import os
import traceback

from typing import List, Dict, Any
from app.schemas.requirement import RequirementAnalysisState
from app.core.config import (
    INPUT_DIR,
    OUTPUT_CSV_DIR,
    OUTPUT_JSON_DIR
)

os.makedirs(INPUT_DIR, exist_ok=True)
os.makedirs(OUTPUT_CSV_DIR, exist_ok=True)
os.makedirs(OUTPUT_JSON_DIR, exist_ok=True)

def process_requirements_in_memory(
    requirements_to_process: List[Dict[str, Any]],
    compiled_app: Any
) -> List[Dict[str, Any]]:
    """
    백그라운드에서 LangGraph를 사용하여 요구사항을 처리하는 함수.
    """
    print(f"요구사항 처리 시작: {len(requirements_to_process)}개 항목")
    processed_count = 0
    error_list = []

    if not requirements_to_process:
        print("처리할 요구사항이 없습니다.")
        return []

    all_final_results: List[Dict[str, Any]] = []
    total_requirements = len(requirements_to_process)

    for i, req_data in enumerate(requirements_to_process):
        print(f"\n[{i+1}/{total_requirements}] 처리 중: '{req_data.get('description_content', 'N/A')[:70]}...'")
        
        # LangGraph에 전달할 초기 상태 구성
        inputs_for_graph: RequirementAnalysisState = {
            "description_name": req_data.get("description_name", "내용 없음"),
            "type": req_data.get("type"),
            "description_content": req_data.get("description_content", "상세 내용 없음"),
            "target_task": req_data.get("target_task"),
            "rfp_page": req_data.get("rfp_page"),
            "processing_detail": req_data.get("processing_detail"),
            "raw_text": req_data.get("raw_text")
        }
        # None 값을 가진 키는 제거 (선택적)
        inputs_for_graph = {k: v for k, v in inputs_for_graph.items() if v is not None}

        try:
            final_state = compiled_app.invoke(inputs_for_graph)
            if final_state and "combined_results" in final_state:
                all_final_results.append(final_state["combined_results"])
                processed_count += 1
            else:
                error_msg = f"요구사항 '{req_data.get('description_name')}' 처리 후 'combined_results' 누락."
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
            error_msg = f"요구사항 '{req_data.get('description_name')}' 처리 중 오류: {str(e)}"
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

    print(f"처리 완료. 총 {processed_count}/{total_requirements}건 처리 성공. 오류: {len(error_list)}건.")
    return all_final_results
