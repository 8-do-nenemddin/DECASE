# app/services/mockup_service.py
import os
import json
from typing import List, Tuple, Dict, Any
from app.core.config import OPENAI_API_KEY, ANTHROPIC_API_KEY

# 새롭게 리팩토링된 UiMockupAgent를 임포트합니다.
from app.agents.mockup.mockup_agent import UiMockupAgent

def run_mockup_generation_pipeline(
    input_data: str,
    output_folder_name: str | None = None
) -> List[Tuple[str, str]]:
    """
    요청 데이터를 받아 UiMockupAgent를 실행하고,
    생성된 HTML 파일들의 (이름, 내용) 리스트를 반환하는 파이프라인입니다.

    Args:
        input_data (str): JSON 형식의 요구사항 명세서 데이터
        output_folder_name (str, optional): 출력 폴더 이름 (프로젝트 이름으로 활용)

    Returns:
        List[Tuple[str, str]]: (파일 경로, 파일 내용) 튜플의 리스트
    """

    if not OPENAI_API_KEY or not ANTHROPIC_API_KEY:
        raise ValueError("OpenAI 또는 Anthropic API 키가 설정되지 않았습니다.")

    try:
        # Pydantic 모델 리스트를 Python 딕셔너리 리스트로 변환
        requirements_data: List[Dict[str, Any]] = json.loads(input_data)
    except json.JSONDecodeError as e:
        raise ValueError(f"입력 데이터 JSON 파싱 실패: {str(e)}")

    # 1. UiMockupAgent 인스턴스 생성
    # 생성자에서 모든 분석과 기획이 완료됩니다.
    agent = UiMockupAgent(
        requirements_data=requirements_data,
        openai_api_key=OPENAI_API_KEY,
        anthropic_api_key=ANTHROPIC_API_KEY
    )

    # 2. 프로젝트 이름 결정
    # output_folder_name이 없으면 시스템 개요에서 추정된 이름을 사용할 수 있습니다.
    # 여기서는 간단하게 기본값을 사용합니다.
    project_name = output_folder_name or "생성된 목업 프로젝트"

    # 3. 에이전트 실행 및 결과 반환
    # agent.run() 메서드가 (파일명, HTML 내용) 리스트를 직접 반환합니다.
    generated_files = agent.run(project_name=project_name)

    return generated_files