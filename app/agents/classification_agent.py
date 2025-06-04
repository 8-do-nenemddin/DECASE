# app/services/classification_service.py
from openai import OpenAI
from typing import Dict
from app.core.config import OPENAI_API_KEY, LLM_MODEL

client = OpenAI(api_key=OPENAI_API_KEY)

def generate_classification_prompt_text(description_name: str, description_content: str, target_task: str) -> str:
    return f"""
당신은 공공 및 민간 부문 정보시스템 구축 프로젝트에서 요구사항을 분석하고, 다음 기준에 따라 대분류, 중분류, 소분류를 분류하는 전문가입니다.

요구사항 설명을 읽고, 각 요구사항이 어떤 업무 기능 또는 시스템 영역에 속하는지 **계층적으로 분류**해 주세요.

[요구사항 명]
{description_name}

[상세 설명]
{description_content}

[대상업무]
{target_task}

[분류 기준]
1. **대분류**: 서비스 또는 시스템 영역 수준에서의 가장 큰 범주입니다. 주요 업무 또는 시스템 모듈 수준을 대표하는 범주입니다.
   예시: 기업뱅킹, 사용자관리, 콘텐츠관리, 데이터분석, 외부연계, 시스템운영 등

2. **중분류**: 대분류 하위의 단위 시스템 또는 기능 영역입니다.
   예시: 회원가입, 콘텐츠 업로드, 자동이체, 통계 대시보드, API 관리, 접근제어 등

3. **소분류**: 기능 세부 수준으로, 화면 또는 단일 기능 단위와 1:1로 매핑됩니다.
   예시: 이메일 인증 처리, 자동이체 해제, 게시판 댓글 등록, 월간 방문자 수 집계 등

[출력 형식]
대분류: <텍스트>
중분류: <텍스트>
소분류: <텍스트 또는 '해당 없음'>

[작성 지침]
- 반드시 **대분류 → 중분류 → 소분류** 순서로 작성하세요.
- 각 분류명은 **명확하고 직관적인 명사형 표현**으로 작성하세요.
- 설명은 생략하고, 지정된 출력 형식만 제공하세요.
- 기존 표준 체계가 없더라도 **요구사항의 의미와 맥락에 따라 논리적으로 계층화**해 주세요.
- 소분류는 해당하는 하위 기능이 없거나 불분명한 경우 "해당 없음"으로 작성하세요.
- 띄어쓰기와 문장 부호에 주의하여, **명확하고 일관된 표현**을 사용하세요.
"""

def classify_requirement_agent(description_name: str, description_content: str, target_task: str) -> Dict[str, str]:
    prompt = generate_classification_prompt_text(description_name, description_content, target_task)
    try:
        response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": "당신은 소프트웨어 분석 및 분류 전문가입니다."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3
        )
        content = response.choices[0].message.content or ""
        lines = [line.strip() for line in content.splitlines() if ":" in line]

        def extract_value(prefix):
            for line in lines:
                if line.startswith(prefix):
                    parts = line.split(":", 1)
                    if len(parts) == 2:
                        return parts[1].strip()
            return "미분류"

        return {
            "category_large": extract_value("대분류"),
            "category_medium": extract_value("중분류"),
            "category_small": extract_value("소분류"),
        }
    except Exception as e:
        print(f"Error in classify_requirement_agent: {e}")
        return {
            "category_large": "Error",
            "category_medium": "Error",
            "category_small": "Error"
        }