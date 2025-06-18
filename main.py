# app/main.py
from fastapi import FastAPI
from app.api.v1 import description as description_router
from app.api.v1 import refine as refine_router
from app.api.v1 import mockup as mockup_router
from app.api.v1 import faiss as faiss_router
from app.api.v1 import request as request_router
from app.api.v3 import asis_job as asis_job_router
from app.api.v3 import srs_job as srs_job_router
from app.api.v3 import srs_db as srs_router # process.py에서 정의한 라우터 임포트
from app.api.v3 import asis_db as asis_router

app = FastAPI(
    title="RFP Analysis Service",
    description="RFP 문서를 분석하여 요구사항을 분류, 평가하고 SRS 문서를 생성하는 API",
    version="0.1.0",
    root_path='/ai/api/v1/decase'
)

# /ai/api/v1 접두사와 함께 process 라우터 포함
app.include_router(srs_router.router, prefix="/ai/api/v1/requirements", tags=["SRS"])
app.include_router(refine_router.router, prefix="/ai/api/v1/requirements", tags=["SRS"]) 
app.include_router(asis_router.router, prefix="/ai/api/v1/requirements", tags=["As-Is"]) 
# app.include_router(description_router.router, prefix="/api/v1", tags=["Requirement Description Generation"]) # 신규 라우터 추가
app.include_router(mockup_router.router, prefix="/ai/api/v1/mockup", tags=["Mockup"]) # 추가
app.include_router(faiss_router.router, prefix="/ai/api/v1/faiss", tags=["FAISS-Indexing"]) # 새 라우터 추가
app.include_router(request_router.router, prefix="/ai/api/v1/request", tags=["Update Request"]) # 새 라우터 추가
app.include_router(asis_job_router.router, prefix="/ai/api/v1/jobs", tags=["As-Is"])  # AS-IS 분석 작업 상태 확인 라우터
app.include_router(srs_job_router.router, prefix="/ai/api/v1/jobs", tags=["SRS"])  # SRS 분석 작업 상태 확인 라우터

@app.get("/")
async def root():
    return {"message": "RFP Analysis Service에 오신 것을 환영합니다!"}

# 애플리케이션 상태 확인용 엔드포인트 (선택 사항)
@app.get("/health")
async def health_check():
    return {"status": "ok"}