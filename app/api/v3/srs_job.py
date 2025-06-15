import uuid
import asyncio
from fastapi import APIRouter, HTTPException
from app.api.v2.jobs import job_store


router = APIRouter()

@router.get("/srs-agent/{job_id}/status")
async def get_srs_status(job_id: str):
    """
    요구사항 분석 상태 조회
    """
    if job_id not in job_store:
        raise HTTPException(status_code=404, detail="Job not found")
    job = job_store[job_id]
    return {
        "job_id": job_id,
        "state": job["status"],
        "message": job.get("message", ""),
    }

@router.get("/srs-agent/latest-status")
async def get_latest_srs_status_by_project_member(
    project_id: int,
    member_id: int,
    job_name: str = "SRS"
):
    """
    project_id, member_id, job_name으로 가장 최신 SRS 분석 작업의 상태와 job_id 반환
    """
    filtered_jobs = [
        (job_id, job)
        for job_id, job in job_store.items()
        if job.get("project_id") == project_id and job.get("member_id") == member_id and job.get("job_name", "SRS") == job_name and "start_time" in job
    ]
    if not filtered_jobs:
        raise HTTPException(status_code=404, detail="해당 project_id, member_id, job_name에 대한 작업이 없습니다.")
    latest_job_id, latest_job = max(
        filtered_jobs,
        key=lambda x: x[1]["start_time"]
    )
    return {
        "job_id": latest_job_id,
        "status": latest_job["status"],
        "message": latest_job.get("message", "")
    } 