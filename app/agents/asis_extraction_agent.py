import json
from typing import List, Dict, Optional, Any
from collections import defaultdict
from langchain_core.documents import Document
from pydantic import BaseModel, Field

# app.services.llm_call_service에서 call_gpt를 가져오는 것은 그대로 유지합니다.
from app.services.llm_call_service import call_gpt 

# --- Pydantic 모델: 데이터 구조의 안정성과 명확성을 위해 사용 ---
class NonFunctionalAspects(BaseModel):
    performance: str = Field(default="정보 없음", description="성능 현황")
    security: str = Field(default="정보 없음", description="보안 현황")
    data: str = Field(default="정보 없음", description="데이터 현황")
    ui_ux: str = Field(default="정보 없음", description="UI/UX 현황")
    stability: str = Field(default="정보 없음", description="안정성 현황")
    constraints: str = Field(default="정보 없음", description="제약사항 현황")

class TechArchitecture(BaseModel):
    tech_stack: str = Field(default="정보 없음", description="기술 스택 현황")
    architecture: str = Field(default="정보 없음", description="아키텍처 현황")
    integration_systems: str = Field(default="정보 없음", description="연동 시스템 현황")

class ExtractedAsIsChunk(BaseModel):
    overview: str = Field(default="정보 없음", description="시스템 개요")
    dynamic_functional_areas: Dict[str, str] = Field(default={}, description="주요 기능 영역")
    non_functional_aspects: NonFunctionalAspects = Field(default_factory=NonFunctionalAspects)
    tech_architecture: TechArchitecture = Field(default_factory=TechArchitecture)


# --- 3단계 아키텍처를 위한 프롬프트들 ---

# 1단계: 청크별 추출 프롬프트 (안정성 강화)
EXTRACTION_SYSTEM_PROMPT = """
당신은 RFP 문서의 한 부분을 분석하여 **현재 시스템(AS-IS)의 현황과 특징에만 집중**하여 보고서의 각 섹션별로 정보를 추출하고 요약하는 전문가입니다.
주어진 텍스트 청크에서 아래 JSON 구조에 맞춰 현재 시스템의 현황을 **최대한 상세하고 구체적으로** 추출하십시오.

- **절대 추측하거나 없는 내용을 만들어내지 마십시오.** 오직 주어진 텍스트 청크에 **명시적/암시적으로 언급된 현재 상태(AS-IS) 정보만** 작성합니다.
- **미래(To-Be) 지향적인 내용은 철저히 제외**하십시오. (예: "필요합니다", "개선 예정", "목표")
- **현재 상태를 설명하는 한계점, 결함, 특정 방식에 대한 언급이 있다면, 이는 중요한 AS-IS 정보이므로 반드시 상세히 기술**하십시오.
- 해당 섹션에 대한 AS-IS 정보가 텍스트 청크에 없으면, 해당 JSON 필드의 기본값("정보 없음" 또는 빈 객체 `{}`)을 그대로 유지하십시오.
- **'dynamic_functional_areas'에는 언급된 현재 시스템의 모든 핵심 기능들을 기능별로 상세히 설명하십시오.** 각 기능의 **현재 운영 방식, 특징, 한계점** 등을 구체적으로 서술해야 합니다.
- 최종 결과물은 반드시 지정된 JSON 형식이어야 합니다.
"""

# 2단계: 병합된 정보 요약 프롬프트 (기존 프롬프트 재활용)
THEMATIC_SYNTHESIS_PROMPT = """
You are a professional technical writer. You will be given a topic (e.g., "성능") and a list of raw text snippets related to that topic.
Your task is to synthesize these snippets into a single, comprehensive, and well-written paragraph in Korean.

**Instructions:**
1.  Read all the provided snippets to understand the full context of the topic.
2.  **Merge duplicate information and resolve redundancies.**
3.  Write a single, coherent paragraph that logically presents all the unique information.
4.  Start with a clear topic sentence.
5.  Ensure the paragraph is factual and based ONLY on the provided snippets.
6.  Your output should be ONLY the final synthesized paragraph in Markdown format.
"""
# 2.5단계: 기능 클러스터링을 위한 프롬프트
FUNCTION_CLUSTERING_SYSTEM_PROMPT = """
당신은 현행 시스템의 기능 목록을 분석하여 비즈니스 관점에서 의미 있는 대분류로 그룹화하는 시스템 아키텍트입니다.
사용자로부터 기능과 설명이 담긴 JSON 데이터를 받게 됩니다.
당신의 임무는 이 기능들을 분석하여 3~5개의 논리적인 카테고리로 묶는 것입니다.
카테고리 이름은 보고서 소제목으로 사용하기에 적합하도록 명확하고 전문적으로 작성해야 합니다. (예: "핵심 뱅킹 서비스", "보안 및 인증 체계")

당신의 출력은 **반드시 유효한 JSON 객체**여야 합니다.
- JSON 객체의 키는 당신이 정의한 '카테고리명'입니다.
- JSON 객체의 값은 해당 카테고리에 속하는 기능들의 '원래 키 이름'을 담은 리스트(array)입니다.
- 다른 설명이나 부가적인 텍스트 없이 JSON 객체만 반환하십시오.
"""

