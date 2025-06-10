from openai import OpenAI # GPT-4o 사용 시
import json
import os
from app.agents.mockup_analyzer_agent import RequirementsAnalyzer
from app.agents.mockup_generator_agent import HtmlGenerator
from app.agents.mockup_planner_agent import MockupPlanner
from app.services.file_processing_service import sanitize_filename
from typing import List, Dict

import re
import anthropic # Claude API 사용을 위해 추가

# --- 유틸리티 함수 (사용자 원본 코드) ---
def sanitize_filename(name):
    """파일 이름으로 사용하기 어려운 문자를 제거하거나 대체합니다."""
    if not isinstance(name, str): # 문자열이 아닌 경우 처리
        name = str(name)
    name = re.sub(r'[<>:"/\\|?*]', '_', name) # 파일명 금지 문자 대체
    name = re.sub(r'\s+', '_', name) # 공백을 밑줄로
    return name[:100] # 파일명 길이 제한 (필요시)

# --- RequirementsLoader 클래스 (사용자 원본 코드) ---
class RequirementsLoader:
    def load_from_file(self, filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            print(f"요구사항 파일 '{filepath}' 로드 성공.")
            return data
        except FileNotFoundError:
            print(f"오류: 파일 '{filepath}'를 찾을 수 없습니다.")
            return None
        except json.JSONDecodeError:
            print(f"오류: 파일 '{filepath}'가 유효한 JSON 형식이 아닙니다.")
            return None
        except Exception as e:
            print(f"파일 로드 중 예기치 않은 오류 발생: {e}")
            return None

# --- RequirementsAnalyzer 클래스 (사용자 원본 코드) ---
class RequirementsAnalyzer:
    def __init__(self, requirements_data: List[Dict], openai_client):
        self.requirements_data = requirements_data
        self.client = openai_client
        self.analysis_cache = {}
    
    def get_system_overview(self) -> str:
        """시스템의 전반적인 개요를 추출합니다."""
        if not self.requirements_data:
            return "시스템 개요를 추출할 수 없습니다."
        
        # 요구사항 데이터에서 시스템 개요를 추출하기 위한 프롬프트 구성
        requirements_text = "\n".join([
            f"- {req.get('description_name', 'N/A')}: {req.get('description_content', 'N/A')}"
            for req in self.requirements_data
        ])
        
        prompt = f"""
        다음은 소프트웨어 시스템의 요구사항 목록입니다:

        {requirements_text}

        위 요구사항들을 종합적으로 분석하여, 이 시스템이 무엇을 하는지에 대한 간단한 개요를 작성해주세요.
        응답은 한 문단으로, 2-3문장 정도로 간단명료하게 작성해주세요.
        """
        
        system_message = "You are an expert software requirements analyst. Provide a concise system overview based on the given requirements."
        
        overview = self._call_gpt(prompt, "system_overview", system_message)
        return overview if overview else "시스템 개요를 추출할 수 없습니다."
    
    def get_feature_specifications(self) -> List[Dict]:
        """각 요구사항을 기능 명세로 변환합니다."""
        if not self.requirements_data:
            return []
        
        feature_specs = []
        for req in self.requirements_data:
            spec = {
                'id': req.get('id', f"REQ-{len(feature_specs) + 1}"),
                'description': req.get('description_content', ''),
                'type': req.get('type', '기능'),
                'priority': req.get('importance', '보통'),
                'actor_suggestion': req.get('target_task', '일반 사용자'),
                'ui_suggestion_raw': req.get('processing_detail', '')
            }
            feature_specs.append(spec)
        
        return feature_specs
    
    def _call_gpt(self, prompt_text: str, cache_key: str, system_message: str = "You are a helpful AI assistant.") -> str:
        """GPT API를 호출하여 응답을 받습니다."""
        if cache_key in self.analysis_cache:
            return self.analysis_cache[cache_key]
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4",
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

# --- MockupPlanner 클래스 (사용자 원본 코드) ---
class MockupPlanner:
    def __init__(self, feature_specs, system_overview, openai_client=None):
        self.feature_specs = feature_specs
        self.system_overview = system_overview
        self.client = openai_client
        self.analysis_cache = {}

    def _call_gpt(self, prompt_text, cache_key, system_message="You are a helpful AI assistant."):
        if not self.client: return None
        try:
            print(f"GPT 계획 요청 중 (키: {cache_key})...")
            response = self.client.chat.completions.create(model="gpt-4o", messages=[{"role": "system", "content": system_message}, {"role": "user", "content": prompt_text}])
            result = response.choices[0].message.content
            self.analysis_cache[cache_key] = result
            return result
        except Exception as e:
            print(f"GPT API 호출 중 오류 발생 ({cache_key}): {e}")
            return None

    def define_pages_and_allocate_features(self):
        if not self.feature_specs:
            return self._get_fallback_page_plan()
        
        features_text_for_gpt = ""
        for spec in self.feature_specs: 
            features_text_for_gpt += f"- ID: {spec['id']}, 기능 설명: {spec['description']}\n"

        # ▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼
        # 핵심 수정: key_ui_elements_suggestion을 훨씬 더 구체적으로 요구하도록 프롬프트 변경
        # ▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼
        prompt = f"""
        시스템 개요: {self.system_overview}
        주요 기능 명세:
        {features_text_for_gpt}
        ---
        **페이지 분할 원칙 (매우 중요):**
        1.  하나의 페이지는 사용자의 **하나의 명확한 목표 또는 작업(Task)**을 해결해야 합니다.
        2.  **기능이 너무 많은 '만능 페이지'를 만들지 마십시오.** 예를 들어 '선수 관리'라는 큰 주제가 있다면, 그것을 '선수 목록 페이지', '선수 상세 정보 페이지', '선수 등록 페이지', '선수 기록 관리 페이지' 등으로 **기능을 분할하여 여러 페이지를 만드는 것을 적극적으로 고려**해주십시오.
        위 정보를 바탕으로, 이 시스템에 필요한 웹 페이지 목록을 제안하고 모든 기능을 페이지에 할당해주십시오.
        사용자 경험 흐름을 고려하여 논리적으로 그룹화하고, 다음 정보를 포함한 JSON 형식으로만 응답해주십시오.
        
        각 페이지 딕셔너리는 다음 키를 포함해야 합니다:
        1. `page_name`: 페이지의 영문 이름 (예: "Admin_User_Management")
        2. `page_title_ko`: 페이지의 한글 제목 (예: "사용자 관리")
        3. `page_description`: 페이지의 목적에 대한 간략한 설명.
        4. `target_actors`: 주요 사용자 역할 (리스트, 예: ["관리자"]) 안녕
        5. `included_feature_ids`: 이 페이지에 포함될 기능 ID 목록.
        6. `key_ui_elements_suggestion`: **(매우 중요)** 이 페이지의 기능을 구현하는 데 필요한 핵심 UI 컴포넌트들을 **구체적인 명세와 함께 제안**해주십시오. 
           **예시:** "사용자 목록을 표시하는 데이터 테이블 (컬럼: ID, 이름, 이메일, 역할, 상태), 사용자를 검색하기 위한 입력 필드와 검색 버튼, 신규 사용자 추가 버튼" 과 같이 **실제 화면에 그려야 할 요소들을 명확하고 상세하게** 작성해주십시오. 이 내용은 HTML 생성 단계에서 그대로 사용됩니다.
        """
        
        system_message = "You are an expert UI/UX designer and information architect. You must respond ONLY in valid JSON format."
        page_definitions_str = self._call_gpt(prompt, "page_definitions_v6_detailed_ui", system_message)
        
        if page_definitions_str:
            try:
                match = re.search(r'```json\s*([\s\S]*?)\s*```', page_definitions_str, re.IGNORECASE)
                json_str_cleaned = match.group(1) if match else page_definitions_str.strip()
                parsed_response = json.loads(json_str_cleaned)
                pages_list = parsed_response if isinstance(parsed_response, list) else parsed_response.get("pages")

                if isinstance(pages_list, list) and pages_list: 
                    print(f"GPT로부터 {len(pages_list)}개의 상세 페이지 계획을 성공적으로 받았습니다.")
                    return pages_list
                else:
                    print("GPT가 유효한 페이지 계획을 생성하지 못했습니다. 대체 계획을 사용합니다.")
                    return self._get_fallback_page_plan()
            except Exception as e:
                print(f"페이지 계획 파싱 오류: {e}. 대체 계획을 사용합니다.")
                return self._get_fallback_page_plan()
        else:
            print("GPT로부터 페이지 계획을 받지 못했습니다. 대체 계획을 사용합니다.")
            return self._get_fallback_page_plan()

    def _get_fallback_page_plan(self):
        print("대체 페이지 계획 사용...")
        if not self.feature_specs: return []
        main_page_features = [spec['id'] for spec in self.feature_specs]
        return [{"page_name": "Main_Application_Page_Fallback", "page_title_ko": "주요 애플리케이션 화면 (대체)", "page_description": "시스템의 모든 기능들을 제공하는 기본 페이지입니다.", "target_actors": ["사용자"], "included_feature_ids": main_page_features, "key_ui_elements_suggestion": "모든 기능에 대한 UI 요소 필요."}]
    def plan_user_main_page(self):
        """사용자 관점에서 메인 페이지에 들어갈 콘텐츠를 기획합니다."""
        print("사용자 중심 메인 페이지 콘텐츠 기획 중...")
        
        # ▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼
        # 핵심 수정: 상위 15개가 아닌, 중요도 높은 기능을 선별하여 컨텍스트로 사용
        # ▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼
        
        # 1. 중요도가 '필수' 또는 '높음'인 기능들을 먼저 필터링합니다.
        #    (JSON 데이터에 'importance' 키와 '필수', '높음' 등의 값이 있어야 합니다)
        high_priority_specs = [
            spec for spec in self.feature_specs 
            if spec.get('priority') in ['필수', '높음', '상'] # 다양한 중요도 표현을 고려
        ]
        
        # 2. 만약 중요도 높은 기능이 없다면, 전체에서 일부를 사용합니다.
        if not high_priority_specs:
            context_specs = self.feature_specs
        else:
            context_specs = high_priority_specs

        # 3. 컨텍스트가 너무 길어지는 것을 방지하기 위해 최대 20개로 제한하되, 이제는 핵심 기능 위주입니다.
        features_list_str = "\n".join([f"- {spec['description']}" for spec in context_specs[:20]])
        print(f"메인 페이지 기획을 위해 {len(context_specs[:20])}개의 핵심 기능 컨텍스트를 사용합니다.")
        
        prompt = f"""
        당신은 '세계 최고의'의 UX 기획자입니다.
        시스템 개요: {self.system_overview}
        
        다음은 이 시스템의 **핵심 기능**들입니다:
        {features_list_str}

        ---
        위 정보를 바탕으로, **일반 사용자가 로그인했을 때 보게 될 메인 페이지(홈 화면)**에 어떤 콘텐츠가 있으면 가장 유용할지 기획해주세요.

        다음 정보를 포함한 **JSON 형식**으로만 응답해주십시오:
        1.  `page_title` (string): 페이지의 적절한 한글 제목 (예: "마이페이지", "홈")
        2.  `welcome_message` (string): 사용자 환영 메시지 (예: "{{이름}}님, 환영합니다!")
        3.  `widgets` (list of objects): 페이지에 배치할 3~5개의 위젯(콘텐츠 섹션) 목록.
            - 각 위젯 객체는 `title` (string)과 `content_idea` (string) 키를 가져야 합니다.
            - **핵심 기능 목록**을 바탕으로, 사용자가 실제로 관심을 가질 만한 내용으로 구성해주십시오.
        """
        system_message = "You are a UX planner designing a user-centric main page based on core system features. Respond ONLY in a valid JSON object."
        
        plan_str = self._call_gpt(prompt, "plan_user_main_page_v2_priority", system_message)
        
        if not plan_str:
            print("⚠️ 메인 페이지 계획 생성 실패. 기본 계획을 사용합니다.")
            return {"page_title": "메인 페이지", "welcome_message": "환영합니다!", "widgets": [{"title": "주요 기능", "content_idea": "시스템의 주요 기능 목록을 보여줍니다."}]}

        try:
            match = re.search(r'```json\s*([\s\S]*?)\s*```', plan_str, re.IGNORECASE)
            json_str = match.group(1) if match else plan_str
            return json.loads(json_str)
        except json.JSONDecodeError:
            print("⚠️ 메인 페이지 계획 JSON 파싱 실패. 기본 계획을 사용합니다.")
            return {"page_title": "메인 페이지", "welcome_message": "환영합니다!", "widgets": [{"title": "주요 기능", "content_idea": "시스템의 주요 기능 목록을 보여줍니다."}]}
# ▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼
# --- HtmlGenerator 클래스 (API 호출 엔진만 Claude로 교체) ---
# ▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲

class HtmlGenerator:
    def __init__(self, anthropic_client):
        self.client = anthropic_client
        self.cache = {}
    
    def generate_html_for_page_plan(self, page_plan_details, all_feature_specs):
        """개별 기능 페이지의 목업을 생성합니다."""
        page_title_ko = page_plan_details.get("page_title_ko", "목업 페이지")
        key_ui_elements_suggestion = page_plan_details.get("key_ui_elements_suggestion", "페이지의 주요 기능들을 표시합니다.")
        
        prompt = f"""
        **지시사항:** 당신은 세계 최고의 UI/UX 디자이너입니다. 다음 정보를 바탕으로, 실제 작동하는 것처럼 보이는 정교하고 완성도 높은 HTML 목업 페이지를 생성해주십시오. 순수 HTML과 인라인 CSS(<style> 태그)만 사용합니다.
        **스타일 목표:** 극도로 깔끔하고, 정교하며, 현대적인 미니멀리즘 UI 디자인.
        ---
        ### 페이지 정보
        - **페이지 제목:** {page_title_ko}
        - **페이지 설명:** {page_plan_details.get("page_description", "")}
        ---
        ### **페이지 핵심 구성 요소 (가장 중요! 반드시 모두 구현할 것)**
        이 페이지의 메인 콘텐츠 영역에는 다음의 구체적인 UI 컴포넌트들이 **반드시 포함**되어야 합니다. 이 지시를 무시하고 영역을 비워두지 마십시오.
        
        **{key_ui_elements_suggestion}**

        **지시 해석 예시:**
        - "사용자 목록을 표시하는 데이터 테이블"이라는 지시가 있다면, 실제 `<table>` 태그와 목업 데이터(`<tr>`, `<td>`)를 사용하여 사용자가 여러 명 있는 것처럼 표를 그려주십시오.
        - "검색 필드와 버튼"이라는 지시가 있다면, 실제 `<input type="search">`와 `<button>`을 만드십시오.
        ---
        **최종 결과물:** 다른 어떤 설명도 없이, 완성된 HTML 코드만 응답하십시오.
        """
        system_message = "You are a world-class UI/UX Design Lead. You must render all requested components. Respond ONLY with the raw HTML code."
        
        cache_key = f"html_gen_{page_plan_details.get('page_name', 'unknown')}_{hash(prompt)}"
        
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        try:
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=4000,
                temperature=0.1,
                system="You are a world-class UI/UX designer creating a stunning, minimalist, and modern web page. Respond ONLY with the raw HTML code.",
                messages=[{"role": "user", "content": prompt}]
            )
            
            html_code = response.content[0].text
            self.cache[cache_key] = html_code
            return html_code
            
        except Exception as e:
            print(f"HTML 생성 중 오류 발생: {str(e)}")
            return None
    
    def generate_user_main_page_html(self, main_page_plan, defined_pages_details, project_name):
        """사용자 메인 페이지의 HTML을 생성합니다."""
        page_title = main_page_plan.get("page_title_ko", "메인 페이지")
        welcome_message = main_page_plan.get("welcome_message", "환영합니다!")
        
        # 위젯 HTML 생성
        widgets_html = ""
        for widget in main_page_plan.get("widgets", []):
            widgets_html += f"""
            <div class="widget">
                <h3>{widget.get('title', '정보')}</h3>
                <div class="widget-content">
                    {widget.get('content_idea', '내용이 여기에 표시됩니다.')}
                </div>
            </div>
            """
        
        # 빠른 링크 HTML 생성
        quick_links_html = ""
        for page in defined_pages_details:
            page_name = page.get("page_name", "")
            page_title = page.get("page_title_ko", "")
            if page_name and page_title:
                quick_links_html += f'<li><a href="{page_name}.html">{page_title}</a></li>'
        
        prompt = f"""
        **지시사항:** 다음 기획안을 바탕으로, 사용자가 로그인했을 때 보게 될 환영 페이지를 생성해주십시오.
        **스타일 목표:** 사용자에게 친근하고, 정보가 명확하며, 현대적인 디자인.
        ---
        ### **페이지 기획안**
        1.  **페이지 전체 제목:** "{page_title}"
        2.  **페이지 상단 헤더:** 환영 메시지 "**{welcome_message}**"를 표시.
        3.  **메인 콘텐츠 (위젯 그리드):**
            - 아래 위젯들을 CSS Grid 레이아웃을 사용하여 카드 스타일로 보기 좋게 배치.
            - 각 위젯의 `content_idea`를 바탕으로, **구체적인 목업 콘텐츠(목록, 숫자, 텍스트 등)를 생성**.
            {widgets_html}
        4.  **네비게이션/사이드바 (선택 사항):**
            - 아래의 빠른 링크들을 포함한 사이드바를 왼쪽에 배치.
            - 빠른 링크 목록: <ul>{quick_links_html}</ul>
        ---
        **최종 결과물:** 설명 없이, 완성된 HTML 코드만 응답.
        """
        system_message = "You are a UI/UX designer creating a personalized, user-centric main page. Respond ONLY with the raw HTML code."
        
        cache_key = f"html_user_main_page_{hash(prompt)}"
        
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        try:
            response = self.client.messages.create(
                model="claude-3-opus-20240229",
                max_tokens=4000,
                temperature=0.1,
                system="You are a UI/UX designer creating a personalized, user-centric main page. Respond ONLY with the raw HTML code.",
                messages=[{"role": "user", "content": prompt}]
            )
            
            html_code = response.content[0].text
            self.cache[cache_key] = html_code
            return html_code
            
        except Exception as e:
            print(f"메인 페이지 HTML 생성 중 오류 발생: {str(e)}")
            return None

