# app/agents/mockup_generator_agent.py
import re
import os
import json # 추가
from app.services.file_processing_service import sanitize_filename

class HtmlGenerator:
    def __init__(self, anthropic_client):
        """클라이언트를 Anthropic 클라이언트로 변경합니다."""
        self.client = anthropic_client
        self.analysis_cache = {}

    def _call_claude(self, prompt_text, cache_key, system_message="You are a helpful AI assistant.", temperature=0.1):
        """Claude API를 호출하는 메서드로 변경되었습니다."""
        if not self.client:
            print("❌ Anthropic 클라이언트가 초기화되지 않았습니다. 실제 환경에서는 API 키를 설정해야 합니다.")
            # 개발/테스트를 위한 기본 HTML 반환
            return f"<!DOCTYPE html><html><body><h1>클라이언트 미설정 오류</h1><p>Anthropic 클라이언트가 제공되지 않았습니다.</p><p>키: {cache_key}</p></body></html>"
        
        if cache_key in self.analysis_cache:
            print(f"캐시에서 HTML 로드 중 (키: {cache_key})...")
            return self.analysis_cache[cache_key]
        
        try:
            print(f"Claude HTML 생성 요청 중 (키: {cache_key})...")
            # Anthropic API 호출 방식으로 변경
            response = self.client.messages.create(
                model="claude-4-sonnet-20250514",  # 모델명은 필요에 따라 변경 가능
                max_tokens=4096, # Claude API는 max_tokens가 필수입니다.
                system=system_message, # System prompt를 별도 파라미터로 전달
                messages=[
                    {"role": "user", "content": prompt_text}
                ],
                temperature=temperature 
            )
            # Claude 응답 구조에 맞게 결과 추출
            result = response.content[0].text
            
            # HTML 코드 블록을 추출하는 로직은 그대로 유지
            match = re.search(r'```(html)?\s*([\s\S]*?)\s*```', result, re.IGNORECASE)
            if match:
                html_code = match.group(2).strip()
            # Claude는 종종 코드만 반환하므로, 코드 블록이 없는 경우를 대비
            elif result.strip().startswith('<!DOCTYPE html>'):
                html_code = result.strip()
            else:
                html_code = result.strip() # 만약 다른 설명이 붙었다면 제거

            self.analysis_cache[cache_key] = html_code
            return html_code
        except Exception as e:
            print(f"❌ Claude HTML 생성 API 호출 중 오류 발생 ({cache_key}): {e}")
            return f"\n<!DOCTYPE html>\n<html><head><title>오류</title></head><body><h1>HTML 생성 중 오류 발생</h1><p>키: {cache_key}</p><p>오류 내용: {e}</p></body></html>"

    def generate_html_page(self, page_details, navigation_html, project_name):
        """[연결 기능 추가] 메인/상세 페이지를 구분하고 공통 내비게이션을 주입하는 통합 함수"""
        page_title = page_details.get('page_title_ko', '페이지')
        print(f"📄 '{page_title}' 페이지 생성 요청...")

        if page_details.get('is_main_page'): # 메인 페이지인 경우
            content_prompt = f"이 페이지는 메인 홈 페이지입니다. 환영 메시지('{page_details.get('welcome_message', '')}')와 아래 위젯 아이디어를 바탕으로 대시보드 형태의 콘텐츠를 구성해주세요:\n{json.dumps(page_details.get('widgets', []), ensure_ascii=False, indent=2)}"
        else: # 상세 페이지인 경우
            content_prompt = f"이 페이지는 '{page_title}' 상세 페이지입니다. 다음 핵심 UI 요소 제안에 따라 구체적인 목업 콘텐츠를 구성해주세요:\n{page_details.get('key_ui_elements_suggestion', '')}"
        
    def generate_html_page(self, page_details, navigation_html, project_name):
        """[연결 기능 추가] 메인/상세 페이지를 구분하고 공통 내비게이션을 주입하는 통합 함수"""
        page_title = page_details.get('page_title_ko', '페이지')
        print(f"📄 '{page_title}' 페이지 생성 요청...")

        if page_details.get('is_main_page'): # 메인 페이지인 경우
            content_prompt = f"이 페이지는 메인 홈 페이지입니다. 환영 메시지('{page_details.get('welcome_message', '')}')와 아래 위젯 아이디어를 바탕으로 대시보드 형태의 콘텐츠를 구성해주세요:\n{json.dumps(page_details.get('widgets', []), ensure_ascii=False, indent=2)}"
        else: # 상세 페이지인 경우
            content_prompt = f"이 페이지는 '{page_title}' 상세 페이지입니다. 다음 핵심 UI 요소 제안에 따라 구체적인 목업 콘텐츠를 구성해주세요:\n{page_details.get('key_ui_elements_suggestion', '')}"
        
        prompt = f"""
        **지시:** 다음 정보를 바탕으로, 완전한 단일 HTML 페이지를 생성해줘.
        
        **공통 요구사항:**
        - `<!DOCTYPE html>` 부터 `</html>` 까지 완전한 HTML5 구조를 갖춰야 해.
        - 페이지 제목(`<title>` 태그)은 '{page_title} | {project_name}' 으로 설정.
        - 모든 페이지는 반응형 2단 레이아웃(왼쪽: 사이드바, 오른쪽: 메인 콘텐츠)을 가져야 함.
        
        **[매우 중요] 사이드바 콘텐츠:**
        - 사이드바에는 프로젝트 이름 '{project_name}'을 표시해줘.
        - 그 아래에는, 내가 제공하는 아래의 HTML 링크 목록을 **그대로** 포함시켜줘. 이것이 모든 페이지를 연결하는 핵심이야.
        ```html
        {navigation_html}
        ```

        **메인 콘텐츠:**
        {content_prompt}
        ---
        **최종 결과물:** 다른 설명 없이, 완성된 HTML 코드만 응답해줘.
        """

        cache_key = f"html_gen_unified_v3_{page_details.get('page_title_ko')}_{hash(prompt)}"
        html_code = self._call_claude(
            prompt,
            cache_key,
            system_message="You are a world-class front-end developer and UI designer. Create a complete, single-file HTML page based on the user's request, including sophisticated CSS within a <style> tag. Respond ONLY with the raw HTML code itself, without any surrounding text or explanations.",
            temperature=0.1
        )
        return html_code

    def save_html_to_file(self, page_name, html_content, output_dir="mockups_output_v3"):
        # 이 메서드는 외부 라이브러리에 의존하지 않으므로 변경할 필요가 없습니다.
        if not os.path.exists(output_dir):
            try:
                os.makedirs(output_dir)
            except OSError as e:
                print(f"❌ 출력 디렉토리 생성 실패: {output_dir}, error: {e}")
                return

        safe_filename = sanitize_filename(page_name) + ".html"
        filepath = os.path.join(output_dir, safe_filename)
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(html_content)
            print(f"✅ 목업 파일 저장 완료: {filepath}")
        except Exception as e:
            print(f"❌ HTML 파일 저장 중 예외 발생 ({safe_filename}): {e}")
            import traceback
            traceback.print_exc()

# 기존 함수들은 새로운 `generate_html_page` 메서드로 대체되었으므로,
# 그대로 두거나 삭제할 수 있습니다. 여기서는 혼동을 피하기 위해 그대로 둡니다.
# def generate_html_for_page_plan(...)
# def generate_index_page_html(...)