FUNCTION_CLUSTERING_USER_PROMPT = """
아래는 그룹화해야 할 기능 목록이 담긴 JSON 데이터입니다. 지시에 따라 이 기능들을 분석하고 그룹화한 결과를 JSON 객체로 반환해 주십시오.

[기능 목록 데이터]
{function_list_json}
"""

# 3단계: 최종 보고서 조립을 위한 마스터 프롬프트 (품질 극대화)
FINAL_REPORT_GENERATION_PROMPT = """
You are a master technical writer and senior consultant creating a professional "AS-IS 시스템 분석 보고서".
You will receive a consolidated summary of the current system's aspects. Your task is to synthesize this information into a comprehensive, well-structured, and fluently written report in Korean Markdown.

**CRITICAL INSTRUCTIONS:**

1.  **Follow the Exact Hierarchical Structure:**
    - `## 1. 현행 시스템 개요`
    - `## 2. 주요 기능 현황` (Use `### 가. [카테고리명]` for each functional category)
    - `## 3. 비기능 요구사항 현황` (Use `### 가.`, `### 나.` for each sub-section)
    - `## 4. 기술 아키텍처 현황` (Use `### 가.`, `### 나.` for each sub-section)

2.  **Create a Narrative Overview (## 1. 현행 시스템 개요):**
    - Don't just copy the overview summary.
    - Weave together the most critical points from the `개요`, `성능`, and `제약사항` summaries to create a compelling introductory paragraph that sets the stage for the entire report. It should explain what the system is, its business goals, and its key characteristics.

3.  **Elaborate on Each Section:**
    - **For `## 2. 주요 기능 현황`,** you will be given summaries for several high-level functional categories.
        - Present each category with a `### 가.`, `### 나.` heading.
        - Under each heading, write a comprehensive, flowing paragraph based on the provided summary for that category.
        - **Do not just list features.** Explain how the functions within the category work together to achieve a business purpose, mentioning specific functionalities as examples within the narrative.
    - **For all other sections,** write a detailed paragraph for each item based **only** on the provided summaries.
    - If a summary for any section is "정보 없음" or missing, professionally state that "해당 항목에 대한 구체적인 현황 정보가 명시되지 않았습니다."
    - Ensure the final report flows logically and is written in a professional, formal tone.

Your final output must be the complete report in a single Markdown text.

---
**[Consolidated AS-IS Summaries]**

{consolidated_summaries}
"""