class UiMockupAgent:
    def __init__(self, requirements_data: List[Dict], openai_api_key: str, anthropic_api_key: str):
        self.requirements_data = requirements_data
        self.openai_client = OpenAI(api_key=openai_api_key) if openai_api_key else None
        self.anthropic_client = anthropic.Anthropic(api_key=anthropic_api_key) if anthropic_api_key else None
        
        self.loader = RequirementsLoader()
        self.analyzer = None
        self.planner = None
        self.generator = None
        self.system_overview = "N/A"
        self.feature_specs = None
        self.defined_pages_with_details = None
        
        # 초기화 및 분석 실행
        self._initialize()
    
    def _initialize(self):
        """에이전트 초기화 및 요구사항 분석을 수행합니다."""
        if not self.requirements_data:
            raise ValueError("요구사항 데이터가 없습니다.")
            
        if not self.openai_client or not self.anthropic_client:
            raise ValueError("OpenAI 또는 Anthropic API 키가 설정되지 않았습니다.")
        
        # 요구사항 분석
        self.analyzer = RequirementsAnalyzer(self.requirements_data, self.openai_client)
        self.system_overview = self.analyzer.get_system_overview()
        self.feature_specs = self.analyzer.get_feature_specifications()
        
        if not self.feature_specs:
            raise ValueError("기능 명세를 추출할 수 없습니다.")
        
        # 페이지 계획 수립
        self.planner = MockupPlanner(self.feature_specs, self.system_overview, self.openai_client)
        self.defined_pages_with_details = self.planner.define_pages_and_allocate_features()
        
        if not self.defined_pages_with_details:
            raise ValueError("페이지 계획을 수립할 수 없습니다.")
        
        # HTML 생성기 초기화
        self.generator = HtmlGenerator(self.anthropic_client)

    def run(self, output_dir="./generated_mockups_final_v3"):
        print("에이전트 실행 시작...")
        self.requirements_data = self.loader.load_from_file(self.requirements_file_path)
        if not self.requirements_data: return

        if not self.openai_client or not self.anthropic_client:
            print("OpenAI 또는 Anthropic API 키가 설정되지 않았습니다.")
            return

        self.analyzer = RequirementsAnalyzer(self.requirements_data, self.openai_client)
        self.system_overview = self.analyzer.get_system_overview()
        feature_specs = self.analyzer.get_feature_specifications()
        if not feature_specs: return

        print(f"\n시스템 개요: {self.system_overview}")
        print(f"추출된 주요 기능 명세 수: {len(feature_specs)}")

        self.planner = MockupPlanner(feature_specs, self.system_overview, self.openai_client)
        defined_pages_with_details = self.planner.define_pages_and_allocate_features()
        if not defined_pages_with_details: return

        print(f"\n기획된 페이지 수: {len(defined_pages_with_details)}")

        # 3. HtmlGenerator에 openai_client 대신 anthropic_client 전달
        self.generator = HtmlGenerator(self.anthropic_client) 
        
        # ... (이하 실행 로직은 사용자 원본과 동일하게 유지) ...
        successfully_generated_page_details = []
        for page_plan in defined_pages_with_details:
             page_name_from_plan = page_plan.get("page_name")
             if not page_name_from_plan: continue
             print(f"\n'{page_name_from_plan}' HTML 생성 시도 (with Claude)...")
             html_code = self.generator.generate_html_for_page_plan(page_plan, feature_specs)
             if html_code and "오류 발생" not in html_code:
                 self.generator.save_html_to_file(page_name_from_plan, html_code, output_dir)
                 successfully_generated_page_details.append(page_plan)
        
        if successfully_generated_page_details:
            # 4-1. 사용자 메인 페이지 콘텐츠 기획 (Planner 호출)
            print("\n--- 4. 사용자 메인 페이지 기획 단계 (OpenAI) ---")
            main_page_plan = self.planner.plan_user_main_page()
            
            # 4-2. 기획안에 따라 사용자 메인 페이지 생성 (Generator 호출)
            if main_page_plan:
                print("\n--- 5. 사용자 메인 페이지 생성 단계 (Claude) ---")
                project_name_base = os.path.splitext(os.path.basename(self.requirements_file_path))[0]
                project_name_display = project_name_base.replace("_", " ").replace("-", " ").title() + " Mockup"

                main_page_html_code = self.generator.generate_user_main_page_html(
                    main_page_plan=main_page_plan,
                    defined_pages_details=successfully_generated_page_details,
                    project_name=project_name_display
                )
                
                if main_page_html_code and "오류" not in main_page_html_code:
                    self.generator.save_html_to_file("index", main_page_html_code, output_dir)
                else:
                    print("🔴 사용자 메인 페이지 생성에 실패했습니다.")
        
        print("\n--- 최종 생성 결과 ---")