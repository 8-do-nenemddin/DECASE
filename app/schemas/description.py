# app/schemas/description.py (또는 app/schemas/requirement.py에 추가)
from pydantic import BaseModel
from typing import List, Optional

class DescriptionGenerationBatchResponse(BaseModel):
    message: str
    input_filename: str
    output_filename: str # 서버에 저장된 결과 파일명
    total_requirements_in_file: int
    processed_requirements: int
    errors_count: int
    # output_file_path: Optional[str] = None # 실제 서버 경로보다는 파일명만 반환하는 것이 일반적