# app/schemas/requirement.py
from typing import TypedDict, Dict, Any, List, Optional
from pydantic import BaseModel

# LangGraph 상태 정의 (기존 코드 활용)
class RequirementAnalysisState(TypedDict, total=False):
    # Fields from your input JSON
    id: str
    type: str
    description: str
    detailed_description: str
    acceptance_criteria: str
    responsible_module: str
    parent_id: str
    source_pages: List[int]

    # module 필드는 LLM 함수에 전달될 책임 모듈을 의미합니다.
    # 입력 JSON의 responsible_module을 이 필드로 매핑하여 사용합니다.
    module: str # LLM 함수용

    # Fields populated by LLM tasks
    category_large: str
    category_medium: str
    category_small: str
    difficulty: str
    importance: str

    # Final aggregated output for each item
    combined_results: Dict[str, Any]


# FastAPI 요청 본문 모델 (단일 요구사항 처리용 - 현재 전체 파일 처리이므로 직접 사용 안 할 수 있음)
class RequirementProcessRequest(BaseModel):
    id: str
    type: Optional[str] = None
    description: str
    detailed_description: Optional[str] = ""
    acceptance_criteria: Optional[str] = None
    responsible_module: Optional[str] = "미지정"
    parent_id: Optional[str] = None
    source_pages: Optional[List[int]] = None

# 파일 처리 요청 모델
class FileProcessRequest(BaseModel):
    input_json_path: str
    output_json_path: str
    output_csv_path: str

# 처리 결과 응답 모델 (예시)
class ProcessResponse(BaseModel):
    message: str
    output_json_file: str
    output_csv_file: str
    total_processed: int
    errors: List[str] = []