# app/schemas/faiss_schemas.py
from pydantic import BaseModel
from typing import Optional, List

class CreateFaissIndexRequest(BaseModel):
    input_json_filename: str # INPUT_JSON_DIR 내에 위치한 파일명
    output_index_name: Optional[str] = None # 생성될 FAISS 인덱스 파일명 (확장자 제외)
    output_metadata_name: Optional[str] = None # 생성될 메타데이터 파일명 (확장자 제외)

class FaissIndexCreationResponse(BaseModel):
    message: str
    task_id: str
    index_file_path: Optional[str] = None # 백그라운드 작업 시에는 None 또는 예상 경로
    metadata_file_path: Optional[str] = None # 백그라운드 작업 시에는 None 또는 예상 경로