import os

from fastapi import APIRouter, HTTPException, BackgroundTasks, UploadFile, File, Form

from app.schemas.requirement import ProcessResponse
from app.graph.rfp_graph import get_rfp_graph_app
from app.services.background_processing_service_copy import background_process_and_save
from app.core.config import (
    INPUT_DIR,
    OUTPUT_CSV_DIR,
    OUTPUT_JSON_DIR
)

router = APIRouter()
compiled_app = get_rfp_graph_app()

@router.post("/process", response_model=ProcessResponse)
async def process_rfp_file_endpoint(
    background_tasks: BackgroundTasks,
    input_file: UploadFile = File(..., description="분석할 요구사항이 담긴 JSON 파일"),
    output_json_filename: str = Form("processed_requirements.json", description="출력될 JSON 파일명"),
    output_csv_filename: str = Form("final_srs.csv", description="출력될 CSV 파일명")
):
    """
    RFP JSON 파일을 업로드 받아 요구사항을 분석하고, 
    처리된 JSON 파일과 최종 SRS CSV 파일을 생성합니다.
    """
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

    # 출력 파일 경로 설정 (보안을 위해 파일명 검증/정제 필요)
    # 여기서는 간단히 OUTPUT_DIR 사용
    safe_output_json_filename = os.path.basename(output_json_filename) # 경로 조작 방지
    safe_output_csv_filename = os.path.basename(output_csv_filename)   # 경로 조작 방지
    
    final_output_json_path = os.path.join(OUTPUT_JSON_DIR, safe_output_json_filename)
    final_output_csv_path = os.path.join(OUTPUT_CSV_DIR, safe_output_csv_filename)

    # 백그라운드 작업 추가
    background_tasks.add_task(
        background_process_and_save,
        input_file_path,
        final_output_json_path,
        final_output_csv_path,
        compiled_app
    )

    return ProcessResponse(
        message="파일 업로드 성공. 백그라운드에서 요구사항 분석 및 파일 생성을 시작합니다.",
        output_json_file=f"결과는 서버의 '{final_output_json_path}' 경로에 저장될 예정입니다.", # 실제로는 다운로드 URL 제공 등이 필요
        output_csv_file=f"결과는 서버의 '{final_output_csv_path}' 경로에 저장될 예정입니다.",
        errors=[]
    )

# (선택 사항) 결과 파일 다운로드 엔드포인트 (실제 운영 시 보안 및 권한 확인 필요)
# from fastapi.responses import FileResponse
# @router.get("/download/{filename}")
# async def download_file(filename: str):
#     file_path = os.path.join(OUTPUT_DIR, filename)
#     if os.path.exists(file_path):
#         return FileResponse(path=file_path, filename=filename, media_type='application/octet-stream')
#     raise HTTPException(status_code=404, detail="파일을 찾을 수 없습니다.")