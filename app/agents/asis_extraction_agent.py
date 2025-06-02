# app/services/as_is_extraction_service.py
from openai import OpenAI
import json
from typing import Dict, Any, List, Optional
from langchain.text_splitter import RecursiveCharacterTextSplitter
from app.core.config import OPENAI_API_KEY, LLM_MODEL
from app.schemas.asis import ExtractedAsIsChunk

# client = OpenAI(api_key=OPENAI_API_KEY)

def split_text_into_chunks(text: str, chunk_size: int = 15000, chunk_overlap: int = 500) -> List[str]:
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        separators=["\\n\\n", "\\n", ". ", "? ", "! ", " ", ""],
        keep_separator=False,
    )
    return text_splitter.split_text(text)

def summarize_chunk_for_as_is_agent(chunk_text: str) -> Optional[ExtractedAsIsChunk]:
    client_instance = OpenAI(api_key=OPENAI_API_KEY)
    extraction_system_prompt = """
    당신은 RFP 문서의 한 부분을 분석하여 **현재 시스템(AS-IS)의 현황과 특징에만 집중**하여 보고서의 각 섹션별로 정보를 추출하고 요약하는 전문가입니다.
    주어진 텍스트 청크에서 아래 JSON 구조에 맞춰 현재 시스템의 현황을 **최대한 상세하고 구체적으로** 추출하십시오.

    - **절대 추측하거나 없는 내용을 만들어내지 마십시오.** 오직 주어진 텍스트 청크에 **명시적/암시적으로 언급된 현재 상태(AS-IS) 정보만** 작성합니다.
    - 특히, "필요합니다", "개선 예정", "목표", "해야 한다"와 같은 **미래(To-Be) 지향적인 내용은 철저히 제외**하십시오.
    - "현재 이러이러한 문제가 있습니다", "현재 이러이러한 제약사항이 있습니다", "현재 이러이러한 기능만 지원합니다", "현재 이러이러한 방식입니다"와 같이 **현재 상태를 설명하는 부정적인 표현, 한계점, 결함, 또는 특정 방식에 대한 언급이 있다면, 이는 중요한 AS-IS 정보이므로 반드시 상세히 기술**하십시오.
    - 해당 섹션에 대한 AS-IS 정보가 텍스트 청크에 없으면, 해당 JSON 필드는 **"정보 없음"**으로 명확히 남겨 두십시오. 빈 문자열("")보다 "정보 없음"이 더 명확합니다.
    - 모든 추출 내용은 요약하거나 중요한 부분을 발췌하되, 가능한 한 원문의 의미를 살려 구체적으로 작성하십시오.
    - **'dynamic_functional_areas'에는 RFP에 언급된 현재 시스템의 모든 핵심 기능들을 기능별로 상세히 설명하십시오.** 각 기능의 **현재 운영 방식, 특징, 한계점** 등을 구체적으로 서술해야 합니다.
    """

    user_prompt_chunk = f"""
    다음 RFP 텍스트 청크에서 현재 시스템(As-Is) 관련 정보를 위 JSON 구조에 맞춰 추출하여 반환해 주십시오.

    --- 추출할 정보 구조 (JSON 형식) ---
    {{
        "overview": "현재 JBANK 시스템의 목적, 구축 배경, 시스템 구성, 재구축 목표 중 현행 시스템과 관련된 부분, 현재 거래 처리량(TPS), 향후 거래량 증가 예측 등 현행 시스템의 전반적인 특징을 상세히 요약합니다. '재구축을 통해 성능 향상 및 보안 강화'와 같은 목표 언급이 있더라도, 이것이 현재 시스템의 한계를 내포한다면 AS-IS 정보로 볼 수 있습니다. (예: 현재 시스템은 50 TPS를 처리하며, 특정 이벤트 시 성능 저하 우려가 있음)",
        "dynamic_functional_areas": {{
            "기능명1": "기능1의 현재 운영 방식, 특징, 한계점 등 상세 설명 (예: (O2O) 비대면 대출 연장 신청 프로세스 개발 적용, (O2O) 비대면 서류 작성 시스템 개발 적용, 신한은행 마이데이터 서비스(머니버스) 연동(웹뷰 방식) 등 RFP에 언급된 현재 구현된 기능 중심으로 상세히 작성)",
            "기능명2": "기능2에 대한 현재 상세 설명",
            "기능명N": "기능N에 대한 현재 상세 설명"
        }},
        "non_functional_aspects": {{
            "performance": "현재 시스템의 성능 관련 특징 (예: 현재 거래 처리량 50TPS, 향후 5년간 100TPS 증가 예상, 서비스의 성능 및 속도 보장 필요성 언급을 통해 현재의 잠재적 한계점 유추, 이벤트 시 사용자 급증에 따른 성능 저하 우려 등 현재 상황에 대한 언급)을 구체적인 수치와 함께 상세히 기술",
            "security": "현재 시스템의 보안 체계 (예: 로그 적재 시 비밀번호 마스킹 처리, 계정계 시스템과의 통신 시 암호화 방식 적용), 금융감독원 보안성 심의 가이드 준수 필요성 언급을 통해 현재 보안 수준 유추, 보안 취약점 예방 및 앱 접근성 인증마크 획득 방안 필요성 언급을 통해 현재의 부족한 부분을 AS-IS로 명시",
            "data": "현재 데이터 관리 방식 (예: 데이터 이행 계획 수립 여부, 데이터 매핑/초기 이행/변경 이행 포함 여부, 데이터 검증 및 정비 절차 유무, 데이터 오류 유형별 대응 방안 제시 여부)의 상세 현황을 기술",
            "ui_ux": "현재 모바일 뱅킹 앱의 사용자 인터페이스 및 사용자 경험에 대한 RFP의 언급 (예: 모바일 최적화 웹 개발 프레임워크 사용 권장이라는 문구를 통해 현재 최적화가 부족할 수 있음을 유추, 웹표준/웹접근성 자동 검증 기능 유무, UX 개선안 정의 및 사용자 검증 필요성 언급을 통해 현재 UX의 부족함 유추)을 상세히 설명",
            "stability": "시스템의 가용성 (예: 이중화 및 HA(Active-Active) 구성 원칙, DR 시스템은 싱글 구조로 제안되어 운영 환경과 동일한 시스템 구조와 소프트웨어 구성 갖춤), 서비스 오류 감지 및 원인 파악을 위한 거래 추적 구조 필요성 언급을 통해 현재 추적 기능의 부족함 유추 등 안정성 관련 현황을 구체적으로 설명",
            "constraints": "현재 시스템이 가진 기술적 (예: 개방형 구조의 Linux 기반, DB 서버는 Oracle RAC 구성), 운영적 한계 또는 외부 제약사항 (예: 프로젝트 진행 중 금융 관련 법규의 신설/변경, 감독당국의 지시사항 수용 필요)을 상세히 기술"
        }},
        "tech_architecture": {{
            "tech_stack": "현재 시스템이 사용하는 주요 기술 스택 (예: 운영체제 - 개방형 구조의 Linux 기반, 데이터베이스 - Oracle RAC 구성, 모바일 웹 개발 프레임워크 사용 권장(react.js, vue.js, spring boot)을 통해 현재 어떤 기술이 사용되거나 부족한지 유추)을 구체적으로 나열",
            "architecture": "현재 시스템의 전반적인 아키텍처 (예: 3 Tier(WEB-AP-DB) 구조, 주요 시스템 구간별 고가용성 확보, 컨텐츠 관리 방식(일괄 다운로드 방식 추정)) 및 구성 방식(다중화, 상호백업)을 상세히 설명",
            "integration_systems": "현재 연동하고 있는 주요 내부/외부 시스템 (예: 신한은행 마이데이터 서비스(머니버스) 연동(웹뷰 방식), 당행 통합모니터링(H/W, 어플리케이션, 네트워크 전구간 모니터링, 장애감지, 실시간 모니터링, 장애처리, 백업/복구 대응)과 연동) 현황 및 연동 방식을 구체적으로 설명"
        }}
    }}
    ---

    --- 텍스트 청크 시작 ---
    {chunk_text}
    --- 텍스트 청크 끝 ---
    """
    extracted_info_str = ""
    try:
        response = client_instance.chat.completions.create(
            model=LLM_MODEL, # 또는 AS_IS_LLM_MODEL
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": extraction_system_prompt},
                {"role": "user", "content": user_prompt_chunk}
            ],
            temperature=0.0
        )
        extracted_info_str = response.choices[0].message.content
        extracted_info_dict = json.loads(extracted_info_str)
        return ExtractedAsIsChunk(**extracted_info_dict) # Pydantic 모델로 변환
    except json.JSONDecodeError as e:
        print(f"   경고: 청크 처리 중 JSON 파싱 오류: {e}. 응답 미리보기: {extracted_info_str[:200]}...")
        return None
    except Exception as e:
        print(f"   오류: 청크 처리 중 LLM API 호출 또는 처리 실패: {e}")
        return None