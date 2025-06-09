# app/agents/mockup_generator_agent.py
import re
import os

from app.services.file_processing_service import sanitize_filename

# client = OpenAI(api_key=OPENAI_API_KEY)
class HtmlGenerator:
    def __init__(self, openai_client):
        self.client = openai_client
        self.analysis_cache = {}

    def _call_gpt(self, prompt_text, cache_key, system_message="You are a helpful AI assistant.", temperature=0.15): # 기본 temperature 조정
        # ... (이전과 동일) ...
        if not self.client:
            # ...
            return None
        if cache_key in self.analysis_cache:
            # ...
            return self.analysis_cache[cache_key]
        
        try:
            # ... (API 호출 부분) ...
            print(f"GPT HTML 생성 요청 중 (키: {cache_key})...")
            response = self.client.chat.completions.create(
                model="gpt-4o", # 또는 최신/최고 성능 모델
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": prompt_text}
                ],
                temperature=temperature 
            )
            result = response.choices[0].message.content
            
            match = re.search(r'```(html)?\s*([\s\S]*?)\s*```', result, re.IGNORECASE)
            if match:
                html_code = match.group(2).strip()
            else:
                html_code = result.strip()

            self.analysis_cache[cache_key] = html_code
            return html_code
        except Exception as e:
            # ... (오류 처리) ...
            print(f"GPT HTML 생성 API 호출 중 오류 발생 ({cache_key}): {e}")
            return f"\n<!DOCTYPE html>\n<html><head><title>오류</title></head><body><h1>HTML 생성 중 오류 발생</h1><p>키: {cache_key}</p><p>오류 내용: {e}</p></body></html>"


    def generate_html_for_page_plan(self, page_plan_details, all_feature_specs):
        # ... (메서드 상단 및 상세 요구사항 변수 준비는 이전 답변과 거의 동일) ...
        page_title_ko = page_plan_details.get("page_title_ko", "목업 페이지")
        # ... (기타 변수들: page_name_en, page_description, target_actors, default_placeholder, user_story_str, acceptance_criteria_str, ui_elements_list_str, data_fields_str, layout_guidelines_str, basic_style_guide_str, api_interactions_str, key_ui_elements_suggestion, features_details_for_prompt, is_responsive, detailed_functional_requirements_section_str, detailed_interface_requirements_section_str - 이전 답변에서 복사)
        # (이하 생략된 변수 준비 코드는 바로 이전 답변을 참고해주세요)
        # ----- 변수 준비 시작 (이전 답변 내용 일부 복사) -----
        page_name_en = page_plan_details.get("page_name", "UnknownPage")
        page_description = page_plan_details.get("page_description", "N/A")
        target_actors = ", ".join(page_plan_details.get("target_actors", [])) if isinstance(page_plan_details.get("target_actors"), list) else str(page_plan_details.get("target_actors", ""))

        default_placeholder = "제공되지 않음"
        user_story_str = page_plan_details.get("user_story", default_placeholder)
        acceptance_criteria_list = page_plan_details.get("acceptance_criteria", [])
        acceptance_criteria_str = "\n".join([f"- {ac}" for ac in acceptance_criteria_list]) if acceptance_criteria_list else default_placeholder
        
        ui_elements_list = page_plan_details.get("ui_elements_needed", [])
        ui_elements_list_str = "\n".join([f"- {elem}" for elem in ui_elements_list]) if ui_elements_list else default_placeholder
        
        data_fields_list = page_plan_details.get("data_fields_to_display", [])
        data_fields_str = "\n".join([f"- {field}" for field in data_fields_list]) if data_fields_list else default_placeholder
        
        layout_guidelines_str = page_plan_details.get("layout_guidelines", default_placeholder)
        basic_style_guide_str = page_plan_details.get("basic_style_guide", default_placeholder)
        
        api_interactions_list = page_plan_details.get("api_interactions", [])
        api_interactions_str = ""
        if api_interactions_list:
            for interaction in api_interactions_list:
                api_interactions_str += f"- 요소/기능: {interaction.get('action_description', interaction.get('element_id', 'N/A'))}\n"
                api_interactions_str += f"  엔드포인트: {interaction.get('endpoint', 'N/A')}\n"
                api_interactions_str += f"  HTTP 메서드: {interaction.get('method', 'N/A')}\n"
                if interaction.get('request_fields'):
                    api_interactions_str += f"  요청 데이터 필드: {', '.join(interaction.get('request_fields'))}\n"
                if interaction.get('response_notes'):
                    api_interactions_str += f"  예상 응답/처리: {interaction.get('response_notes')}\n\n"
        else:
            api_interactions_str = "이 페이지와 직접 관련된 주요 API 연동 정보가 명시되지 않음."

        key_ui_elements_suggestion = page_plan_details.get("key_ui_elements_suggestion", "기본 콘텐츠 영역")
        included_feature_ids = page_plan_details.get("included_feature_ids", [])
        features_details_for_prompt = ""
        if included_feature_ids:
            for req_id in included_feature_ids:
                feature = next((spec for spec in all_feature_specs if spec["id"] == req_id), None)
                if feature:
                    desc = feature.get('description_detailed', feature.get('description', 'N/A'))
                    acc_crit = feature.get('acceptance_criteria_summary', feature.get('acceptance_criteria', 'N/A'))
                    features_details_for_prompt += f"- 기능 ID {feature['id']}: {desc}\n  (수용 조건 요약: {acc_crit})\n\n"
        else:
            features_details_for_prompt = "이 페이지에 직접 할당된 세부 기능 명세가 없습니다.\n"
        is_responsive = True

        if user_story_str == default_placeholder and acceptance_criteria_str == default_placeholder:
            detailed_functional_requirements_section_str = "(요청 시 제공된 상세 기능 정보 없음)"
        else:
            detailed_functional_requirements_section_str = f"""
        - 사용자 스토리: {user_story_str}
        - 주요 수용 기준 (Acceptance Criteria):
{acceptance_criteria_str}"""

        if (ui_elements_list_str == default_placeholder and
            data_fields_str == default_placeholder and
            layout_guidelines_str == default_placeholder and
            basic_style_guide_str == default_placeholder):
            detailed_interface_requirements_section_str = "(요청 시 제공된 상세 인터페이스 정보 없음)"
        else:
            detailed_interface_requirements_section_str = f"""
        - 이 페이지에 필요한 주요 UI 요소 목록 (형식: 요소타입:이름:표시텍스트 또는 설명):
{ui_elements_list_str}
        - 페이지에 표시되어야 할 주요 데이터 필드 (테이블, 리스트, 카드 등에 해당):
{data_fields_str}
        - 기본 레이아웃 가이드라인: {layout_guidelines_str}
        - 초기 스타일/브랜딩 가이드라인 (제공된 경우): {basic_style_guide_str}"""
        # ----- 변수 준비 끝 -----

        prompt = f"""
        웹 페이지의 HTML 목업 코드를 생성해주십시오. 이 목업은 단순한 와이어프레임을 넘어, **전문 UI 디자이너가 Stitch나 Figma와 같은 전문 도구를 사용하여 제작한 수준의 매우 높은 시각적 완성도와 전문성**을 목표로 합니다. 
        API 연동을 준비하는 구조를 갖추되, JavaScript 없이 순수 HTML/CSS로 작성됩니다.

        **목표 컨텍스트:** Figma에서 상세 UI 디자인으로 즉시 활용 가능하며, 이후 백엔드 API와 연동하여 실제 작동하는 애플리케이션으로 개발될 **최소 실행 가능한 기초 자료(MCP)**입니다.
        **스타일 목표:** **극도로 깔끔하고(immaculate), 정교하며(sophisticated), 현대적인(modern) 미니멀리즘 UI 디자인**을 구현합니다. 모든 디자인 요소는 의도적이어야 하며, 최고 수준의 미적 감각을 반영해야 합니다.

        **페이지 기본 정보:**
        - 한글 페이지 제목: "{page_title_ko}"
        - 페이지 영문명 (내부 참조용): "{page_name_en}"
        - 페이지 주요 목적: "{page_description}"
        - 주요 대상 사용자: "{target_actors}"

        **상세 기능 요구사항:**
        {detailed_functional_requirements_section_str}

        **상세 인터페이스 요구사항:**
        {detailed_interface_requirements_section_str}

        **주요 API 연동 정보 (이 페이지에서 예상되는):**
        {api_interactions_str}
        (주: 이 정보를 바탕으로, HTML 요소에 `data-*` 속성 등을 추가하거나, 주석으로 API 연동을 위한 준비를 해주십시오.)

        **페이지에 포함되어야 할 핵심 기능 및 UI 요소 제안 (위 상세 요구사항이 우선):**
        {key_ui_elements_suggestion}

        **참고할 기타 관련 기능 정보:**
        {features_details_for_prompt}

        **HTML 생성 가이드라인 (전문 UI 디자이너 수준):**
        1.  **완전한 HTML 문서 구조** 및 **필수 Meta 태그**를 포함해주십시오.
        2.  **시맨틱 HTML & Figma/개발 친화적 구조:**
            -   HTML5 시맨틱 태그를 최대한 활용하고, 모든 요소는 논리적으로 그룹화되어야 합니다.
            -   CSS 클래스명은 BEM(Block, Element, Modifier) 방법론이나 유사한 체계적인 명명 규칙을 사용하여 매우 명확하고 재사용 가능하도록 작성해주십시오. (예: `class="card product-card product-card--featured"`)
            -   **API 연동 준비:** 데이터 표시 영역에는 명확한 `id`를, 인터랙티브 요소에는 `data-action` 등의 `data-*` 속성을 부여하고, 폼에는 각 `input`에 `name` 속성을 명시해주십시오. API 호출 정보는 주석으로 상세히 기술합니다.
        3.  **인라인 CSS 스타일 (최고 수준의 미니멀 & 모던 디자인):**
            -   **모든 CSS 스타일은 HTML 코드 내 `<style>` 태그 안에 포함**해주십시오.
            -   **전반적인 디자인 철학:** "Less is more, but every detail matters." 모든 디자인 결정은 목적이 있어야 하며, 최고의 사용자 경험과 미적 완성도를 추구합니다. 일반적이거나 미숙해 보이는 스타일링은 절대적으로 피해주십시오.
            -   **정교한 레이아웃(Sophisticated Layouts):**
                -   CSS Grid와 Flexbox를 창의적이고 효과적으로 조합하여, 시각적으로 매우 매력적이고 안정적인 페이지 구조를 설계하십시오. 필요시 비대칭 레이아웃이나 복합 그리드를 적용하여 단조로움을 피하고 디자인에 깊이를 더하십시오.
                -   사용자의 시선을 자연스럽게 유도하는 명확한 시각적 흐름(visual flow)을 만드십시오. 모든 요소는 의도된 위치에 정렬(alignment)되어야 합니다.
            -   **세련된 컴포넌트 스타일링(Refined Component Design):**
                -   버튼, 폼 요소(입력창, 셀렉트박스, 라디오/체크박스), 카드, 내비게이션, 탭, 아코디언, 모달, 툴팁 등 모든 UI 요소는 극도로 세심한 주의를 기울여 스타일링해야 합니다. 각 요소는 명확한 사용성(affordance)과 미적인 아름다움을 동시에 가져야 합니다.
                -   미묘하지만 명확한 `hover`, `focus`, `active`, `disabled` 상태 스타일을 모든 인터랙티브 요소에 일관되게 적용하십시오. (예: `focus` 시 은은한 외곽선 또는 그림자 변화)
            -   **고급 타이포그래피(Advanced Typography):**
                -   정교한 타이포그래피 스케일(typographic scale)과 수직 리듬(vertical rhythm)을 적용하여, 명확한 정보 계층과 뛰어난 가독성을 동시에 달성하십시오.
                -   폰트는 극도로 가독성이 높고 현대적인 산세리프 계열(예: Inter, Figtree, 또는 시스템 UI 폰트 스택 `-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif`)을 사용하십시오.
                -   다양한 텍스트 요소(H1-H6, 본문, 캡션, 인용구 등)에 맞는 정밀한 폰트 크기, 굵기(font-weight), 자간(letter-spacing, 예: -0.01em ~ -0.03em), 행간(line-height, 예: 1.5 ~ 1.8) 설정을 적용하십시오.
            -   **의도적인 색상 팔레트(Intentional Color Palette):**
                -   전문가가 설계한 듯한, 극도로 제한적이고 조화로운 색상 팔레트를 구성하십시오. 주로 밝고 깨끗한 배경(예: `#FFFFFF`, `#F7F7F7`) 위에 매우 높은 명암비를 가지는 텍스트 색상(예: `#111111`, `#333333`)을 사용합니다.
                -   단 하나의 주요 액센트 컬러(예: 세련된 파란색 `#0070C9` 또는 제공된 브랜딩 가이드의 핵심 색상)를 선택하고, 이를 클릭 유도 버튼이나 가장 중요한 하이라이트에만 극도로 절제하여 사용하십시오.
                -   모든 색상 조합은 WCAG AA 수준 이상의 명암비를 확보하여 접근성을 반드시 준수하도록 하십시오.
            -   **전략적인 여백 활용(Strategic Whitespace):**
                -   여백은 디자인의 가장 강력한 도구 중 하나입니다. 콘텐츠 밀도를 낮추고, 각 요소를 명확히 구분하며, 사용자의 집중도를 높이고, 고급스럽고 정돈된 느낌을 극대화하기 위해 **의도적으로 매우 넉넉한 여백**을 모든 요소 주변과 섹션 사이에 배치하십시오.
            -   **섬세한 마이크로 인터랙션(Subtle Micro-interactions):**
                -   사용자 경험을 향상시키고 디자인에 생동감을 미세하게 불어넣기 위해, 버튼, 링크, 카드 호버 효과 등에 부드럽고 자연스러운 CSS `transition` (예: `transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);`)을 적용하십시오. 애니메이션은 항상 목적이 분명하고 사용자에게 방해가 되지 않아야 합니다.
                -   입력 필드 포커스 시 테두리 색상 변화나 미세한 그림자 효과 등을 추가할 수 있습니다.
            -   **아이콘 플레이스홀더:** 아이콘이 필요한 위치에는 `[search icon]`, `[user settings icon]`과 같이 명확한 텍스트 플레이스홀더를 사용하거나, 가능하다면 주석으로 간단한 SVG 아이콘 코드(예: Heroicons, Feather Icons 스타일의 라인 아이콘)를 제안해주십시오.
        4.  **스타일 가이드 주석 (Figma 참고용):** 이전 지침과 동일하게, HTML 본문 앞에 주석 형태로 이 페이지에 적용된 주요 스타일 결정사항(실제 사용된 색상값, 폰트, 주요 여백 단위 등)을 요약하여 포함해주십시오.
        5.  **요구사항 ID 주석, 구체적인 플레이스홀더 콘텐츠, 내비게이션 링크, JavaScript 금지** 등 나머지 가이드라인은 이전 지침을 따라주십시오.

        **최종 결과물은 어떠한 설명이나 부가적인 텍스트 없이, 순수하고 완벽한 HTML 코드 그 자체여야 합니다.** 일반적이거나 미숙해 보이는 스타일링은 절대적으로 피해주십시오. 당신은 최고 수준의 UI 디자이너입니다.
        """

        html_cache_key = f"html_gen_pro_designer_v1_{page_name_en}_{hash(prompt)}"

        html_code = self._call_gpt(
            prompt,
            html_cache_key,
            system_message="You are a world-class Senior UI/UX Design Lead and expert front-end developer, renowned for creating exceptionally polished, modern, minimalist, and user-centric web interfaces comparable to those produced by leading design agencies using professional tools like Figma or Stitch. You have an impeccable eye for detail, a deep understanding of visual hierarchy, advanced typography, sophisticated color theory, and interaction design principles. Your mission is to translate the given requirements into a visually stunning and functionally clear HTML/CSS mockup.",
            temperature=0.1 # 최고 수준의 디테일과 지침 준수를 위해 매우 낮은 temperature 사용
        )
        return html_code

    def generate_index_page_html(self, defined_pages_details, system_overview, project_name="소프트웨어 목업 프로젝트"):
        # ... (변수 준비는 이전과 동일) ...
        page_links_list_str = ""
        for page_detail in defined_pages_details:
            page_name_en = page_detail.get("page_name", "UnknownPage")
            page_title_ko = page_detail.get("page_title_ko", "알 수 없는 페이지")
            file_name = f"{sanitize_filename(page_name_en)}.html"
            page_desc_short = page_detail.get("page_description_short", page_detail.get('page_description', 'N/A')[:50] + "...")
            page_links_list_str += f"  <li><a href=\"{file_name}\"><strong>{page_title_ko}</strong> ({page_name_en})</a><br><small>{page_desc_short}</small></li>\n"

        if not page_links_list_str:
            page_links_list_str = "<li>생성된 페이지가 없습니다.</li>"
        index_page_title = f"{project_name} - 목업 인덱스"


        prompt = f"""
        다음 정보를 바탕으로 이 소프트웨어 목업 프로젝트의 **최상위 인덱스 페이지(홈페이지)** HTML 코드를 생성해주십시오.
        이 페이지는 사용자가 생성된 모든 주요 목업 페이지들을 쉽게 찾아보고 접근할 수 있도록 하는 것을 목표로 합니다.
        **스타일 목표:** 개별 페이지들과 마찬가지로, **전문 UI 디자이너가 만든 것처럼 극도로 깔끔하고, 정교하며, 현대적인 미니멀리즘 UI 디자인**을 적용해주십시오.

        페이지 제목 (HTML title 태그 및 화면 제목용): "{index_page_title}"
        
        시스템 개요:
        {system_overview}

        생성된 주요 페이지 목록 (아래 각 항목을 클릭하면 해당 .html 파일로 이동해야 합니다.):
        <ul class="page-link-list">
        {page_links_list_str}
        </ul>

        **HTML 생성 가이드라인 (인덱스 페이지 - 전문 UI 디자이너 수준):**
        1.  **전체 HTML 문서 구조** 및 **필수 Meta 태그**는 개별 페이지 생성 가이드라인과 동일하게 적용해주십시오.
        2.  **시맨틱 HTML & Figma 친화적 구조**를 적용하며, 클래스명은 체계적으로(예: BEM) 작성해주십시오.
        3.  **인라인 CSS 스타일 (최고 수준의 미니멀 & 모던 디자인):**
            -   **모든 CSS 스타일은 HTML 코드 내 `<style>` 태그 안에 포함**해주십시오.
            -   **주요 디자인 원칙 (전문가 수준):** 개별 페이지 생성 가이드라인에서 언급된 **정교한 레이아웃, 세련된 컴포넌트 스타일링, 고급 타이포그래피, 의도적인 색상 팔레트, 전략적인 여백 활용, 섬세한 마이크로 인터랙션** 원칙들을 이 인덱스 페이지에도 최고 수준으로 충실히 적용해주십시오.
            -   페이지 목록은 각 항목을 명확하게 구분하고(예: 각 링크 항목을 세련된 정보 카드 형태로 표현하거나, 리스트 아이템 간 충분한 간격과 미세한 구분선 사용 등), 사용자가 쉽게 클릭하고 정보를 인지할 수 있도록 매우 높은 수준으로 스타일링 해주십시오.
        4.  **스타일 가이드 주석 (Figma 참고용):** 개별 페이지 생성 가이드라인의 '스타일 가이드 주석' 항목을 참고하여, 이 인덱스 페이지에 적용된 주요 스타일 정보를 HTML 본문 앞에 주석으로 포함해주십시오.
        5.  페이지 상단에는 프로젝트 이름과 함께 시스템 개요를 간략히 소개하는 섹션을 포함하여, 전체 프로젝트의 첫인상을 매우 전문적이고 세련되게 전달해주십시오. (예: 큰 타이틀, 부드러운 배경, 명확한 설명)
        6.  그 아래에는 "생성된 목업 페이지 목록" 등과 같은 명확한 제목으로, 제공된 페이지 목록을 표시해주십시오.
        7.  JavaScript는 포함하지 마십시오. 순수 HTML과 CSS로만 구성된 목업입니다.
        8.  **최종 결과물은 설명이나 다른 텍스트 없이 순수 HTML 코드만이어야 합니다.**
        """
        
        index_cache_key = f"html_gen_index_page_pro_designer_v1_{hash(prompt)}"
        
        html_code = self._call_gpt(
            prompt, 
            index_cache_key,
            system_message="You are a world-class Senior UI/UX Design Lead, creating a stunning, minimalist, and modern index page for a web mockup project. Your work mirrors the quality of top design agencies. Respond ONLY with the raw HTML code.",
            temperature=0.1
        )
        return html_code

    def save_html_to_file(self, page_name, html_content, output_dir="mockups_output_v3"):
        # ... (이전과 동일) ...
        if not os.path.exists(output_dir):
            # ...
            return

        safe_filename = sanitize_filename(page_name) + ".html"
        filepath = os.path.join(output_dir, safe_filename)
        
        try:
            # ...
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(html_content)
            print(f"목업 파일 저장: {filepath}")
        except Exception as e:
            # ...
            print(f"❌ HTML 파일 저장 중 예외 발생 ({safe_filename}): {e}")
            import traceback
            traceback.print_exc()
