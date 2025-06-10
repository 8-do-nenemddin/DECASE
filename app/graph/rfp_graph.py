# app/graph/rfp_graph.py

import concurrent.futures
from typing import Dict, Any
from langgraph.graph import StateGraph, END

from app.schemas.requirement import RequirementAnalysisState
from app.agents.classification_agent import classify_requirement_agent
from app.agents.difficulty_agent import get_difficulty_agent
from app.agents.importance_agent import get_importance_agent
# <<< 1. ID 매니저 임포트 >>>
from app.services.id_management_service import RequirementIdManager

# <<< 2. 모듈 레벨에서 ID 매니저 인스턴스 생성 >>>
# 이렇게 하면 애플리케이션이 실행되는 동안 상태(카운터)가 유지됩니다.
id_manager = RequirementIdManager()


# --- 1번 노드: 병렬 평가 (기존과 동일) ---
def node_parallel_assessments(state: RequirementAnalysisState) -> Dict[str, Any]:
    print(f"--- 병렬 평가 시작 for: {state.get('description_name', 'N/A')[:50]}... ---")
    description_name = state.get("description_name", "요구사항명 없음")
    description_content = state.get("description_content", "상세 설명 없음")
    target_task = state.get("target_task", "대상 업무 미지정")

    
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        future_classify = executor.submit(classify_requirement_agent, description_name, description_content, target_task)
        future_difficulty = executor.submit(get_difficulty_agent, description_name, description_content, target_task)
        future_importance = executor.submit(get_importance_agent, description_name, description_content, target_task)

        try:
            classification_dict = future_classify.result()
            print(f"    - 분류 완료 for: {description_name[:30]}...")
        except Exception as e:
            print(f"Error in future_classify.result(): {e}")
            classification_dict = {"category_large": "Error", "category_medium": "Error", "category_small": "Error"}

        try:
            difficulty_str = future_difficulty.result()
            print(f"    - 난이도 평가 완료 for: {description_name[:30]}...")
        except Exception as e:
            print(f"Error in future_difficulty.result(): {e}")
            difficulty_str = "Error"

        try:
            importance_str = future_importance.result()
            print(f"    - 중요도 평가 완료 for: {description_name[:30]}...")
        except Exception as e:
            print(f"Error in future_importance.result(): {e}")
            importance_str = "Error"
    
    print(f"--- 병렬 평가 완료 for: {state.get('description_name', 'N/A')[:50]} ---")
    return {
        "category_large": classification_dict.get("category_large", "미분류"),
        "category_medium": classification_dict.get("category_medium", "미분류"),
        "category_small": classification_dict.get("category_small", "미분류"),
        "difficulty": difficulty_str,
        "importance": importance_str,
    }


# <<< 3. 새로 추가된 2번 노드: ID 생성 >>>
def node_generate_id(state: RequirementAnalysisState) -> Dict[str, str]:
    """
    분류된 결과를 바탕으로 고유 ID를 생성하여 상태에 추가합니다.
    """
    print(f"--- ID 생성 시작 for: {state.get('description_name', 'N/A')[:50]}... ---")
    try:
        # 상태 정보를 ID 매니저에 전달하여 ID 문자열을 받음
        final_id = id_manager.generate_id(state)
        print(f"    - 생성된 ID: {final_id}")
        # LangGraph 규칙에 따라, 업데이트할 상태의 키와 값을 반환
        return {"id": final_id}
    except Exception as e:
        print(f"ID 생성 중 오류 발생: {e}")
        return {"id": "REQ-ERR-ERR-0000"}


# --- 3번 노드: 최종 결과 취합 (기존과 동일) ---
def node_combine_results(state: RequirementAnalysisState) -> Dict[str, Any]:
    print(f"--- 최종 결과 취합 중 for: {state.get('description_name', 'N/A')[:50]}... ---")
    combined_data_for_output: Dict[str, Any] = {}
    for key, value in state.items():
        if key != "combined_results":
            combined_data_for_output[key] = value

    print(f"--- 최종 결과 취합 완료 for: {state.get('description_name', 'N/A')[:50]} ---")
    return {"combined_results": combined_data_for_output}


# <<< 4. 그래프 빌더 및 엣지 연결 수정 >>>
workflow = StateGraph(RequirementAnalysisState)

# 노드 추가
workflow.add_node("parallel_processor", node_parallel_assessments)
workflow.add_node("id_generator", node_generate_id) # 새 노드 추가
workflow.add_node("final_combiner", node_combine_results)

# 엣지 연결 (데이터 흐름 정의)
workflow.set_entry_point("parallel_processor")
workflow.add_edge("parallel_processor", "id_generator") # 평가 후 ID 생성으로 이동
workflow.add_edge("id_generator", "final_combiner")   # ID 생성 후 결과 취합으로 이동
workflow.add_edge("final_combiner", END)

# 그래프 컴파일
compiled_rfp_app = workflow.compile()

# 컴파일된 앱 인스턴스 반환 함수
def get_rfp_graph_app():
    return compiled_rfp_app