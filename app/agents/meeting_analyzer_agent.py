# app/agents/meeting_analyzer_agent.py
import json
from typing import List, Dict, Any, Optional
from openai import OpenAI # 또는 app.services.llm_call_service 사용
from app.core.config import OPENAI_API_KEY, LLM_MODEL
from app.schemas.request import MeetingActionItem

# client = OpenAI(api_key=OPENAI_API_KEY) # 모듈 레벨 또는 함수 내에서 생성

def extract_actions_from_meeting_text(full_text: str) -> List[MeetingActionItem]:
    # 이전 답변에서 제안된 `extract_actions_from_meeting_agent` 함수 로직과 유사
    # OpenAI 클라이언트 인스턴스를 외부에서 주입받거나 여기서 생성
    client_instance = OpenAI(api_key=OPENAI_API_KEY) # 예시로 여기서 생성

    prompt = f"""
당신은 회의록을 분석하여 시스템 요구사항의 변경, 추가, 삭제와 관련된 논의 사항을 식별하는 전문가입니다.
다음 회의록 텍스트에서 각 논의 사항에 대해 다음 정보를 포함하는 JSON 객체들의 리스트로 반환해주세요.
응답은 "action_items"라는 키를 가진 JSON 객체여야 하며, 이 키의 값은 아래 구조를 따르는 객체들의 리스트입니다:
- "action_type": "추가", "변경", "삭제" 중 하나여야 합니다.
- "description_name": 회의에서 논의된 요구사항의 핵심 내용을 간결한 명사형 제목으로 작성합니다. (예: "실시간 알림 기능 개선")
- "details": 회의에서 논의된 구체적인 내용입니다. (예: "기존 알림 방식이 사용자에게 도달하지 않는 문제가 있어, 푸시 알림 외 이메일 알림도 추가하기로 함.")
- "reason": 해당 액션(추가/변경/삭제)이 필요한 이유입니다. (예: "사용자 피드백 반영 및 시스템 안정성 향상")
- "raw_text_from_meeting": 회의록에서 이 정보를 추출한 근거가 되는 원본 문맥 또는 핵심 구절입니다.

만약 해당하는 내용이 없다면 "action_items" 키의 값으로 빈 리스트 `[]`를 반환합니다.
일반적인 인사, 참석자 소개, 다음 회의 일정 안내 등 요구사항 변경과 직접 관련 없는 내용은 제외합니다.

회의록:
\"\"\"
{full_text}
\"\"\"
"""
    action_items_validated: List[MeetingActionItem] = []
    try:
        response = client_instance.chat.completions.create(
            model=LLM_MODEL,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": "당신은 회의록 분석 전문가입니다. 응답은 'action_items' 키를 가진 JSON 객체로, 그 값은 지정된 필드를 가진 객체들의 리스트여야 합니다."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1
        )
        content = response.choices[0].message.content.strip() if response.choices[0].message.content else "{}"
        
        # LLM이 마크다운 코드 블록으로 감싸서 반환하는 경우가 있으므로 제거
        if content.startswith("```json"):
            content = content[7:]
        if content.endswith("```"):
            content = content[:-3]
        
        data = json.loads(content)
        
        action_items_raw = data.get("action_items", [])
        if isinstance(action_items_raw, list):
            for item_dict in action_items_raw:
                try:
                    action_items_validated.append(MeetingActionItem(**item_dict))
                except Exception as e_pydantic: # Pydantic 유효성 검사 오류
                    print(f"MeetingActionItem 변환 실패: {item_dict}, 오류: {e_pydantic}")
            return action_items_validated
        else:
            print("LLM으로부터 'action_items' 리스트를 추출하지 못했습니다.")
            return []
            
    except json.JSONDecodeError as e:
        print(f"회의록 분석 JSON 파싱 오류: {e}, 응답: {content[:500]}")
        return []
    except Exception as e:
        print(f"회의록 분석 중 오류 (extract_actions_from_meeting_text): {e}")
        return []