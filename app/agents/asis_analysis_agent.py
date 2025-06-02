# app/services/toc_analysis_service.py
from openai import OpenAI
import json
from typing import List, Optional, Dict, Any
from app.core.config import OPENAI_API_KEY, LLM_MODEL # LLM_MODEL 대신 AS_IS_LLM_MODEL 등 구분 가능
from app.schemas.asis import TocEntry, TargetSection
from app.services.file_processing_service import extract_text_for_pages_from_list # 순환참조 피하기 위해 함수 내 임포트 (구조개선 필요)

# client = OpenAI(api_key=OPENAI_API_KEY) # 필요시 모듈 레벨 또는 함수 내에서 생성

def parse_toc_with_llm_agent(toc_raw_text: str) -> Optional[List[TocEntry]]:
    client_instance = OpenAI(api_key=OPENAI_API_KEY)
    system_prompt = """
    당신은 PDF 문서에서 추출된 목차(Table of Contents)의 원시 텍스트를 분석하는 전문가입니다.
    주어진 텍스트를 파싱하여 각 목차 항목의 제목, 페이지 번호, 그리고 해당 항목이 '요구사항' 관련 내용을 담고 있을 가능성을 분석하여 JSON 형태로 반환해야 합니다.
    JSON의 최상위 레벨은 "toc_entries"라는 키를 가진 객체여야 하고, 그 키의 값은 목차 항목 객체들의 리스트여야 합니다.
    **매우 중요: JSON 형식 외에 다른 어떠한 추가적인 설명이나 문장도 포함하지 마십시오.** 당신의 응답은 오직 JSON 객체여야 합니다.
    """
    user_prompt = f"""
    다음은 PDF에서 추출한 목차로 추정되는 텍스트입니다:

    --- 목차 원문 텍스트 시작 ---
    {toc_raw_text}
    --- 목차 원문 텍스트 끝 ---

    이 텍스트를 분석하여 JSON 객체를 반환해주세요. 이 객체는 "toc_entries"라는 키를 가져야 하며,
    이 키의 값은 각 목차 항목을 나타내는 객체들의 리스트여야 합니다.
    각 목차 항목 객체는 다음 키를 가져야 합니다:
    - "title": (문자열) 목차 항목의 전체 제목. 제목 앞의 번호(예: "1.", "II.", "가.", "1.1.", "제1장.")도 포함해주세요.
    - "page": (정수) 해당 항목의 시작 페이지 번호.
    - "is_requirement_related": (불리언) 제목이나 내용을 볼 때, 해당 항목이 '요구사항', '과업 범위', '제안 요청 상세', '기능 명세', '기술 요건', '현황', 'AS-IS', '재구축', '현재 시스템', '개선 방안' 등과 관련된 내용을 다룰 가능성이 높으면 true, 그렇지 않으면 false로 설정해주세요.

    예시 JSON 출력 형식:
    {{
      "toc_entries": [
        {{
          "title": "1. 사업 개요",
          "page": 5,
          "is_requirement_related": false
        }},
        {{
          "title": "III. 제안요청 내용",
          "page": 6,
          "is_requirement_related": true
        }},
        {{
          "title": "3. 상세 요구사항",
          "page": 11,
          "is_requirement_related": true
        }},
        {{
          "title": "* 보안 요구사항 별표",
          "page": 63,
          "is_requirement_related": true
        }},
        {{
          "title": "IV. 현행 시스템 분석",
          "page": 20,
          "is_requirement_related": true
        }},
        {{
          "title": "5. As-Is 시스템 현황",
          "page": 25,
          "is_requirement_related": true
        }}
      ]
    }}

    만약 주어진 텍스트가 유효한 목차로 보이지 않거나 항목을 전혀 파싱할 수 없다면,
    "toc_entries" 키의 값으로 빈 리스트 `[]`를 포함하는 JSON 객체를 반환해주세요. (예: {{"toc_entries": []}})
    """
    llm_response_content = ""
    try:
        response = client_instance.chat.completions.create(
            model=LLM_MODEL, # 또는 LLM_MODEL_FOR_PARSING
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.0
        )
        llm_response_content = response.choices[0].message.content
        parsed_data = json.loads(llm_response_content)

        extracted_list = []
        if isinstance(parsed_data, dict) and "toc_entries" in parsed_data and isinstance(parsed_data["toc_entries"], list):
            extracted_list = parsed_data["toc_entries"]
        else:
            print(f"LLM 응답이 예상된 'toc_entries' 리스트를 포함하는 객체 형식이 아닙니다. 응답: {llm_response_content[:200]}")
            return []

        valid_entries = []
        for entry_dict in extracted_list:
            try:
                # Pydantic 모델로 변환 시도 (데이터 유효성 검사)
                toc_item = TocEntry(**entry_dict)
                valid_entries.append(toc_item) # Pydantic 모델 객체 저장
            except Exception as e_pydantic: # pydantic.ValidationError 등
                print(f"경고: TocEntry 모델 변환 실패. 항목: {entry_dict}, 오류: {e_pydantic}")
        return valid_entries # Pydantic 모델 리스트 반환
    except Exception as e:
        print(f"LLM 목차 파싱 중 오류: {e}. 응답 미리보기: {llm_response_content[:200]}")
        return None


