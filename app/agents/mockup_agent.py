# app/agents/mockup_agent.py
import os
import json
from typing import List, Dict, Any, Tuple
from openai import OpenAI
import anthropic

from app.agents.mockup_analyzer_agent import RequirementsAnalyzer
from app.agents.mockup_planner_agent import MockupPlanner
from app.agents.mockup_generator_agent import HtmlGenerator
from app.services.file_processing_service import sanitize_filename
from typing import List, Dict

class UiMockupAgent:
    """
    요구사항 분석, 페이지 기획, HTML 생성을 총괄하여
    상호 연결된 UI 목업 결과물을 생성하는 메인 에이전트 클래스입니다.
    """
    def __init__(self, requirements_data: List[Dict[str, Any]], openai_api_key: str, anthropic_api_key: str):
        if not requirements_data:
            raise ValueError("요구사항 데이터가 없습니다.")
        if not openai_api_key or not anthropic_api_key:
            raise ValueError("API 키가 설정되지 않았습니다.")

        self.requirements_data = requirements_data
        self.openai_client = OpenAI(api_key=openai_api_key)
        self.anthropic_client = anthropic.Anthropic(api_key=anthropic_api_key)
        
        self.system_overview = "N/A"
        self.feature_specs = []
        self.main_page_plan = {}
        self.defined_pages = []
        
        self._initialize_components_and_plan()

    def _initialize_components_and_plan(self):
        """에이전트 생성 시점에 분석 및 기획을 미리 수행합니다."""
        print("--- 에이전트 초기화: 요구사항 분석 및 페이지 기획 시작 ---")
        
        # 1. 요구사항 분석
        analyzer = RequirementsAnalyzer(self.requirements_data, self.openai_client)
        self.system_overview = analyzer.get_system_overview()
        # [추가] get_system_overview가 실패했는지(예: Fallback 메시지 포함) 확인할 수 있습니다.
        if not self.system_overview or "Fallback" in self.system_overview:
             # 더 강력하게는 여기서 예외를 발생시킬 수 있습니다.
             print("경고: 시스템 개요 생성에 실패하여 대체 데이터를 사용합니다.")

        self.feature_specs = analyzer.get_feature_specifications()
        if not self.feature_specs:
            # [수정] 기능 명세 추출 실패는 치명적이므로 예외를 발생시킵니다.
            raise ValueError("기능 명세를 추출할 수 없어 프로세스를 중단합니다.")
        
        # 2. 페이지 기획
        planner = MockupPlanner(self.feature_specs, self.system_overview, self.openai_client)
        self.main_page_plan = planner.plan_user_main_page()
        self.defined_pages = planner.define_pages_and_allocate_features()
        
        # [수정] 페이지 기획 실패는 치명적이므로 예외를 발생시킵니다.
        if not self.main_page_plan or not self.defined_pages:
            raise ValueError("페이지 계획을 수립할 수 없어 프로세스를 중단합니다.")
            
        print("✅ 에이전트 초기화 및 사전 기획 완료.")

    def _create_navigation_html(self) -> str:
        """모든 페이지 정보를 바탕으로 공통 내비게이션 HTML 메뉴를 생성합니다."""
        main_page_title = self.main_page_plan.get("page_title_ko", "홈")
        nav_html = '<ul>\n'
        nav_html += f'    <li><a href="index.html" class="nav-link">{main_page_title} (Home)</a></li>\n'
        for page in self.defined_pages:
            page_name = page.get("page_name")
            if not page_name:
                continue
            
            file_name = f"{sanitize_filename(page_name)}.html"
            title = page.get('page_title_ko', page_name)
            nav_html += f'    <li><a href="{file_name}" class="nav-link">{title}</a></li>\n'
        nav_html += '</ul>'
        return nav_html

    def run(self, project_name: str) -> List[Tuple[str, str]]:
        """
        초기화 시 기획된 내용을 바탕으로, 연결된 목업 페이지들을 생성하고
        (파일명, 파일 내용) 튜플 리스트를 반환합니다.
        """
        print(f"\n🚀 '{project_name}' 프로젝트 목업 생성 실행 시작...")
        
        generator = HtmlGenerator(self.anthropic_client)
        navigation_html = self._create_navigation_html()
        generated_files = []
        
        all_pages_to_generate = [self.main_page_plan] + self.defined_pages
        
        print(f"--- 총 {len(all_pages_to_generate)}개 페이지 순차 생성 시작 ---")

        for page_plan in all_pages_to_generate:
            page_html = generator.generate_html_page(
                page_details=page_plan,
                navigation_html=navigation_html,
                project_name=project_name
            )
            
            if page_html and "Error" not in page_html:
                if page_plan.get('is_main_page'):
                    filename = "index.html"
                else:
                    filename = f"{sanitize_filename(page_plan.get('page_name'))}.html"
                
                generated_files.append((filename, page_html))
                print(f"👍 '{filename}' 생성 성공")
            else:
                page_title = page_plan.get('page_title_ko', '알 수 없는 페이지')
                print(f"⚠️ '{page_title}' 페이지 생성 실패.")
        
        print(f"\n🎉 모든 작업 완료! 총 {len(generated_files)}개의 파일이 생성되었습니다.")
        return generated_files
