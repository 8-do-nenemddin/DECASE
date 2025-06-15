# app/agents/mockup_planner_agent.py
import json
import re
from typing import List, Dict, Any
from openai import OpenAI

class MockupPlanner:
    """
    기능 명세와 시스템 개요를 바탕으로 웹 페이지 구조를 기획하고,
    메인 페이지 및 상세 페이지의 콘텐츠를 정의하는 클래스입니다.
    """
    def __init__(self, feature_specs: List[Dict[str, Any]], system_overview: str, openai_client: OpenAI):
        self.feature_specs = feature_specs
        self.system_overview = system_overview
        self.client = openai_client
        self.analysis_cache = {}

    def _call_gpt(self, prompt_text: str, cache_key: str, system_message: str, is_json: bool = True) -> str | None:
        """GPT API를 호출하고 결과를 반환하는 내부 메서드."""
        if not self.client:
            print(f"OpenAI 클라이언트가 없어 GPT 계획 수립을 건너뜁니다 ({cache_key}).")
            return None
        if cache_key in self.analysis_cache:
            return self.analysis_cache[cache_key]
        
        try:
            print(f"GPT 계획 요청 중 (키: {cache_key})...")
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": prompt_text}
                ],
                response_format={"type": "json_object"} if is_json else None,
                temperature=0.2
            )
            result = response.choices[0].message.content.strip() if response.choices and response.choices[0].message.content else None
            if result:
                self.analysis_cache[cache_key] = result
                return result
            return None
        except Exception as e:
            print(f"GPT API 호출 중 오류 발생 ({cache_key}): {e}")
            return None

    def define_pages_and_allocate_features(self) -> List[Dict[str, Any]]:
        """기능 명세를 바탕으로 웹 페이지들을 정의하고 기능을 할당합니다."""
        if not self.feature_specs:
            print("페이지 계획을 위한 기능 명세가 없습니다.")
            return []

        features_text_for_gpt = "\n".join([
            f"- ID: {spec['id']}, 기능 설명: {spec['description']}, 우선순위: {spec.get('priority', 'N/A')}"
            for spec in self.feature_specs
        ])

        prompt = f"""
        시스템 개요: {self.system_overview}
        주요 기능 명세:
        {features_text_for_gpt}
        ---
        **지시:** 위 정보를 바탕으로, 이 시스템에 필요한 웹 페이지 목록을 제안하고 모든 기능을 페이지에 할당해주십시오.
        사용자 경험 흐름을 고려하여 논리적으로 그룹화하고, 다음 정보를 포함한 JSON 객체로만 응답해주십시오.
        최상위 키는 "pages" 이고, 값은 페이지 정보 객체들의 리스트여야 합니다.

        각 페이지 객체는 다음 키를 가져야 합니다:
        1. `page_name`: 페이지의 영문 이름 (예: "Admin_User_Management")
        2. `page_title_ko`: 페이지의 한글 제목 (예: "사용자 관리")
        3. `page_description`: 페이지의 목적에 대한 간략한 설명.
        4. `target_actors`: 주요 사용자 역할 (리스트, 예: ["관리자"])
        5. `included_feature_ids`: 이 페이지에 포함될 기능 ID 목록.
        6. `key_ui_elements_suggestion`: 이 페이지의 기능을 구현하는데 필요한 핵심 UI 컴포넌트들을 구체적인 명세와 함께 제안해주십시오. (예: "사용자 목록을 표시하는 데이터 테이블 (컬럼: ID, 이름, 이메일), 신규 사용자 추가 버튼")
        """
        system_message = "You are an expert UI/UX designer and information architect. You must respond ONLY in a valid JSON object with a 'pages' key."
        
        page_definitions_str = self._call_gpt(prompt, "page_definitions_v6", system_message, is_json=True)

        if not page_definitions_str:
            print("GPT로부터 페이지 계획을 받지 못했습니다. 대체 계획을 사용합니다.")
            return self._get_fallback_page_plan()
        
        try:
            parsed_response = json.loads(page_definitions_str)
            pages_list = parsed_response.get("pages")
            if isinstance(pages_list, list):
                print(f"GPT로부터 {len(pages_list)}개의 상세 페이지 계획을 성공적으로 받았습니다.")
                return pages_list
            else:
                raise ValueError("JSON 'pages' 키가 리스트가 아닙니다.")
        except (json.JSONDecodeError, ValueError) as e:
            print(f"페이지 계획 파싱 오류: {e}. 대체 계획을 사용합니다.")
            return self._get_fallback_page_plan()

    def plan_user_main_page(self) -> Dict[str, Any]:
        """사용자 관점에서 메인 페이지에 들어갈 콘텐츠를 기획합니다."""
        print("사용자 중심 메인 페이지 콘텐츠 기획 중...")

        high_priority_specs = [
            spec for spec in self.feature_specs
            if spec.get('priority') in ['필수', '높음', '상']
        ]
        context_specs = high_priority_specs if high_priority_specs else self.feature_specs
        features_list_str = "\n".join([f"- {spec['description']}" for spec in context_specs[:15]])

        prompt = f"""
        시스템 개요: {self.system_overview}
        핵심 기능:
        {features_list_str}
        ---
        **지시:** 위 정보를 바탕으로, 일반 사용자가 로그인했을 때 보게 될 메인 페이지(홈 대시보드)에 어떤 콘텐츠가 있으면 가장 유용할지 기획해주세요.
        다음 정보를 포함한 JSON 객체로만 응답해주십시오:
        1.  `page_title_ko` (string): 페이지의 한글 제목 (예: "메인 대시보드")
        2.  `welcome_message` (string): 사용자 환영 메시지 (예: "{{user_name}}님, 환영합니다!")
        3.  `widgets` (list of objects): 페이지에 배치할 3~5개의 위젯. 각 위젯은 `title` (string)과 `content_idea` (string) 키를 가져야 합니다.
        """
        system_message = "You are a UX planner designing a user-centric main page. Respond ONLY in a valid JSON object."
        
        plan_str = self._call_gpt(prompt, "plan_user_main_page_v3", system_message, is_json=True)
        
        if not plan_str:
            return self._get_fallback_main_page_plan()
        try:
            plan = json.loads(plan_str)
            # is_main_page 플래그 추가
            plan['is_main_page'] = True
            return plan
        except json.JSONDecodeError:
            return self._get_fallback_main_page_plan()

    def _get_fallback_page_plan(self) -> List[Dict[str, Any]]:
        """GPT 계획 실패 시 대체 페이지 계획을 반환합니다."""
        print("대체 상세 페이지 계획 사용...")
        if not self.feature_specs: return []
        return [{
            "page_name": "Main_Application_Page_Fallback",
            "page_title_ko": "주요 기능 페이지 (대체)",
            "page_description": "시스템의 모든 기능들을 제공하는 기본 페이지입니다.",
            "target_actors": ["사용자"],
            "included_feature_ids": [spec['id'] for spec in self.feature_specs],
            "key_ui_elements_suggestion": "모든 기능에 대한 UI 요소가 필요합니다."
        }]
    
    def _get_fallback_main_page_plan(self) -> Dict[str, Any]:
        """GPT 메인 페이지 계획 실패 시 대체 계획을 반환합니다."""
        print("⚠️ 메인 페이지 계획 생성 실패. 기본 계획을 사용합니다.")
        return {
            "page_title_ko": "메인 페이지",
            "welcome_message": "환영합니다!",
            "widgets": [{"title": "주요 기능", "content_idea": "시스템의 주요 기능 목록을 보여줍니다."}],
            "is_main_page": True
        }