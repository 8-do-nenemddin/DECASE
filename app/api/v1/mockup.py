import os
import io
import zipfile
from typing import List
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from app.services.mockup_service import run_mockup_generation_pipeline
from urllib.parse import quote
import json
import httpx
from fastapi import BackgroundTasks

router = APIRouter()

class RequirementItem(BaseModel):
    description_name: str
    type: str
    description_content: str
    target_task: str
    rfp_page: int
    processing_detail: str
    category_large: str
    category_medium: str
    category_small: str
    difficulty: str
    importance: str

class MockupRequest(BaseModel):
    requirements: List[RequirementItem]
    output_folder_name: str = None
    project_id: int
    revision_count: int
    callback_url: str

@router.post("/generate-mockup")
async def generate_mockup_endpoint(
    request: MockupRequest,
    background_tasks: BackgroundTasks
):
    try:
        # 요구사항 데이터를 JSON 문자열로 변환 (UTF-8 인코딩 사용)
        input_data = json.dumps([req.dict() for req in request.requirements], ensure_ascii=False, indent=2)

        # 비동기로 콜백 호출
        background_tasks.add_task(
            send_callback,
            input_data=input_data,
            request=request
        )
        return {"message": "목업 생성 및 콜백 요청이 시작되었습니다."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"목업 생성 실패: {str(e)}")
    
async def send_callback(input_data: str, request: MockupRequest):
    # 목업 생성 및 zip 파일 생성
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        # 목업 생성 파이프라인 실행 및 결과를 zip에 추가
        mockup_files = run_mockup_generation_pipeline(input_data, request.output_folder_name)
        for file_path, file_content in mockup_files:
            # 파일 내용을 UTF-8로 인코딩하여 zip에 추가
            zip_file.writestr(file_path, file_content.encode('utf-8'))
        
    zip_buffer.seek(0)

    # 파일명 생성 및 인코딩
    filename = f"mockup_{request.output_folder_name or 'result'}.zip"
    encoded_filename = quote(filename.encode('utf-8'))

    async with httpx.AsyncClient() as client:
        files = {
            "mockUpZip": ({encoded_filename}, zip_buffer.getvalue, "application/zip"),
        }
        data = {
            "revisionCount": str(request.revision_count),
            "status": "SUCCESS"
        }
        params = {"projectId": request.project_id}
        try:
            await client.post(request.callback_url, params=params, data=data, files=files, timeout=60)
        except Exception as e:
            # 실패시 로깅 등 처리
            pass
    