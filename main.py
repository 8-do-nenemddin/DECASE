# app/main.py
from fastapi import FastAPI
from app.routers import process as process_router # process.py에서 정의한 라우터 임포트
from app.routers import asis as asis_router
from app.routers import description as description_router

app = FastAPI(
    title="RFP Analysis Service",
    description="RFP 문서를 분석하여 요구사항을 분류, 평가하고 SRS 문서를 생성하는 API",
    version="0.1.0"
)

# /api/v1 접두사와 함께 process 라우터 포함
app.include_router(process_router.router, prefix="/api/v1", tags=["RFP Processing"])
app.include_router(asis_router.router, prefix="/api/v1/as-is", tags=["As-Is Analysis"]) # 신규 라우터 추가
app.include_router(description_router.router, prefix="/api/v1/description", tags=["Requirement Description Generation"]) # 신규 라우터 추가

@app.get("/")
async def root():
    return {"message": "RFP Analysis Service에 오신 것을 환영합니다!"}

# 애플리케이션 상태 확인용 엔드포인트 (선택 사항)
@app.get("/health")
async def health_check():
    return {"status": "ok"}