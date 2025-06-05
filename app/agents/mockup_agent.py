
from openai import OpenAI # GPT-4o 사용 시
import json
import os
from app.agents.mockup_analyzer_agent import RequirementsAnalyzer
from app.agents.mockup_generator_agent import HtmlGenerator
from app.agents.mockup_planner_agent import MockupPlanner
from app.services.file_processing_service import sanitize_filename

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
        
class UiMockupAgent:
    def __init__(self, requirements_file_path, openai_api_key):
        self.requirements_file_path = requirements_file_path
        self.openai_client = OpenAI(api_key=openai_api_key) if openai_api_key else None
        self.loader = RequirementsLoader()
        self.requirements_data = None
        self.analyzer = None
        self.planner = None
        self.generator = None
        self.system_overview = "N/A" # 클래스 변수로 system_overview 초기화

    def run(self, output_dir="./generated_mockups_final_v3"):
        print("에이전트 실행 시작...")
        self.requirements_data = self.loader.load_from_file(self.requirements_file_path)
        if not self.requirements_data:
            print("요구사항 로드 실패. 에이전트 실행을 중단합니다.")
            return None

        if not self.openai_client:
            print("OpenAI API 키가 설정되지 않아 GPT 기반 작업을 진행할 수 없습니다. 에이전트 실행을 중단합니다.")
            return None

        self.analyzer = RequirementsAnalyzer(self.requirements_data, self.openai_client)
        self.system_overview = self.analyzer.get_system_overview() # 인스턴스 변수에 저장
        feature_specs = self.analyzer.get_feature_specifications()

        if not feature_specs:
            print("기능 명세 추출 실패 또는 추출된 기능 명세가 없습니다. 에이전트 실행을 중단합니다.")
            return None

        print(f"\n시스템 개요: {self.system_overview}")
        print(f"추출된/준비된 주요 기능 명세 수: {len(feature_specs)}")

        self.planner = MockupPlanner(feature_specs, self.system_overview, self.openai_client)
        defined_pages_with_details = self.planner.define_pages_and_allocate_features()

        if not defined_pages_with_details or not isinstance(defined_pages_with_details, list) or not defined_pages_with_details:
            print("페이지 정의 및 기능 할당 실패. GPT 응답을 확인하거나 MockupPlanner._get_fallback_page_plan()의 결과를 확인하십시오.")
            if not defined_pages_with_details:
                print("기획된 페이지가 없습니다. 실행을 중단합니다.")
                return None

        print(f"\nGPT 또는 대체 로직으로부터 기획된 페이지 수: {len(defined_pages_with_details)}")
        for i, page_plan in enumerate(defined_pages_with_details):
            if isinstance(page_plan, dict):
                print(f"  {i+1}. 페이지 영문명: {page_plan.get('page_name')}, 한글 제목: {page_plan.get('page_title_ko')}, 관련 기능 ID 수: {len(page_plan.get('included_feature_ids', []))}")
            else:
                print(f"  {i+1}. 경고: 페이지 계획 형식이 잘못되었습니다: {page_plan}")

        self.generator = HtmlGenerator(self.openai_client)
        generated_htmls_map = {}
        successfully_generated_page_details = []

        for page_plan in defined_pages_with_details:
            if not isinstance(page_plan, dict):
                print(f"잘못된 페이지 계획 형식으로 HTML 생성을 건너뜁니다: {page_plan}")
                continue

            page_name_from_plan = page_plan.get("page_name")
            if not page_name_from_plan:
                page_name_from_plan = sanitize_filename(page_plan.get("page_title_ko", f"Unknown_Page_{len(generated_htmls_map) + 1}"))
                print(f"경고: page_name이 없어 page_title_ko 또는 임의 이름으로 대체합니다: {page_name_from_plan}")
                page_plan["page_name"] = page_name_from_plan

            print(f"\n'{page_name_from_plan}' HTML 생성 시도...")
            html_code = self.generator.generate_html_for_page_plan(page_plan, feature_specs)

            if html_code and "HTML 생성 중 오류 발생" not in html_code and "OpenAI 클라이언트가 설정되지 않았습니다" not in html_code:
                self.generator.save_html_to_file(page_name_from_plan, html_code, output_dir)
                generated_htmls_map[page_name_from_plan] = True
                successfully_generated_page_details.append(page_plan)
            else:
                print(f"🔴 '{page_name_from_plan}' HTML 목업 생성 실패 또는 오류 포함된 HTML 반환.")
                generated_htmls_map[page_name_from_plan] = False
                if html_code:
                     self.generator.save_html_to_file(f"ERROR_{page_name_from_plan}", html_code, output_dir)

        # --- 인덱스 페이지 생성 로직 (복구 및 유지) ---
        if successfully_generated_page_details:
            print("\n인덱스 페이지 생성 시도...")
            project_name_base = os.path.splitext(os.path.basename(self.requirements_file_path))[0]
            project_name_display = project_name_base.replace("_", " ").replace("-", " ").title() + " 목업"

            index_html_code = self.generator.generate_index_page_html(
                successfully_generated_page_details,
                self.system_overview,
                project_name_display
            )
            if index_html_code and "HTML 생성 중 오류 발생" not in index_html_code:
                self.generator.save_html_to_file("index", index_html_code, output_dir) # 파일명을 "index"로 지정
                print("🟢 인덱스 페이지(index.html) 생성 완료.")
                generated_htmls_map["index.html"] = True # 키를 파일명과 일치
            else:
                print("🔴 인덱스 페이지 생성 실패.")
                generated_htmls_map["index.html"] = False
        else:
            print("\n성공적으로 생성된 개별 페이지가 없어 인덱스 페이지를 생성하지 않습니다.")

        print("\n--- 최종 생성 결과 ---")
        if any(status for status in generated_htmls_map.values()):
            print("🟢 생성된 (또는 시도된) HTML 파일 목록:")
            for idx, (page_key, status) in enumerate(generated_htmls_map.items(), start=1): # page_key 사용
                status_icon = "✅" if status else "❌"
                # page_key가 "index.html"일 수도 있고, page_name일 수도 있으므로, sanitize_filename 적용
                display_filename = page_key if page_key.endswith(".html") else f"{sanitize_filename(page_key)}.html"
                print(f"{idx}. {status_icon} {page_key}: {display_filename}")
            if generated_htmls_map.get("index.html"): # 키를 "index.html"로 확인
                 print(f"\n👉 웹 브라우저에서 '{os.path.join(output_dir, 'index.html')}' 파일을 열어 확인하세요.")
        else:
            print("\n🔴 생성된 유효한 HTML 목업이 없습니다.")

        return generated_htmls_map