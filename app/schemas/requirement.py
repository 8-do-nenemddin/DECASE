# app/schemas/requirement.py
from typing import TypedDict, Dict, Any, List
from pydantic import BaseModel

# LangGraph 상태 정의 (기존 코드 활용)
class RequirementAnalysisState(TypedDict, total=False):
    # Fields from your input JSON
    description_name: str
    type: str
    description_content: str
    target_task: str
    rfp_page: int
    processing_detail: str
    raw_text: str

    # Fields populated by LLM tasks
    id: str
    category_large: str
    category_medium: str
    category_small: str
    difficulty: str
    importance: str

    # Final aggregated output for each item
    combined_results: Dict[str, Any]


# FastAPI 요청 본문 모델 (단일 요구사항 처리용 - 현재 전체 파일 처리이므로 직접 사용 안 할 수 있음)
# class RequirementProcessRequest(BaseModel):
#     description_name: str
#     type: str
#     description_content: str
#     target_task: str
#     rfp_page: int
#     processing_detail: str

# 파일 처리 요청 모델
class FileProcessRequest(BaseModel):
    input_json_path: str
    output_json_path: str
    output_csv_path: str

# 처리 결과 응답 모델 (예시)
class RefineResponse(BaseModel):
    message: str
    output_json_file: str
    errors: List[str] = []

# 처리 결과 응답 모델
class ProcessResponse(BaseModel):
    message: str
    requirements: List[Dict[str, Any]]