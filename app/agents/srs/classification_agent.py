import json
from openai import OpenAI
from typing import Dict
from app.core.config import OPENAI_API_KEY, LLM_MODEL

# 모듈 레벨에서 클라이언트 인스턴스 생성
client = OpenAI(api_key=OPENAI_API_KEY)


def generate_classification_only_prompt(description_name: str, description_content: str, target_task: str) -> str:
    """
    요구사항 분류(대/중/소)를 위한 LLM 프롬프트를 생성합니다.
    """
    return f"""
당신은 요구사항을 분석하고, 지정된 규칙에 따라 구조화된 JSON 데이터를 생성하는 매우 정확하고 체계적인 시스템 분석 전문가입니다.

**수행할 작업:**
주어진 요구사항 정보를 바탕으로 다음 규칙과思考 과정을 거쳐 최종 JSON 객체를 생성해야 합니다.

1.  **한글 분류**: 요구사항 내용을 분석하여 [분류 기준]과 [소분류 결정 심화 지침]에 따라 '대분류', '중분류', '소분류'를 한글로 결정합니다.
2.  **최종 JSON 출력**: 결정된 한글 분류명들을 지정된 JSON 형식에 맞춰 최종적으로 반환합니다.

**분석할 요구사항 정보:**
[요구사항 명]
{description_name}

[상세 설명]
{description_content}

[대상업무]
{target_task}

**[분류 기준]**
1.  **대분류**: 서비스 또는 시스템 영역 수준의 가장 큰 범주. (예: 기업뱅킹, 사용자관리, 콘텐츠관리)
2.  **중분류**: 대분류 하위의 단위 시스템 또는 기능 영역. (예: 회원가입, 콘텐츠 업로드, 자동이체)
3.  **소분류**: 중분류 기능을 구성하는 가장 작은 단위의 기능. (상세 내용은 아래 심화 지침 참조)

**[소분류 결정 심화 지침]**
이것은 가장 중요한 규칙입니다. 반드시 따르십시오.

1.  **기능(Function)의 정의**: 소분류는 반드시 '명사'가 아닌 '동사' 중심의 명확한 **동작(Action) 또는 프로세스**여야 합니다.
    - **좋은 예시**: `아이디 중복 확인`, `약관 동의 처리`, `본인 인증 요청`, `가입 정보 유효성 검사`
    - **나쁜 예시**: `이메일, 비밀번호 입력`, `사용자 정보`, `가입 화면` (이것들은 기능이 아니라 데이터 항목 또는 UI 설명임)

2.  **계층 구조의 원칙**: 소분류는 항상 중분류의 하위 단계여야 합니다.
    - 만약, [상세 설명]의 내용이 '중분류'로 정의된 기능 전체를 포괄적으로 설명하고 있으며, 그 안에서 더 작은 단위의 기능으로 나눌 수 없다면, 소분류는 **반드시 "해당 없음"**으로 지정해야 합니다.
    - 예를 들어, 중분류가 '회원가입'인데 상세 설명이 "사용자가 이메일, 비밀번호로 가입한다" 라면, 이는 '회원가입' 기능 자체를 설명하는 것이므로 소분류는 "해당 없음"입니다.

3.  **데이터 필드 나열 금지**: [상세 설명]에 언급된 데이터 필드(예: 이름, 이메일, 주소)를 **절대로 그대로 나열하지 마십시오.** 그것은 기능이 아닙니다.

**[최종 출력 형식]**
思考 과정은 응답에 포함하지 말고, 반드시 아래 키를 가진 최종 JSON 객체만 반환해야 합니다. 다른 어떤 설명도 추가하지 마십시오.
{{
  "category_large": "<결정된 한글 대분류>",
  "category_medium": "<결정된 한글 중분류>",
  "category_small": "<결정된 한글 소분류 또는 '해당 없음'>"
}}
"""

def classify_requirement_agent(description_name: str, description_content: str, target_task: str) -> Dict[str, str]:
    """
    LLM을 통해 요구사항을 대/중/소 카테고리로 분류합니다.
    """
    classification_prompt = generate_classification_only_prompt(description_name, description_content, target_task)
    
    try:
        response = client.chat.completions.create(
            model=LLM_MODEL,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": "You are a highly structured system analyst. Your output must be a single, valid JSON object as specified."},
                {"role": "user", "content": classification_prompt}
            ],
            temperature=0.2
        )
        
        classification_result = json.loads(response.choices[0].message.content or "{}")
        
        # 최종 결과 조합
        final_result = {
            "category_large": classification_result.get("category_large", "미분류"),
            "category_medium": classification_result.get("category_medium", "미분류"),
            "category_small": classification_result.get("category_small", "해당 없음"),
        }
        return final_result

    except Exception as e:
        print(f"classify_requirement_agent에서 오류 발생: {e}")
        # 오류 발생 시, ID 관련 키 없이 분류 필드만 에러로 반환
        return {
            "category_large": "Error",
            "category_medium": "Error",
            "category_small": "Error"
        }