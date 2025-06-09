# app/schemas/change_request_schemas.py
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

class MeetingActionItem(BaseModel):
    action_type: str # "추가", "변경", "삭제"
    description_name: str # 회의록에서 논의된 요구사항의 핵심 명칭
    details: str # 회의록에서 논의된 구체적인 내용
    reason: Optional[str] = None # 해당 액션이 필요한 이유
    raw_text_from_meeting: str # 회의록 원본 문맥

class ChangeRequestResultItem(BaseModel):
    original_requirement_id: Optional[str] = None # 변경/삭제 시 매칭된 기존 요구사항 ID
    original_description_name: Optional[str] = None # 변경/삭제 시 매칭된 기존 요구사항명
    action_type: str # "추가", "변경", "삭제"
    updated_description_name: Optional[str] = None # 추가/변경 시 새로운 또는 변경된 요구사항명
    details_from_meeting: str
    reason_for_change: Optional[str] = None
    status: str # 예: "신규 제안", "변경 제안", "삭제 제안", "검토 필요"
    raw_text_from_meeting: str
    similarity_score: Optional[float] = None # 변경/삭제 시 유사도 점수
    # 추가적으로 필요한 필드 (예: 담당자, 우선순위 등)를 정의할 수 있음

class ProcessMeetingRequest(BaseModel):
    meeting_minutes_text: Optional[str] = None # 직접 텍스트를 전달하는 경우
    meeting_minutes_filename: Optional[str] = None # 서버에 업로드된 회의록 파일명
    faiss_index_name: str # 사용할 FAISS 인덱스 파일명 (확장자 제외)
    metadata_name: str # 사용할 메타데이터 파일명 (확장자 제외)
    top_k_search: Optional[int] = 1 # 유사도 검색 시 상위 K개 결과

class ProcessMeetingResponse(BaseModel):
    message: str
    task_id: Optional[str] = None # 백그라운드 처리 시
    change_requests: Optional[List[ChangeRequestResultItem]] = None
    error: Optional[str] = None