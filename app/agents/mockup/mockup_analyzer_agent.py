# app/agents/mockup_analyzer_agent.py
import json
from typing import List, Dict, Any
from openai import OpenAI

class RequirementsAnalyzer:
    """
    요구사항 데이터를 분석하여 시스템 개요를 파악하고,
    핵심 기능 명세를 추출하는 역할을 담당하는 클래스입니다.
    """
    def __init__(self, requirements_data: List[Dict[str, Any]], openai_client: OpenAI):
        self.requirements = requirements_data
        self.client = openai_client
        self.model = "gpt-4o"
        self.analysis_cache = {}

    def _call_gpt(self, prompt_text: str, cache_key: str, system_message: str, is_json: bool = False) -> str | None:
        """GPT API를 호출하고 결과를 반환하는 내부 메서드."""
        if not self.client:
            print(f"OpenAI 클라이언트가 없어 GPT 분석을 건너뜁니다 ({cache_key}).")
            return None
        if cache_key in self.analysis_cache:
            return self.analysis_cache[cache_key]

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": prompt_text}
                ],
                temperature=0.2,
                max_tokens=2048,
                response_format={"type": "json_object"} if is_json else None
            )
            result = response.choices[0].message.content.strip() if response.choices and response.choices[0].message.content else None
            if result:
                self.analysis_cache[cache_key] = result
                return result
            else:
                print(f"⚠️ GPT 응답이 비어 있음. 키: {cache_key}")
                return None
        except Exception as e:
            print(f"❌ GPT 호출 실패 (키: {cache_key}) → {e}")
            return None

    def get_system_overview(self) -> str:
        """요구사항을 바탕으로 시스템의 전반적인 개요를 생성합니다."""
        if not self.requirements:
            return "요구사항 데이터가 없어 시스템 개요를 생성할 수 없습니다."

        # [수정] 요구사항의 전체 내용 대신 'description_name'(제목)만 사용합니다.
        # 이렇게 하면 토큰 사용량을 크게 줄일 수 있습니다.
        sample_descriptions = "\n".join([
            f"- 기능 제목: {req.get('description_name', '제목 없음')}"
            for req in self.requirements[:min(25, len(self.requirements))] # 제목만 보내므로 샘플 수를 조금 늘려도 괜찮습니다.
        ])

        prompt = f"""
        다음은 소프트웨어 시스템의 주요 기능 제목 목록입니다:
        {sample_descriptions}
        ---
        위 기능 목록을 종합하여, 이 시스템의 주요 목적, 예상되는 주요 사용자 역할(액터),
        그리고 이 시스템을 대표할 만한 간결한 이름이나 주제가 있다면 무엇인지 요약해주십시오.
        """
        system_message = "You are a system architect summarizing project requirements based on feature titles."
        overview = self._call_gpt(prompt, "system_overview_summary_from_titles", system_message, is_json=False)

        if overview:
            print(f"시스템 개요 파악 (GPT): {overview[:150]}...")
            return overview
        else:
            # [수정] API 호출 실패 시, 여기서 예외를 발생시켜 프로세스를 중단시키는 것이 더 안전합니다.
            # raise ValueError("시스템 개요를 생성하는 데 실패하여 프로세스를 중단합니다.")
            
            # 또는 기존처럼 Fallback 로직을 유지할 수 있습니다.
            first_req_desc = self.requirements[0].get("description_name", "상세 설명 없음")
            fallback_overview = f"총 {len(self.requirements)}개의 요구사항을 가진 시스템입니다. 주요 목적은 '{first_req_desc}'와 관련될 것으로 보입니다."
            print(f"⚠️ 시스템 개요 생성 실패. Fallback을 사용합니다: {fallback_overview}")
            return fallback_overview

    def get_feature_specifications(self) -> List[Dict[str, Any]]:
        """요구사항 목록을 기반으로 기능 명세 목록을 생성합니다."""
        feature_specs = []
        if not self.requirements:
            print("오류: 분석할 요구사항 데이터가 없습니다.")
            return feature_specs

        target_reqs = [req for req in self.requirements if req.get("type") == "기능"]
        print(f"분석 대상 기능적 요구사항 수: {len(target_reqs)}")

        for i, req in enumerate(target_reqs):
            req_id = f"FUNC-{i+1:03}"
            description = req.get("description_name", "제목 없음")
            detail = f"{req.get('description_content', '')}\n\n{req.get('processing_detail', '')}".strip()

            feature_specs.append({
                "id": req_id,
                "description": description.strip(),
                "description_detailed": detail,
                "acceptance_criteria": "요구사항 내 명시 없음", # 필요 시 이 부분도 생성 가능
                "ui_suggestion_raw": f"'{description}' 기능을 위한 UI 구성 요소 제안",
                "actor_suggestion": req.get("target_task", "사용자"), # target_task를 액터 추정에 사용
                "module": req.get("category_medium", "미분류"), # category_medium을 모듈로 사용
                "priority": req.get("importance", "중"),
            })

        print(f"{len(feature_specs)}개의 주요 기능 명세 추출 완료.")
        return feature_specs