# app/schemas/requirement.py
from typing import TypedDict, Dict, Any, List
from pydantic import BaseModel

# LangGraph 상태 정의
class RequirementAnalysisState(TypedDict, total=False):
    id: str
    description_name: str
    type: str
    description_content: str
    target_task: str
    processing_detail: str
    category_large: str
    category_medium: str
    category_small: str
    difficulty: str
    importance: str
    rfp_page: int
    raw_text: str

    combined_results: Dict[str, Any]

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