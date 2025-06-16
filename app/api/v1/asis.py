# app/api/v1/asis.py
import os
import shutil
import uuid
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse

# 수정된 서비스와 설정 파일을 가져옵니다.
from app.services.background_asis_services import process_asis_report
# from app.services.background_asis_services import process_asis_document
from app.core import config

router = APIRouter()

# @router.post("/as-is/start-analysis")
# async def start_as_is_analysis(
#     background_tasks: BackgroundTasks,
#     file: UploadFile = File(..., description="분석할 RFP PDF 파일")
# ):
#     """
#     AS-IS 분석을 위한 PDF 파일을 업로드합니다.
#     분석은 백그라운드에서 실행되며, 작업이 시작되었음을 즉시 응답합니다.
#     """
#     if file.content_type != "application/pdf":
#         raise HTTPException(status_code=400, detail="PDF 파일만 업로드할 수 있습니다.")

#     # 업로드된 파일을 서버의 임시 공간에 저장합니다.
#     # 파일명을 고유하게 만들어 동시 요청 시 겹치지 않도록 합니다.
#     temp_filename = f"{uuid.uuid4()}_{file.filename}"
#     temp_file_path = os.path.join(config.INPUT_DIR, temp_filename)

#     try:
#         # INPUT_DIR 디렉토리가 없으면 생성합니다.
#         os.makedirs(config.INPUT_DIR, exist_ok=True)
        
#         # 파일을 임시 경로에 저장합니다.
#         with open(temp_file_path, "wb") as buffer:
#             shutil.copyfileobj(file.file, buffer)

#         # 시간이 오래 걸리는 파일 처리 작업을 백그라운드 태스크로 추가합니다.
#         # process_asis_document 함수는 이제 파일 경로를 인자로 받습니다.
#         background_tasks.add_task(
#             process_asis_document,
#             file_path=temp_file_path,
#             file_type=file.content_type
#         )

#         # 사용자에게는 작업이 시작되었음을 바로 알립니다.
#         return JSONResponse(
#             status_code=202, # 202 Accepted: 요청이 접수되었으며 처리가 시작됨
#             content={
#                 "message": "AS-IS 문서 분석 작업이 시작되었습니다. 완료되면 서버의 지정된 경로에 결과가 저장됩니다.",
#                 "uploaded_file": file.filename,
#             }
#         )

#     except Exception as e:
#         # 파일 저장 등 초기 단계에서 오류 발생 시
#         raise HTTPException(status_code=500, detail=f"파일 처리 준비 중 오류 발생: {str(e)}")
#     finally:
#         # file.file 객체는 FastAPI가 관리하므로 여기서 닫지 않아도 됩니다.
#         pass


# === OpenAI(GPT)용 엔드포인트 추가 ===
@router.post("/as-is/start-analysis")
async def start_as_is_analysis_openai(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="OpenAI(GPT)로 분석할 RFP PDF 파일")
):
    """
    AS-IS 분석을 위한 PDF 파일을 업로드합니다. (OpenAI/GPT 사용)
    분석은 백그라운드에서 실행되며, 작업이 시작되었음을 즉시 응답합니다.
    """
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="PDF 파일만 업로드할 수 있습니다.")

    temp_filename = f"{uuid.uuid4()}_{file.filename}"
    temp_file_path = os.path.join(config.INPUT_DIR, temp_filename)

    try:
        os.makedirs(config.INPUT_DIR, exist_ok=True)
        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # GPT용 백그라운드 태스크를 추가합니다.
        background_tasks.add_task(
            process_asis_report,
            file_path=temp_file_path,
            file_type=file.content_type
        )

        return JSONResponse(
            status_code=202,
            content={
                "message": "AS-IS 문서 분석 작업(OpenAI)이 시작되었습니다. 완료되면 서버의 지정된 경로에 결과가 저장됩니다.",
                "uploaded_file": file.filename,
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"파일 처리 준비 중 오류 발생: {str(e)}")