def get_target_sections(parsed_toc_entries: List[TocEntry], total_pages: int) -> List[TargetSection]:
    
    # get_target_sections_from_llm_parsed_toc 함수 로직 (입력: List[TocEntry])
    target_sections_output = []
    sorted_toc_dicts = sorted([entry.model_dump() for entry in parsed_toc_entries], key=lambda x: x.get('page', 0))

    keywords_to_find = [
        "현황 분석", "시스템 현황", "현행 시스템", "시스템 개요",
        "제안요청 내용", "상세 요구사항", "기능 요구사항", "비기능 요구사항",
        "보안 요구사항", "기술 현황", "아키텍처 현황",
        "현재 시스템", "as-is", "재구축", "목표시스템", "개선 방안",
        "사업 목표", "사업 내용"
    ]
    as_is_candidate_entries = []
    for entry_dict in sorted_toc_dicts:
        entry_title_lower = entry_dict.get('title', '').strip().lower()
        is_relevant_by_keyword = any(keyword in entry_title_lower for keyword in keywords_to_find)
        is_relevant_by_llm_flag = entry_dict.get('is_requirement_related', False)
        if is_relevant_by_keyword or is_relevant_by_llm_flag:
            as_is_candidate_entries.append(entry_dict)

    if not as_is_candidate_entries:
        print("경고: LLM 파싱 목차에서 주요 As-Is 관련 섹션을 찾지 못했습니다...")
        return [TargetSection(title='전체 문서 (As-Is 섹션 식별 실패)', start_page=1, end_page=total_pages)]

    # (get_target_sections_from_llm_parsed_toc의 나머지 로직을 여기에 적용하여 final_target_sections_dicts 리스트를 채웁니다)
    # ... 이 부분은 as_is_module.ipynb의 get_target_sections_from_llm_parsed_toc 함수 로직을 가져와서 채워야 합니다.
    # 이 예시에서는 단순화하여 as_is_candidate_entries를 바로 사용합니다 (실제로는 범위 계산 필요)
    for entry_dict in as_is_candidate_entries:
         # 임시로 페이지 범위를 단순하게 설정 (실제로는 다음 항목을 보고 end_page 결정)
        start_page = entry_dict.get('page',1)
        end_page = start_page # 실제 로직에서는 다음 항목 페이지 등을 이용해 계산
        # 다음 항목 찾아서 end_page 설정하는 로직 필요
        idx = sorted_toc_dicts.index(entry_dict)
        if idx + 1 < len(sorted_toc_dicts):
            end_page = max(start_page, sorted_toc_dicts[idx+1].get('page', total_pages + 1) -1)
        else:
            end_page = total_pages
        end_page = min(total_pages, end_page)
        if end_page < start_page: end_page = start_page


        target_sections_output.append(TargetSection(
            title=entry_dict.get('title', 'AS-IS 관련 섹션'),
            start_page=start_page,
            end_page=end_page
        ))
        print(f"식별된 As-Is 관련 섹션: '{entry_dict.get('title')}' (페이지 {start_page}-{end_page})")

    if not target_sections_output:
         return [TargetSection(title='전체 문서 (As-Is 섹션 식별 실패)', start_page=1, end_page=total_pages)]
    return sorted(target_sections_output, key=lambda x: x.start_page)