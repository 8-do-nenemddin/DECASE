# app/services/classification_service.py
from openai import OpenAI
from typing import Dict
from app.core.config import OPENAI_API_KEY, LLM_MODEL

client = OpenAI(api_key=OPENAI_API_KEY)

def generate_classification_prompt_text(description: str, detailed_description: str, module: str) -> str:
    return f"""
당신은 차세대 정보시스템 구축 프로젝트에서 요구사항을 분석하고, 아래 기준에 따라 대분류, 중분류, 소분류를 분류하는 전문가입니다.

다음 요구사항 설명을 읽고 각 분류 항목에 맞게 분류해 주세요:

[요구사항 설명]
{description}

[상세 설명]
{detailed_description}

[담당 모듈]
{module}

[분류 기준]
1. **대분류**: 차세대 정보시스템 업무 수준
   예시: 수신, 여신, 부대/대행, 통합고객 등

2. **중분류**: 단위업무 시스템 수준
   예시: 예금, 신탁, 상담신청, 심사승인 등

3. **소분류**: 단위업무 시스템 하위 수준 (업무 프로세스 3~4레벨)
   ※ 소분류는 3레벨 분류가 어려운 경우 선택적으로 작성해도 무방함

아래 형식으로 정확히 출력하세요 (불필요한 설명 없이):

대분류: <텍스트>
중분류: <텍스트>
소분류: <텍스트 또는 '해당 없음'>

※ 유의사항:
- 반드시 대분류 → 중분류 → 소분류 순으로 작성
- 각 분류명은 명확하고 직관적인 한국어 명사형 표현을 사용할 것
- 기존 분류 체계가 없으므로, 의미적으로 유사한 요구사항끼리 논리적으로 묶어서 계층화할 것
- 불필요한 설명 없이 위 형식만 출력
"""

def classify_requirement_agent(description: str, detailed_description: str, module: str) -> Dict[str, str]:
    prompt = generate_classification_prompt_text(description, detailed_description, module)
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