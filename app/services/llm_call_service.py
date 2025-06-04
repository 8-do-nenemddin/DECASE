import json

from openai import OpenAI
from app.core.config import OPENAI_API_KEY, LLM_MODEL
from typing import Any, Optional

client = OpenAI(api_key=OPENAI_API_KEY)

# === 3. LLM 호출 헬퍼 함수 (기존과 동일) ===
def call_llm(
    system_prompt: str,
    user_prompt: str,
    is_json_output: bool = False
) -> Optional[Any]:
    global client, LLM_MODEL
    llm_response_content = ""
    try:
        request_params = {
            "model": LLM_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.0,
            "max_tokens": 4000 # 필요시 조절
        }
        if is_json_output:
            request_params["response_format"] = {"type": "json_object"}

        response = client.chat.completions.create(**request_params)
        llm_response_content = response.choices[0].message.content

        if llm_response_content is None:
            print("경고: LLM으로부터 응답 내용이 없습니다.")
            return None

        if is_json_output:
            return json.loads(llm_response_content)
        return llm_response_content

    except json.JSONDecodeError as e:
        print(f"LLM 응답 JSON 파싱 오류: {e}. 응답: {llm_response_content[:500]}...")
        return None
    except Exception as e:
        print(f"LLM API 호출 또는 처리 중 오류 발생: {type(e).__name__} - {e}")
        if llm_response_content:
            print(f"오류 발생 시 LLM 응답 일부: {llm_response_content[:500]}...")
        return None