# app/graph/rfp_graph.py
import concurrent.futures
from typing import Dict, Any
from langgraph.graph import StateGraph, END

from app.schemas.requirement import RequirementAnalysisState # 정의된 상태 모델 임포트
from app.agents.classification_agent import classify_requirement_agent
from app.agents.difficulty_agent import get_difficulty_agent
from app.agents.importance_agent import get_importance_agent

# --- LangGraph 노드 정의 ---
def node_parallel_assessments(state: RequirementAnalysisState) -> Dict[str, Any]:
    print(f"--- 병렬 평가 시작 for: {state.get('description', 'N/A')[:50]}... ---") # 로그 강화
    # 입력 JSON의 'responsible_module'을 LangGraph 상태의 'module'로 매핑하여 사용
    # 이 매핑은 main.py에서 app.invoke에 전달하는 inputs_for_graph 에서 이미 처리되었어야 합니다.
    # 여기서는 state에 이미 'module' 키가 있다고 가정합니다.
    description = state.get("description", "설명 없음")
    detailed_description = state.get("detailed_description", "상세 설명 없음")
    module_for_llm = state.get("module", "모듈 미지정") # LLM 프롬프트에 사용될 모듈명

    if not description or not module_for_llm:
        print(f"경고: description 또는 module이 비어있습니다. Description: '{description}', Module: '{module_for_llm}'")
        # 필수 값 누락 시 에러 처리 또는 기본값으로 진행 결정
        # 여기서는 예시로 에러 값을 포함한 결과를 반환
        return {
            "category_large": "Error: Missing description/module",
            "category_medium": "Error: Missing description/module",
            "category_small": "Error: Missing description/module",
            "difficulty": "Error: Missing description/module",
            "importance": "Error: Missing description/module",
        }

    classification_dict: Dict[str, str] = {}
    difficulty_str: str = ""
    importance_str: str = ""

    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        future_classify = executor.submit(classify_requirement_agent, description, detailed_description, module_for_llm)
        future_difficulty = executor.submit(get_difficulty_agent, description, detailed_description, module_for_llm)
        future_importance = executor.submit(get_importance_agent, description, detailed_description, module_for_llm)

        try:
            classification_dict = future_classify.result()
            print(f"    - 분류 완료 for: {description[:30]}...")
        except Exception as e:
            print(f"Error in future_classify.result(): {e}")
            classification_dict = {"category_large": "Error", "category_medium": "Error", "category_small": "Error"}

        try:
            difficulty_str = future_difficulty.result()
            print(f"    - 난이도 평가 완료 for: {description[:30]}...")
        except Exception as e:
            print(f"Error in future_difficulty.result(): {e}")
            difficulty_str = "Error"

        try:
            importance_str = future_importance.result()
            print(f"    - 중요도 평가 완료 for: {description[:30]}...")
        except Exception as e:
            print(f"Error in future_importance.result(): {e}")
            importance_str = "Error"
            
    print(f"--- 병렬 평가 완료 for: {state.get('description', 'N/A')[:50]} ---")
    return {
        "category_large": classification_dict.get("category_large", "미분류"),
        "category_medium": classification_dict.get("category_medium", "미분류"),
        "category_small": classification_dict.get("category_small", "미분류"),
        "difficulty": difficulty_str,
        "importance": importance_str,
    }

def node_combine_results(state: RequirementAnalysisState) -> Dict[str, Any]:
    print(f"--- 최종 결과 취합 중 for: {state.get('description', 'N/A')[:50]}... ---")
    combined_data_for_output: Dict[str, Any] = {}
    # 상태에 있는 모든 키를 combined_results로 옮김 (combined_results 자체는 제외)
    for key, value in state.items():
        if key != "combined_results":
            combined_data_for_output[key] = value
    
    # 'module' 키는 LLM 프롬프트용으로 사용되었으므로,
    # 만약 원본 'responsible_module'과 값이 다르다면, 최종 결과에는 둘 다 포함되거나 선택적으로 포함할 수 있습니다.
    # 현재는 RequirementAnalysisState에 responsible_module과 module이 둘 다 정의되어 있고,
    # node_parallel_assessments는 state["module"]을 사용하므로,
    # main.py에서 inputs_for_graph 생성 시 state["module"]에 적절한 값을 매핑하는 것이 중요합니다.
    # 이 node_combine_results는 state에 있는 그대로를 combined_data_for_output에 담습니다.

    print(f"--- 최종 결과 취합 완료 for: {state.get('description', 'N/A')[:50]} ---")
    return {"combined_results": combined_data_for_output}

# 그래프 빌더 생성
workflow = StateGraph(RequirementAnalysisState)

# 노드 추가
workflow.add_node("parallel_processor", node_parallel_assessments)
workflow.add_node("final_combiner", node_combine_results)

# 엣지 연결
workflow.set_entry_point("parallel_processor")
workflow.add_edge("parallel_processor", "final_combiner")
workflow.add_edge("final_combiner", END)

# 그래프 컴파일
# 애플리케이션 시작 시 한 번 컴파일하여 재사용
compiled_rfp_app = workflow.compile()

# 이 함수를 통해 컴파일된 앱 인스턴스를 가져올 수 있도록 합니다.
def get_rfp_graph_app():
    return compiled_rfp_app