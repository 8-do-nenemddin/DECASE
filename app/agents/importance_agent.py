# app/services/importance_service.py
from openai import OpenAI
from app.core.config import OPENAI_API_KEY, LLM_MODEL

client = OpenAI(api_key=OPENAI_API_KEY)

def generate_importance_prompt_text(description: str, detailed_description: str, module: str) -> str:
    # 기존 generate_importance_prompt_text 함수 내용 붙여넣기
    return f"""
당신은 소프트웨어 요구사항을 분석하여 중요도를 판단하는 **매우 숙련되고 비판적인 시스템 분석가**입니다. 제시된 기준과 판단 가이드라인에 따라 각 요구사항의 중요도를 '상', '중', '하' 중 하나로 **극도로 신중하고 일관성 있게** 평가해야 합니다. **'상' 등급은 매우 제한적으로 사용되어야 함**을 명심하십시오.

다음은 시스템에 대한 요구사항입니다:

[요구사항 설명]
{description}

[상세 설명]
{detailed_description}

[담당 모듈]
{module}

요구사항을 분석한 뒤, 아래의 **세분화된 기준과 판단 가이드라인**에 따라 중요도를 평가하세요:

**[판단 가이드라인]**
1.  **가장 먼저 '상' (Critical)에 해당하는지 극도로 보수적으로 판단합니다.** 이 요구사항이 없으면 시스템 자체가 완전히 무너지거나 법적/보안적으로 회복 불가능한 치명적 문제가 발생하는지 자문하십시오. **대부분의 요구사항은 '상'에 해당하지 않을 가능성이 높습니다.**
2.  '상'이 아니라면, '중' (Important)에 해당하는지 검토합니다.
3.  '상'도 '중'도 아니라면 '하' (Useful)로 평가합니다.
4.  요구사항의 단어나 문구에 현혹되지 말고, **실제 시스템 전체에 미치는 파급 효과와 해당 요구사항 실패 시의 구체적인 결과를 기준으로 냉정하게 판단**하십시오. 모든 요구사항이 중요해 보일 수 있지만, 자원은 한정되어 있으므로 상대적인 중요도를 엄격히 구분해야 합니다.

**[중요도 평가 기준]**

* **상 (C, Critical):**
    * **판단 기준:** 해당 요구사항의 미구현이 **시스템 전체의 핵심 기능 마비, 서비스 불가능 상태 초래, 심각한 법적/규제적 문제 야기, 대규모 중요 데이터의 영구적 손실 또는 오염, 회복 불가능한 치명적 보안 사고 발생**과 같이 프로젝트의 존립을 위협하거나 시스템 전체의 실패를 의미하는 경우에만 해당합니다. **대체 수단이 전혀 없거나, 그 영향이 조직/서비스 전체에 즉각적이고 치명적인 경우**에만 극히 제한적으로 부여합니다.
    * **'상'이 아닌 경우 (예시):** 단순히 "필수적"이라고 언급되거나, 중요한 기능처럼 보이더라도, 위와 같은 수준의 치명적이고 즉각적인 결과로 이어지지 않는다면 '상'으로 평가해서는 안 됩니다. 예를 들어, 특정 기능의 부재가 큰 불편을 야기하지만 시스템의 다른 핵심 기능은 정상 동작한다면 '상'이 아닙니다.

* **중 (I, Important):**
    * **판단 기준:** 시스템의 기능적 완성도, 운영 효율성, 사용자 만족도에 **상당한 영향을 미치지만, 그것이 없다고 해서 시스템 전체가 즉시 마비되거나 사용 불가능 상태가 되지는 않는 경우**입니다. 미구현 시 서비스 중단까지는 아니지만, 주요 사용자의 큰 불편을 초래하거나, 기업의 수익/평판에 측정 가능한 부정적 영향을 미치거나, 핵심 업무 프로세스에 심각한 차질을 주는 경우 해당됩니다.
    * **'중'이 아닌 경우 (예시):** 사소한 불편함, 일부 제한된 사용자에게만 영향, 또는 있으면 좋지만 없어도 큰 지장이 없는 경우는 '중'이 아닙니다.

* **하 (U, Useful):**
    * **판단 기준:** 구현되면 유용하고 사용자 경험을 개선할 수 있지만, 미구현되어도 시스템의 핵심 기능, 안정성, 보안 및 주요 사용자 그룹의 전반적인 만족도에 **심각한 영향을 주지 않는 사항**입니다. 약간의 불편함이 있거나, 특정 소수의 사용자에게만 영향을 미치거나, 다른 기능으로 비교적 쉽게 대체 가능하거나, 장기적으로 고려할 만한 개선 사항인 경우 해당됩니다.

아래와 같이 **정확히 이 형식**으로만 출력하세요 (불필요한 설명 없이):

중요도: <상|중|하>
"""

def get_importance_agent(description: str, detailed_description: str, module: str) -> str:
    prompt = generate_importance_prompt_text(description, detailed_description, module)
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