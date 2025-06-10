import os
import traceback
from typing import List, Dict, Any

from app.schemas.requirement import RequirementAnalysisState
from app.core.config import INPUT_DIR, OUTPUT_CSV_DIR, OUTPUT_JSON_DIR
from app.services.id_management_service import RequirementIdManager

os.makedirs(INPUT_DIR, exist_ok=True)
os.makedirs(OUTPUT_CSV_DIR, exist_ok=True)
os.makedirs(OUTPUT_JSON_DIR, exist_ok=True)

def process_requirements_in_memory(
    requirements_to_process: List[Dict[str, Any]],
    compiled_app: Any
) -> List[Dict[str, Any]]:
    """
    백그라운드에서 LangGraph를 사용하여 요구사항을 처리하고, 고유 ID가 포함된 결과 리스트를 반환합니다.
    """
    print(f"요구사항 처리 시작: {len(requirements_to_process)}개 항목")
    
    if not requirements_to_process:
        print("처리할 요구사항이 없습니다.")
        return []

    all_final_results: List[Dict[str, Any]] = []
    total_requirements = len(requirements_to_process)

    for i, req_data in enumerate(requirements_to_process):
        print(f"\n[{i+1}/{total_requirements}] 처리 중: '{req_data.get('description_content', 'N/A')[:70]}...'")
        
        inputs_for_graph: RequirementAnalysisState = {
            "description_name": req_data.get("description_name", "내용 없음"),
            "type": req_data.get("type"),
            "description_content": req_data.get("description_content", "상세 내용 없음"),
            "target_task": req_data.get("target_task"),
            "rfp_page": req_data.get("rfp_page"),
            "processing_detail": req_data.get("processing_detail"),
            "raw_text": req_data.get("raw_text")
        }
        inputs_for_graph = {k: v for k, v in inputs_for_graph.items() if v is not None}

        try:
            # LangGraph 실행
            final_state = compiled_app.invoke(inputs_for_graph)
            
            # ❗❗❗ 핵심 수정 부분 ❗❗❗
            # LangGraph의 최종 결과물인 'combined_results' 딕셔너리 전체를 가져와야 합니다.
            if final_state and "combined_results" in final_state:
                # ✅ 올바른 방법: 'combined_results' 딕셔너리 전체를 추가
                all_final_results.append(final_state["combined_results"])
            else:
                # 오류 처리
                error_msg = f"요구사항 '{req_data.get('description_name')}' 처리 후 'combined_results' 누락."
                print(f"    ⚠️ {error_msg}")
                all_final_results.append({
                    **inputs_for_graph, 
                    "error_processing": "combined_results_missing",
                    "id": "REQ-ERR-ERR-0000"
                })

        except Exception as e:
            # 예외 처리
            error_msg = f"요구사항 '{req_data.get('description_name')}' 처리 중 오류: {str(e)}"
            print(f"    ❌ {error_msg}")
            traceback.print_exc()
            all_final_results.append({
                **inputs_for_graph,
                "error_processing": str(e),
                "id": "REQ-ERR-ERR-0000"
            })

    print(f"\n처리 완료. 총 {len(all_final_results)}건의 결과 생성.")
    return all_final_results