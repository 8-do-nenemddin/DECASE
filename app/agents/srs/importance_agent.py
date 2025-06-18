# app/services/importance_service.py
from openai import OpenAI
from app.core.config import OPENAI_API_KEY, LLM_MODEL

client = OpenAI(api_key=OPENAI_API_KEY)

def generate_importance_prompt_text(description_name: str, description_content: str, target_task: str) -> str:
    # 청크 내용 넣기 생각해야함
    return f"""
당신은 소프트웨어 요구사항을 분석하여 중요도를 판단하는 **매우 숙련되고 비판적인 시스템 분석가**입니다. 제시된 기준과 판단 가이드라인에 따라 각 요구사항의 중요도를 '상', '중', '하' 중 하나로 **극도로 신중하고 일관성 있게** 평가해야 합니다. **'상' 등급은 매우 제한적으로 사용되어야 함**을 명심하십시오.

다음은 시스템에 대한 요구사항입니다:

[요구사항 명]
{description_name}

[상세 설명]
{description_content}

[대상 업무]
{target_task}


요구사항을 분석한 뒤 전체 시스템에 대한 개요를 파악하고, 아래의 **세분화된 기준과 판단 가이드라인**에 따라 중요도를 평가하세요:

**[판단 가이드라인]**
1. 가장 먼저 '상' (Critical)에 해당하는지 판단하세요. 반드시 시스템 전체의 마비나 보안 사고가 아니라도, **전체 시스템의 주요 목적을 충족하지 못하게 하거나, 조직의 핵심 서비스 제공에 심각한 영향을 준다면 ‘상’으로 간주할 수 있습니다.**
2. '상'이 아니라면, '중' (Important)에 해당하는지 검토하세요.
3. ‘상’도 ‘중’도 아니라면, ‘하’ (Useful)로 평가하세요.
4. 평가 시 문구보다 **시스템 전반에 미치는 효과, 업무 흐름상 영향, 실패 시의 리스크** 등을 고려해 균형 있게 판단하십시오.

**[중요도 평가 기준]**

* **상 (C, Critical):**
    * **판단 기준:** 해당 요구사항이 누락되거나 실패할 경우, 전체 시스템의 **주요 기능이 심각하게 저해되거나**, 보안, 법적, 운영상 **치명적인 리스크**가 발생할 가능성이 있으며, **서비스 제공의 핵심 가치가 손상되는 경우**입니다. **대체 수단이 없거나 매우 제한적**이며, 주요 이해관계자의 **업무 또는 고객 경험에 직접적이고 즉각적인 악영향**이 발생하는 경우 포함됩니다.
    * **포함 사례 예시:**
        - 사용자 인증, 민감 정보 보호, 주요 업무 프로세스의 핵심 처리 로직, 장애/오류 발생 시 복구 메커니즘 등
        - 법적 요구 사항, 공공 API 대응 등 외부 규제 관련 항목

* **중 (I, Important):**
    * **판단 기준:** 시스템이 정상적으로 운영되기 위해 **강하게 권장되며**, 미구현 시 **업무 효율성 저하, 고객 불만 증가, 수익/평판 손실**로 이어질 수 있는 수준입니다. **단기적으로는 회피 가능하더라도, 반복적 업무 증가, 장기적인 운영 부담** 등의 형태로 **실질적인 영향**을 주는 경우 포함됩니다.

* **하 (U, Useful):**
    * **판단 기준:** 구현 시 **유용성이나 편의성**은 높지만, 없더라도 **대체 방안이 존재**하거나, 전체 시스템의 핵심 운영에는 큰 영향을 주지 않는 항목입니다. 주로 **UX 개선**, **장기 개선 항목**, **부가 기능** 등이 포함됩니다.

아래 형식으로 정확히 출력하세요:

중요도: <상|중|하>
"""

def get_importance_agent(description_name: str, description_content: str, target_task: str) -> str:
    prompt = generate_importance_prompt_text(description_name, description_content, target_task)
    try:
        response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": "당신은 소프트웨어 분석 전문가입니다."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.4
        )
        content = response.choices[0].message.content or ""
        importance = next((line.split(":")[1].strip() for line in content.splitlines() if "중요도" in line), "중")
        return importance
    except Exception as e:
        print(f"Error in get_importance_agent: {e}")
        return "Error"