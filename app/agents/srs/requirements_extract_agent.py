from typing import List
from app.services.llm_call_service import call_gpt

# === 4. 에이전트 1: 청크 내 요구사항 핵심 문장 식별 ===
def extract_requirement_sentences_agent(text_chunk: str) -> List[str]:
    system_prompt = """
    당신은 주어진 텍스트에서 시스템 구축과 관련된 요구사항을 나타내는 핵심 문장들만을 정확히 식별하는 전문가입니다.
    설명, 배경, 일반적인 내용이 아닌, 구체적인 행위, 기능, 제약조건 등을 명시하는 문장을 추출하세요.
    각 요구사항 문장을 한 줄에 하나씩 명확히 구분하여 응답하세요.
    예를 들어 한 문장에 두 가지의 요구사항이 있다고 판단되면, 구분하여 작성해야 합니다.
    만약 식별된 요구사항 문장이 없다면 "No requirements found."라고 응답하세요.
    """
    user_prompt = f"""
    다음 텍스트에서 시스템 요구사항에 해당하는 핵심 문장들을 모두 추출해주십시오. 각 문장은 새 줄로 구분하여 응답합니다:

    --- 텍스트 시작 ---
    {text_chunk}
    --- 텍스트 끝 ---
    """
    response_text = call_gpt(system_prompt, user_prompt, is_json_output=False)

    if response_text and response_text.strip().lower() != "no requirements found.":
        sentences = [sentence.strip() for sentence in response_text.splitlines() if sentence.strip()]
        return sentences
    return []