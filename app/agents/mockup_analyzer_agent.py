import json # 이전에 있었는지 확인, 없다면 추가
from typing import List, Dict, Any # 타입 힌트용

# client = OpenAI(api_key=OPENAI_API_KEY) # 모듈 레벨 또는 함수 내에서 생성
class RequirementsAnalyzer:
    def __init__(self, requirements_data: List[Dict[str, Any]], openai_client: Any = None): # 타입 힌트 명시
        self.requirements = requirements_data
        self.client = openai_client
        self.model = "gpt-4o"
        self.analysis_cache = {}

    def _call_gpt(self, prompt_text: str, cache_key: str, system_message: str = "You are a helpful AI assistant.") -> str | None: # 반환 타입 힌트 명시
        if not self.client:
            print(f"OpenAI 클라이언트가 없어 GPT 분석을 건너뜁니다 ({cache_key}).")
            return None
        if cache_key in self.analysis_cache:
            return self.analysis_cache[cache_key]

        try:
            if hasattr(self.client, 'chat') and hasattr(self.client.chat, 'completions'):
                 response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_message},
                        {"role": "user", "content": prompt_text}
                    ],
                    temperature=0.2,
                    max_tokens=2048
                )
                 result = response.choices[0].message.content.strip() if response.choices[0].message.content else None
            else:
                result = "GPT 호출 방식 오류로 분석 결과 없음"
                print(f"⚠️ RequirementsAnalyzer._call_gpt: 클라이언트 API 형식이 예상과 다릅니다. ({cache_key})")

            if not result:
                print(f"⚠️ GPT 응답이 비어 있음. 키: {cache_key}")
                return None
            self.analysis_cache[cache_key] = result
            return result
        except Exception as e:
            print(f"❌ GPT 호출 실패 (키: {cache_key}) → {e}")
            return None

    def get_feature_specifications(self) -> List[Dict[str, Any]]: # 반환 타입 힌트 명시
        feature_specs = []
        if not self.requirements:
            print("오류: 분석할 요구사항 데이터가 없습니다.")
            return feature_specs

        # "type"이 "기능"인 항목만 필터링
        target_reqs = [
            req for req in self.requirements
            if req.get("type") == "기능" # 실제 데이터의 "type" 필드 사용
        ]
        print(f"분석 대상 기능적 요구사항 수: {len(target_reqs)}")

        for i, req in enumerate(target_reqs):
            # ID는 req 데이터에 있다면 그것을 사용하고, 없다면 생성 (현재는 항상 새로 생성)
            # 만약 req.get("id")를 우선 사용하고 싶다면 아래와 같이 수정:
            # req_id = req.get("id", f"FUNC-{i+1:03}")
            req_id = f"FUNC-{i+1:03}"  # 현재 로직 유지 (새로 ID 생성)

            description = req.get("description_name", "제목 없음") # 실제 데이터 필드명 "description_name" 사용
            
            # 상세 설명 조합 (실제 데이터 필드명 사용)
            desc_content = req.get("description_content", "")
            proc_detail = req.get("processing_detail", "")
            detail = f"{desc_content}\n\n{proc_detail}".strip()
            
            actor_guess = "사용자"  # 역할 정보가 명시적으로 없음, 추정 필요

            feature_specs.append({
                "id": req_id,
                "description": description.strip(),
                "description_detailed": detail.strip(),
                "acceptance_criteria": req.get("acceptance_criteria", "요구사항 내 명시 없음"), # 데이터에 이 필드가 있다면 사용
                "ui_suggestion_raw": f"'{description}' 기능을 위한 UI 구성 요소 제안",
                "actor_suggestion": actor_guess,
                "module": req.get("target_task", "미정"), # 실제 데이터 필드명 "target_task" 사용
                "priority": req.get("importance", "중"), # 실제 데이터 필드명 "importance" 사용
            })

        print(f"{len(feature_specs)}개의 주요 기능 명세 추출 완료.")
        return feature_specs

    def get_system_overview(self) -> str: # 반환 타입 힌트 명시
        if not self.requirements:
            print("오류: 시스템 개요를 파악할 요구사항 데이터가 없습니다.")
            return "요구사항 데이터 없음"

        # 첫 번째 요구사항의 description_name 사용
        first_req_desc = self.requirements[0].get("description_name", "요구사항명 없음")
        num_total_reqs = len(self.requirements)

        sample_descriptions_for_overview = "\n".join([
            # ID가 있다면 req.get('id') 사용, 없다면 인덱스 사용. description_name 사용
            f"- ID:{req.get('id', f'ITEM-{idx}')}, 설명:{req.get('description_name', '설명 없음')}"
            for idx, req in enumerate(self.requirements[:min(10, len(self.requirements))])
        ])

        prompt = f"""다음은 소프트웨어 요구사항의 일부입니다:
        {sample_descriptions_for_overview}
        ---
        위 요구사항들을 종합하여, 이 시스템의 주요 목적은 무엇이며, 예상되는 주요 사용자 역할(액터)들은 누구인지, 그리고 이 시스템을 대표할 만한 간결한 이름이나 주제가 있다면 무엇인지 요약해주십시오.
        """
        overview = self._call_gpt(prompt, "system_overview_summary_v3_updated", "You are a system architect summarizing project requirements.") # cache_key 변경 또는 유지

        if overview:
            print(f"시스템 개요 파악 (GPT): {overview[:100]}...")
            return overview
        else:
            # Fallback 메시지에서 first_req_desc가 description_name을 참조하도록 함
            fallback_overview = f"총 {num_total_reqs}개의 요구사항을 가진 시스템. 주요 목적은 '{first_req_desc}'와 관련될 것으로 보이며, 다양한 사용자를 지원할 것으로 예상됩니다."
            print(f"시스템 개요 파악 (Fallback): {fallback_overview[:100]}...")
            return fallback_overview