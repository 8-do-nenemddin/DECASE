# app/agents/mockup_planner_agent.py
import json
import re
# client = OpenAI(api_key=OPENAI_API_KEY)

class MockupPlanner:
    def __init__(self, feature_specs, system_overview, openai_client=None):
        self.feature_specs = feature_specs
        self.system_overview = system_overview
        self.client = openai_client
        self.analysis_cache = {}

    def _call_gpt(self, prompt_text, cache_key, system_message="You are a helpful AI assistant."):
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
                ]
            )
            result = response.choices[0].message.content
            self.analysis_cache[cache_key] = result
            return result
        except Exception as e:
            print(f"GPT API 호출 중 오류 발생 ({cache_key}): {e}")
            return None

    def define_pages_and_allocate_features(self):
        if not self.feature_specs:
            print("페이지 계획을 위한 기능 명세가 없습니다.")
            return self._get_fallback_page_plan()

        features_text_for_gpt = ""
        for spec in self.feature_specs: 
            features_text_for_gpt += f"- ID: {spec['id']}\n  기능 설명: {spec['description']}\n  (UI 제안: {spec['ui_suggestion_raw']}, 대상 액터 추정: {spec['actor_suggestion']}, 우선순위: {spec.get('priority', 'N/A')})\n\n"

        prompt = f"""
        다음은 구축할 소프트웨어 시스템의 개요와 주요 기능 명세입니다:

        시스템 개요:
        {self.system_overview}

        주요 기능 명세 (ID, 설명, UI 제안, 대상 액터 추정, 우선순위 순):
        {features_text_for_gpt}

        ---
        위 정보를 바탕으로, 이 시스템에 필요한 웹 페이지(화면)들의 목록을 제안해주십시오. 
        사용자 경험 흐름(User Flow)과 정보 구조(Information Architecture)를 고려하여, 기능들이 논리적으로 그룹화되고 중복이 최소화되도록 페이지를 구성해주십시오.
        **"필수" 우선순위 기능을 반드시 포함**하는 페이지들을 우선적으로 고려해주십시오.
        시스템의 주요 목적(예: 온라인 교육 플랫폼, 스포츠 지원 포털)을 충분히 고려하여 페이지들을 제안해주십시오.

        각 페이지에 대해 다음 정보를 포함하여 **JSON 형식**으로 응답해주십시오. 
        결과는 'pages'라는 최상위 키를 가진 딕셔너리이거나, 페이지 정보 딕셔너리들의 리스트 자체일 수 있습니다. 
        만약 리스트 자체로 응답한다면, 각 요소는 다음 키들을 포함해야 합니다:
        1.  `page_name`: 페이지의 대표적인 이름 (예: "User_Login", "Learner_Dashboard", "Course_Browse_And_Apply"). 파일명으로 사용하기 좋게 영어와 밑줄로 구성해주십시오.
        2.  `page_title_ko`: 페이지의 한글 제목 (HTML title 태그 및 화면 표시용).
        3.  `page_description`: 이 페이지의 주요 목적과 핵심 기능에 대한 간략한 설명.
        4.  `target_actors`: 이 페이지를 주로 사용할 사용자 역할(들) (리스트 형태, 예: ["학습자"], ["관리자", "운영자"]).
        5.  `included_feature_ids`: 이 페이지에 포함되어야 할 주요 기능들의 ID (위 기능 명세의 ID들을 참조하여 리스트 형태로, 예: ["FUNC-001", "DATA-003"]).
        6.  `key_ui_elements_suggestion`: 이 페이지의 핵심 UI 컴포넌트들에 대한 구체적인 제안 (문자열 형태).

        만약 제안할 페이지가 없다면 빈 리스트 `[]`를 'pages' 키의 값으로 주거나, 빈 리스트 자체를 응답해주십시오.
        """

        print("GPT에 페이지 정의 및 기능 할당 요청...")
        page_definitions_str = self._call_gpt(prompt, "page_definitions_v5_flexible", 
                                                "You are an expert UI/UX designer and information architect. Respond ONLY in valid JSON format. The response can be a JSON object with a 'pages' key containing a list, OR it can be a list of page objects directly.")
        
        if page_definitions_str:
            try:
                match = re.search(r'```json\s*([\s\S]*?)\s*```', page_definitions_str, re.IGNORECASE)
                if match:
                    json_str_cleaned = match.group(1)
                else:
                    json_str_cleaned = page_definitions_str.strip()
                
                parsed_response = json.loads(json_str_cleaned)

                pages_list = None
                if isinstance(parsed_response, list): 
                    pages_list = parsed_response
                    print(f"GPT로부터 {len(pages_list)}개의 페이지 계획 (리스트 직접 반환)을 성공적으로 받았습니다.")
                elif isinstance(parsed_response, dict) and "pages" in parsed_response and isinstance(parsed_response.get("pages"), list):
                    pages_list = parsed_response["pages"]
                    print(f"GPT로부터 {len(pages_list)}개의 페이지 계획 ('pages' 키 사용)을 성공적으로 받았습니다.")
                
                if pages_list is not None: 
                    if not pages_list: 
                        print("GPT가 제안한 페이지가 없습니다. 대체 계획을 사용합니다.")
                        return self._get_fallback_page_plan()
                    return pages_list
                else: 
                    print(f"GPT 응답이 예상된 형식이 아닙니다. 응답 내용: {parsed_response}")
                    return self._get_fallback_page_plan()

            except json.JSONDecodeError as e:
                print(f"GPT 페이지 계획 응답 파싱 오류: {e}. 응답 내용:\n{page_definitions_str}")
                return self._get_fallback_page_plan()
            except Exception as e:
                print(f"페이지 계획 처리 중 예기치 않은 오류: {e}")
                return self._get_fallback_page_plan()
        else:
            print("GPT로부터 페이지 계획을 받지 못했습니다.")
            return self._get_fallback_page_plan()

    def _get_fallback_page_plan(self):
        print("대체 페이지 계획 사용...")
        if not self.feature_specs:
            return [{
                "page_name": "Error_No_Features",
                "page_title_ko": "오류 - 기능 정보 없음",
                "page_description": "분석할 기능 명세가 없어 페이지를 계획할 수 없습니다.",
                "target_actors": ["개발자"],
                "included_feature_ids": [],
                "key_ui_elements_suggestion": "오류 메시지 표시."
            }]
        
        main_page_features = [spec['id'] for spec in self.feature_specs if spec.get('priority') == '필수']
        if not main_page_features: 
            main_page_features = [spec['id'] for spec in self.feature_specs[:min(3, len(self.feature_specs))]]
        
        actors_for_fallback = set()
        for spec_id in main_page_features:
            spec = next((s for s in self.feature_specs if s['id'] == spec_id), None)
            if spec and spec.get('actor_suggestion'):
                current_actors = spec['actor_suggestion']
                if isinstance(current_actors, str):
                    actors_for_fallback.update(act.strip() for act in current_actors.split('/'))
                elif isinstance(current_actors, list):
                    actors_for_fallback.update(current_actors)

        return [{
            "page_name": "Main_Application_Page_Fallback",
            "page_title_ko": "주요 애플리케이션 화면 (대체)",
            "page_description": "시스템의 핵심 기능들을 제공하는 기본 페이지입니다. (GPT 계획 실패로 인한 대체 화면)",
            "target_actors": list(actors_for_fallback) if actors_for_fallback else ["일반 사용자"],
            "included_feature_ids": main_page_features,
            "key_ui_elements_suggestion": "이 페이지는 다음 기능들을 포함합니다: " + ", ".join(main_page_features) + ". 각 기능에 맞는 UI 요소(버튼, 테이블, 폼 등)가 필요합니다."
        }]