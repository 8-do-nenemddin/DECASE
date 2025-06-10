# app/services/mockup_service.py
import os
import json
from typing import List, Tuple
from app.core.config import INPUT_DIR, OUTPUT_MOCKUP_DIR
from app.services.file_processing_service import sanitize_filename
from app.agents.mockup_agent import UiMockupAgent

def run_mockup_generation_pipeline(
    input_data: str,
    output_folder_name: str = None
) -> List[Tuple[str, str]]:
    """
    목업 생성 파이프라인을 실행하고 생성된 HTML 파일들의 내용을 반환합니다.
    
    Args:
        input_data (str): JSON 형식의 입력 데이터
        output_folder_name (str, optional): 출력 폴더 이름
        
    Returns:
        List[Tuple[str, str]]: (파일 경로, 파일 내용) 튜플의 리스트
    """
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
    
    if not OPENAI_API_KEY or not ANTHROPIC_API_KEY:
        raise ValueError("OpenAI 또는 Anthropic API 키가 설정되지 않았습니다.")
    
    # JSON 문자열을 파싱하여 Python 객체로 변환
    try:
        requirements_data = json.loads(input_data)
    except json.JSONDecodeError as e:
        raise ValueError(f"입력 데이터 JSON 파싱 실패: {str(e)}")
    
    agent = UiMockupAgent(
        requirements_data=requirements_data,  # 파싱된 Python 객체 전달
        openai_api_key=OPENAI_API_KEY,
        anthropic_api_key=ANTHROPIC_API_KEY
    )
    
    # 목업 생성 및 결과 수집
    generated_files = []
    
    # 각 페이지 생성
    for page_plan in agent.defined_pages_with_details:
        page_name = page_plan.get("page_name")
        if not page_name:
            continue
            
        html_code = agent.generator.generate_html_for_page_plan(page_plan, agent.feature_specs)
        if html_code and "오류 발생" not in html_code:
            # 파일 경로에서 한글을 영문으로 변환
            safe_page_name = sanitize_filename(page_name)
            file_path = f"{safe_page_name}.html"
            # HTML 내용을 UTF-8로 인코딩
            html_content = html_code.encode('utf-8').decode('utf-8')
            generated_files.append((file_path, html_content))
    
    # 메인 페이지 생성
    if generated_files:
        main_page_plan = agent.planner.plan_user_main_page()
        if main_page_plan:
            project_name = output_folder_name or "Mockup Project"
            main_page_html = agent.generator.generate_user_main_page_html(
                main_page_plan=main_page_plan,
                defined_pages_details=agent.defined_pages_with_details,
                project_name=project_name
            )
            if main_page_html and "오류" not in main_page_html:
                # 메인 페이지 HTML도 UTF-8로 인코딩
                main_page_content = main_page_html.encode('utf-8').decode('utf-8')
                generated_files.append(("index.html", main_page_content))
    
    return generated_files