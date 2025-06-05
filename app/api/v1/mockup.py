import os

from fastapi import APIRouter, UploadFile, File, Form, BackgroundTasks, HTTPException
from app.services.mockup_service import run_mockup_generation_pipeline
from app.schemas.mockup import MockupResponse
from app.core.config import (
    INPUT_DIR
)

router = APIRouter()

@router.post("/generate-mockup", response_model=MockupResponse)
async def generate_mockup_endpoint(
    background_tasks: BackgroundTasks,
    input_file: UploadFile = File(...),
    output_folder_name: str = Form(None),
):
    if not input_file.filename.endswith(".json"):
        raise HTTPException(status_code=400, detail="잘못된 파일 형식입니다. JSON 파일을 업로드해주세요.")

    # 입력 파일 저장
    input_file_path = os.path.join(INPUT_DIR, f"input_{input_file.filename}")
    try:
        with open(input_file_path, "wb") as buffer:
            buffer.write(await input_file.read())
        print(f"입력 파일 임시 저장: {input_file_path}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"입력 파일 저장 실패: {str(e)}")
    
    background_tasks.add_task(run_mockup_generation_pipeline, input_file_path, output_folder_name)

    return MockupResponse(
        message="목업 생성 요청이 접수되었습니다. 백그라운드에서 처리가 시작됩니다.",
        folder_name=output_folder_name or "자동생성됨"
    )