def extract_asis_and_generate_report(chunks: List[Document]) -> str:
    """
    (오류 수정 최종본) RFP 청크로부터 AS-IS 분석 보고서를 생성하는 전체 파이프라인
    """
    
    # --- 1단계: 안정적인 청크별 정보 추출 ---
    print("--- 1단계: 청크별 AS-IS 정보 추출 시작 ---")
    extracted_chunks: List[ExtractedAsIsChunk] = []
    schema_json_string = json.dumps(ExtractedAsIsChunk.model_json_schema(), indent=2, ensure_ascii=False)

    for i, doc in enumerate(chunks):
        print(f"  청크 {i+1}/{len(chunks)} 처리 중...")
        user_prompt = f"""
        다음 RFP 텍스트 청크에서 현재 시스템(As-Is) 관련 정보를 아래 JSON 스키마에 맞춰 추출하여 반환해 주십시오.

        --- JSON 스키마 ---
        {schema_json_string}
        ---

        --- 텍스트 청크 시작 ---
        {doc.page_content}
        --- 텍스트 청크 끝 ---
        """
        extracted_dict = call_gpt(
            system_prompt=EXTRACTION_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            is_json_output=True
        )
        
        if extracted_dict:
            try:
                extracted_chunks.append(ExtractedAsIsChunk(**extracted_dict))
            except Exception as e:
                print(f"  경고: 청크 {i+1} 처리 중 Pydantic 모델 변환 오류 발생. 건너뜁니다. 오류: {e}")

    if not extracted_chunks:
        return "문서 전체에서 분석 가능한 AS-IS 정보를 찾을 수 없었습니다."
    print(f"--- 1단계 완료: {len(extracted_chunks)}개의 청크에서 정보 추출 ---")


    # --- 2단계: 추출 결과의 병합 ---
    print("\n--- 2단계: 추출 결과 병합 시작 ---")
    merged_data = defaultdict(lambda: defaultdict(list))
    for chunk in extracted_chunks:
        if chunk.overview and chunk.overview != "정보 없음":
            merged_data["overview"]["overview"].append(chunk.overview)
        for name, desc in chunk.dynamic_functional_areas.items():
            if desc and desc != "정보 없음":
                merged_data["dynamic_functional_areas"][name].append(desc)
        for aspect, value in chunk.non_functional_aspects:
            if value and value != "정보 없음":
                merged_data["non_functional_aspects"][aspect].append(value)
        for aspect, value in chunk.tech_architecture:
            if value and value != "정보 없음":
                merged_data["tech_architecture"][aspect].append(value)
    print("--- 2단계 완료 ---")

    # --- 2.5단계: 기능 클러스터링 및 그룹별 요약 ---
    print("\n--- 2.5단계: 기능 클러스터링 및 그룹별 요약 시작 ---")
    clustered_functional_summaries = {}
    if merged_data["dynamic_functional_areas"]:
        all_functions = {k: " ".join(v) for k, v in merged_data["dynamic_functional_areas"].items()}
        
        # [수정] 분리된 시스템/사용자 프롬프트를 사용하여 LLM 호출
        function_clusters = call_gpt(
            system_prompt=FUNCTION_CLUSTERING_SYSTEM_PROMPT,
            user_prompt=FUNCTION_CLUSTERING_USER_PROMPT.format(
                function_list_json=json.dumps(all_functions, indent=2, ensure_ascii=False)
            ),
            is_json_output=True
        )
        
        if not function_clusters or not isinstance(function_clusters, dict):
            print("  경고: 기능 클러스터링에 실패했거나 유효한 결과를 받지 못했습니다. 기능 현황 섹션을 건너뜁니다.")
            function_clusters = {}

        if function_clusters:
            print(f"  기능 클러스터링 완료: {list(function_clusters.keys())}")
            for category, func_keys in function_clusters.items():
                snippets_for_category = [desc for key in func_keys if key in merged_data["dynamic_functional_areas"] for desc in merged_data["dynamic_functional_areas"].get(key, [])]
                if not snippets_for_category:
                    continue
                
                unique_snippets = sorted(list(set(snippets_for_category)), key=snippets_for_category.index)
                synthesis_prompt = f"Topic: '{category}'\n\nPlease synthesize the following snippets into a comprehensive paragraph about this functional area:\n- " + "\n- ".join(unique_snippets)
                
                summary = call_gpt(system_prompt=THEMATIC_SYNTHESIS_PROMPT, user_prompt=synthesis_prompt)
                clustered_functional_summaries[category] = summary
    print("--- 2.5단계 완료 ---")


    # --- 3단계: 최종 보고서 조립 (변경 없음) ---
    print("\n--- 3단계: 최종 보고서 생성 시작 ---")
    final_summaries = {}
    
    all_other_aspects = {**merged_data["overview"], **merged_data["non_functional_aspects"], **merged_data["tech_architecture"]}
    for key, snippets in all_other_aspects.items():
        if not snippets:
            continue
        unique_snippets = sorted(list(set(snippets)), key=snippets.index)
        synthesis_prompt = f"Topic: '{key}'\n\nPlease synthesize the following snippets:\n- " + "\n- ".join(unique_snippets)
        
        summary = call_gpt(system_prompt=THEMATIC_SYNTHESIS_PROMPT, user_prompt=synthesis_prompt)
        final_summaries[key] = summary

    key_map = {
        "overview": "개요", "performance": "성능", "security": "보안", "data": "데이터",
        "ui_ux": "UI/UX", "stability": "안정성", "constraints": "제약사항",
        "tech_stack": "기술 스택", "architecture": "아키텍처", "integration_systems": "연동 시스템"
    }
    
    summary_text_parts = []
    for key, name in key_map.items():
        summary_text_parts.append(f"### {name}\n{final_summaries.get(key, '정보 없음')}")
    
    if clustered_functional_summaries:
        summary_text_parts.append("\n### 주요 기능 카테고리별 현황")
        for category, desc in clustered_functional_summaries.items():
            summary_text_parts.append(f"- **카테고리명: {category}**\n  - 요약: {desc}")
    
    consolidated_summaries_text = "\n\n".join(summary_text_parts)

    final_report = call_gpt(
        system_prompt=FINAL_REPORT_GENERATION_PROMPT,
        user_prompt=FINAL_REPORT_GENERATION_PROMPT.format(consolidated_summaries=consolidated_summaries_text)
    )
    
    print("--- 3단계 완료. 보고서 생성 성공! ---")
    
    return final_report