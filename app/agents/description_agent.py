# app/agents/description_agent_service.py
from openai import OpenAI
from typing import Optional
from app.core.config import OPENAI_API_KEY, LLM_MODEL # LLM_MODEL_FOR_DESCRIPTION 등으로 구분 가능

# client는 필요에 따라 함수 내에서 생성하거나, 의존성 주입을 통해 관리할 수 있습니다.
# 여기서는 각 함수 호출 시 생성하는 것으로 가정합니다.

def generate_detailed_prompt_text(description: str, snippet: Optional[str], module: Optional[str]) -> str:
    """
    LLM에게 전달할 상세 설명 생성용 프롬프트를 생성합니다.
    description_agent.ipynb의 generate_detailed_prompt 함수 내용을 기반으로 합니다.
    """
    description_val = description if description else "요구사항 명칭 누락"
    snippet_val = snippet if snippet else "관련 원문 스니펫 정보 없음"
    module_val = module if module else "담당 모듈 미지정"

    # description_agent.ipynb의 generate_detailed_prompt 함수 내 prompt f-string 부분 전체를 여기에 붙여넣습니다.
    prompt = f"""
당신은 금융 정보 시스템 구축 프로젝트의 수석 시스템 분석가(SA)입니다. 당신의 임무는 주어진 간략한 요구사항 정보를 바탕으로, 개발팀이 즉시 상세 설계 및 개발에 착수할 수 있도록 매우 구체적이고, 체계적이며, 완전한 '상세 설명'을 작성하는 것입니다.

현재 작성해야 할 요구사항의 기본 정보는 다음과 같습니다:
- [요구사항 명칭]: {description_val}
- [관련 원문 스니펫]: {snippet_val}
- [예상 담당 모듈]: {module_val}

아래 형식에 따라 이 요구사항에 대한 상세 설명을 작성해 주세요.

□ 요구사항은 아래 내용을 참조로 도출하며, 요구사항, 대상업무, 요건처리 상세의 형식으로 작성 사례를 참조하여 작성함
1) 요구사항 도출을 위한 기초자료
   - PI 사업을 통해 도출된 산출물
   - 현행 시스템을 분석한 현행시스템분석서
   - 사업수행계획서, RFP, 인터뷰 결과서

2) 작성 방법 (신규/개선 요구사항 기준)
[요구사항]
- 요구사항 내용을 간결하게 기술합니다.
[대상업무]
- 요구사항이 반영될 대상 업무를 기술하고, 구현되는 기능 유형(예: 화면, 온라인, 배치 등)을 명시합니다.
[요건처리 상세]
- 해당 요구사항을 어떻게 처리할지 구체적으로 기술합니다. (예: 어떤 데이터를 어떤 기준으로 계산하고 어디에 표시하는지, 흐름 중심의 처리 방식 등)

예시:
[요구사항]
영업부점에서 등록한 지준이체예상보고 데이터를 기준으로 입출금 내역을 집계한다.
[대상업무]
자금결제관리 - 화면 기능
[요건처리 상세]
지준이체예상보고서에 등록된 입금/출금 데이터를 수집하여 이체사유별로 당일 집계금액을 계산하고, 사용자가 조회 가능한 화면에 표출한다.

※ 반드시 위와 같은 형식으로만 응답해 주세요.
"""
    return prompt

def get_detailed_description_from_llm(description: str, snippet: Optional[str], module: Optional[str]) -> str:
    """
    OpenAI API를 호출하여 상세 설명을 생성합니다.
    description_agent.ipynb의 get_detailed_description 함수 내용을 기반으로 합니다.
    """
    client_instance = OpenAI(api_key=OPENAI_API_KEY)
    prompt_text = generate_detailed_prompt_text(description, snippet, module)
    try:
        response = client_instance.chat.completions.create(
            model=LLM_MODEL,  # 또는 상세 설명 생성에 특화된 모델명 (예: config.LLM_MODEL_FOR_DESCRIPTION)
            messages=[
                {"role": "system", "content": "당신은 시스템 분석 전문가이며, 업무 설명을 상세하게 기술하는 역할입니다."},
                {"role": "user", "content": prompt_text}
            ],
            temperature=0.3 # description_agent.ipynb에서 사용된 temperature
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Error in get_detailed_description_from_llm for '{description[:30]}...': {e}")
        return f"상세 설명 생성 중 오류 발생: {str(e)}"