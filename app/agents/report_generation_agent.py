# app/services/report_generation_service.py
from openai import OpenAI
from typing import List, Dict, Any, Optional
from app.core.config import OPENAI_API_KEY, LLM_MODEL
from app.schemas.asis import ExtractedAsIsChunk, TargetSection
from app.services.file_processing_service import extract_text_for_pages_from_list # 순환참조 주의, 구조개선 필요할 수 있음
from app.agents.asis_extraction_agent import split_text_into_chunks, summarize_chunk_for_as_is_agent

# client = OpenAI(api_key=OPENAI_API_KEY)

def _consolidate_section_content_logic(section_title: str, all_extracted_texts: List[Any], is_dynamic_functional: bool = False) -> str:
    client_instance = OpenAI(api_key=OPENAI_API_KEY)
    # as_is_module.ipynb의 consolidate_section_content 함수 내용
    # ... (LLM 호출 및 텍스트 통합 로직) ...
    # 아래는 간략화된 예시, 실제 로직은 노트북에서 가져와야 함
    if not all_extracted_texts:
        return "RFP 텍스트에서 관련 정보를 충분히 찾을 수 없습니다."

    if is_dynamic_functional:
        # ... (dynamic_functional_areas 처리 로직) ...
        # combined_texts_for_llm = "..." # 기능 목록을 LLM에 전달할 형태로 구성
        pass # 이 부분은 노트북의 상세 로직 필요
    else:
        unique_texts = list(set([str(text).strip() for text in all_extracted_texts if str(text).strip() and str(text).strip() != "정보 없음"]))
        if not unique_texts:
            return "RFP 텍스트에서 관련 정보를 찾을 수 없습니다."
        # combined_texts_for_llm = "\\n- ".join(unique_texts)
        # if len(combined_texts_for_llm) > 40000: combined_texts_for_llm = combined_texts_for_llm[:40000] + "..."

    # 실제 LLM 호출 부분은 as_is_module.ipynb의 consolidate_section_content 내부 로직을 참조하여 완성해야 합니다.
    # 여기서는 단순화된 문자열 결합으로 대체합니다.
    # 실제 구현 시에는 LLM을 호출하여 자연스러운 문장으로 통합해야 합니다.
    if is_dynamic_functional:
        report_content = ""
        for func_dict_list_item in all_extracted_texts: # all_extracted_texts is List[Dict[str,str]]
            if isinstance(func_dict_list_item, dict):
                for func_name, func_desc in func_dict_list_item.items():
                    if func_desc and func_desc != "정보 없음":
                         report_content += f"#### {func_name}\\n{func_desc}\\n\\n"
        return report_content if report_content else "RFP 텍스트에서 주요 기능을 찾을 수 없습니다."
    else:
        return "\\n".join(unique_texts) if unique_texts else "RFP 텍스트에서 관련 정보를 찾을 수 없습니다."


def generate_as_is_report_service(
    page_texts_list: List[str],
    total_pages: int, # 사용되진 않지만 인터페이스 유지
    target_sections: List[TargetSection]
) -> str:
    # as_is_module.ipynb의 generate_as_is_report_from_rfp_text 함수 로직 기반
    print("\\n[As-Is 보고서 생성] LLM을 사용하여 현황 분석 보고서를 생성합니다...")
    all_as_is_relevant_text_parts = []
    for section_info in target_sections:
        section_text = extract_text_for_pages_from_list(
            page_texts_list, section_info.start_page, section_info.end_page
        )
        if section_text:
            all_as_is_relevant_text_parts.append(section_text)
        # ... (경고 로직 등) ...

    if not all_as_is_relevant_text_parts:
        return "As-Is 보고서 생성이 실패했습니다: 분석할 텍스트가 없습니다."

    combined_rfp_text_for_as_is = "\\n\\n".join(all_as_is_relevant_text_parts)
    rfp_chunks = split_text_into_chunks(combined_rfp_text_for_as_is) # 청킹

    all_extracted_data_typed: Dict[str, List[Any]] = { # 타입 명시
        "overview": [], "dynamic_functional_areas": [],
        "non_functional_aspects": {"performance": [], "security": [], "data": [], "ui_ux": [], "stability": [], "constraints": []},
        "tech_architecture": {"tech_stack": [], "architecture": [], "integration_systems": []}
    }

    for i, chunk in enumerate(rfp_chunks):
        print(f"   청크 {i+1}/{len(rfp_chunks)}에서 정보 추출 중...")
        extracted_info: Optional[ExtractedAsIsChunk] = summarize_chunk_for_as_is_agent(chunk)
        if extracted_info:
            if extracted_info.overview and extracted_info.overview != "정보 없음":
                all_extracted_data_typed["overview"].append(extracted_info.overview)
            if extracted_info.dynamic_functional_areas: # Dict[str, str]
                 all_extracted_data_typed["dynamic_functional_areas"].append(extracted_info.dynamic_functional_areas)

            # Non-functional aspects
            for key, val_list in all_extracted_data_typed["non_functional_aspects"].items(): # val_list는 여기서 타입 검사를 위함
                attr_val = getattr(extracted_info.non_functional_aspects, key, None) if extracted_info.non_functional_aspects else None
                if attr_val and attr_val != "정보 없음":
                    val_list.append(attr_val)

            # Tech architecture
            for key, val_list in all_extracted_data_typed["tech_architecture"].items():
                attr_val = getattr(extracted_info.tech_architecture, key, None) if extracted_info.tech_architecture else None
                if attr_val and attr_val != "정보 없음":
                    val_list.append(attr_val)

    final_as_is_report_parts = []
    final_as_is_report_parts.append("# 현황 분석(AS-IS) 보고서\n")

    overview_content = _consolidate_section_content_logic(
        "시스템 개요", all_extracted_data_typed["overview"]
    )
    final_as_is_report_parts.append("## 1. 현행 시스템 개요\\n")
    final_as_is_report_parts.append(overview_content)

    functional_content = _consolidate_section_content_logic(
        "주요 기능 현황", all_extracted_data_typed["dynamic_functional_areas"], is_dynamic_functional=True
    )
    final_as_is_report_parts.append("\\n\\n## 2. 주요 기능 현황\\n")
    final_as_is_report_parts.append(functional_content)

    # ... (비기능, 기술 아키텍처 섹션 통합 로직은 위와 유사하게 _consolidate_section_content_logic 사용) ...
    final_as_is_report_parts.append("\\n\\n## 3. 비기능 요구사항 현황\\n")
    non_functional_titles = {
        "performance": "가. 성능", "security": "나. 보안", "data": "다. 데이터",
        "ui_ux": "라. UI/UX", "stability": "마. 안정성", "constraints": "바. 제약사항",
    }
    for key, title in non_functional_titles.items():
        content = _consolidate_section_content_logic(
            title, all_extracted_data_typed["non_functional_aspects"][key]
        )
        final_as_is_report_parts.append(f"\\n### {title}\\n{content}")

    final_as_is_report_parts.append("\\n\\n## 4. 기술 아키텍처 현황\\n")
    tech_arch_titles = {
        "tech_stack": "가. 기술 스택", "architecture": "나. 아키텍처", "integration_systems": "다. 연동 시스템",
    }
    for key, title in tech_arch_titles.items():
        content = _consolidate_section_content_logic(
            title, all_extracted_data_typed["tech_architecture"][key]
        )
        final_as_is_report_parts.append(f"\\n### {title}\\n{content}")

    return "\\n".join(final_as_is_report_parts)