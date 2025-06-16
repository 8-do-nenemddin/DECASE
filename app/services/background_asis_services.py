import os

from markdown_pdf import MarkdownPdf, Section

from app.services import file_processing_service
from app.agents import asis_extraction_agent 
from app.core import config

def clean_markdown_fences(markdown_text: str) -> str:
    """
    LLM이 생성한 마크다운 텍스트에서 코드 블록 래퍼(```markdown ... ```)를 제거합니다.
    """
    if not isinstance(markdown_text, str):
        return ""

    # 앞뒤 공백 및 줄바꿈 문자를 먼저 제거합니다.
    text = markdown_text.strip()
    
    # 시작 부분의 ```markdown 또는 ``` 제거
    if text.startswith("```markdown"):
        text = text[len("```markdown"):].lstrip()
    elif text.startswith("```"):
        text = text[len("```"):].lstrip()
        
    # 끝 부분의 ``` 제거
    if text.endswith("```"):
        text = text[:-3].rstrip()
        
    return text

def convert_md_to_pdf(md_file_path: str) -> str:
    """
    주어진 마크다운 파일을 PDF로 변환합니다.
    """
    # 저장될 PDF 파일 경로 설정 (원본 파일명에서 확장자만 변경)
    pdf_file_path = os.path.splitext(md_file_path)[0] + ".pdf"
    
    print(f"\n'{md_file_path}' 파일을 PDF로 변환 시작...")

    try:
        # 마크다운 파일 내용 읽기
        with open(md_file_path, 'r', encoding='utf-8') as f:
            markdown_content = f.read()
            
        lines = markdown_content.strip().split('\n')
        if lines and lines[0].strip().startswith('```markdown') and lines[-1].strip() == '```':
            print("  [INFO] 마크다운 코드 블록 구문을 감지하여 제거합니다.")
            markdown_content = '\n'.join(lines[1:-1])

        
        # PDF에 적용할 한글 폰트 CSS 정의
        user_css = """
        body { 
            font-family: 'NanumGothic', 'Malgun Gothic', sans-serif; 
        }
        @page {
            margin: 1in;
        }
        """

        pdf = MarkdownPdf(toc_level=2)
        pdf.add_section(Section(markdown_content), user_css=user_css)
        pdf.save(pdf_file_path)
        
        print(f"✅ PDF 변환 성공! '{pdf_file_path}' 파일이 생성되었습니다.")
        return pdf_file_path

    except FileNotFoundError:
        print(f"❌ 오류: 원본 파일 '{md_file_path}'을(를) 찾을 수 없습니다.")
        return None
    except Exception as e:
        print(f"❌ PDF 변환 중 오류가 발생했습니다: {e}")
        return None
    
# === OpenAI(GPT)용 서비스 함수 (수정됨) ===
def process_asis_report(file_path: str, file_type: str):
    """
    (수정됨) OpenAI(GPT)를 사용하여 AS-IS 문서를 처리하고,
    결과물(.md)과 함께 PDF 파일도 생성하는 전체 파이프라인.
    """
    try:
        # 1. PDF에서 Document 객체 리스트 추출
        print(f"파일 처리 시작: {os.path.basename(file_path)}")
        docs = file_processing_service.extract_pages_as_documents(file_path)
        if not docs:
            raise ValueError("PDF에서 텍스트를 추출하지 못했습니다.")

        # 2. Document 리스트를 청크로 분할
        print("문서를 청크로 분할 중...")
        chunks = file_processing_service.create_chunks_from_documents(
            docs,
            chunk_size=config.CHUNK_SIZE,
            chunk_overlap=config.CHUNK_OVERLAP
        )
        if not chunks:
            raise ValueError("문서를 청크로 분할하지 못했습니다.")

        # 3. GPT용 에이전트 함수 호출하여 마크다운 보고서 생성
        print("AS-IS 보고서 생성 시작 (LLM 호출)...")
        markdown_report = asis_extraction_agent.extract_asis_and_generate_report(chunks)
        
        # 4. 마크다운(.md) 결과 저장
        base_filename = os.path.splitext(os.path.basename(file_path))[0]
        output_md_path = os.path.join(config.OUTPUT_ASIS_DIR, f"{base_filename}_asis_report_openai.md")
        
        with open(output_md_path, 'w', encoding='utf-8') as f:
            f.write(markdown_report)
        print(f"AS-IS 분석 보고서(MD)가 다음 경로에 저장되었습니다: {output_md_path}")
        
        # <<< --- 6. 저장된 마크다운 파일을 PDF로 변환 --- >>>
        pdf_path = convert_md_to_pdf(output_md_path)
        
        # 성공 시 MD와 PDF 경로 모두 반환 (백그라운드 작업이므로 직접 사용되진 않음)
        return {"status": "success", "report_path_md": output_md_path, "report_path_pdf": pdf_path}

    except Exception as e:
        print(f"AS-IS 문서 처리(OpenAI) 중 오류 발생: {e}")
        return {"status": "error", "message": str(e)}
    

# # app/services/background_asis_services.py
# import os
# from app.services import file_processing_service
# from app.agents import asis_extraction_agent 
# from app.core import config # config에서 직접 설정값 가져오기

# def process_asis_document(file_path: str, file_type: str):
#     """
#     AS-IS 문서를 청킹, 필터링하여 최종 보고서를 생성하는 전체 파이프라인.
#     """
#     try:
#         # 1. PDF에서 Document 객체 리스트 추출
#         docs = file_processing_service.extract_pages_as_documents(file_path)
#         if not docs:
#             raise ValueError("PDF에서 텍스트를 추출하지 못했습니다.")

#         # 2. Document 리스트를 청크(Document 리스트)로 분할 (config 값 사용)
#         chunks = file_processing_service.create_chunks_from_documents(
#             docs,
#             chunk_size=config.CHUNK_SIZE,
#             chunk_overlap=config.CHUNK_OVERLAP
#         )
#         if not chunks:
#             raise ValueError("문서를 청크로 분할하지 못했습니다.")

#         # 3. 에이전트를 통해 청크 필터링 및 최종 보고서 생성
#         markdown_report = asis_extraction_agent.filter_and_generate_report(chunks)
        
#         # 4. 결과 저장
#         base_filename = os.path.splitext(os.path.basename(file_path))[0]
#         # config에 정의된 출력 디렉토리 사용
#         output_md_path = os.path.join(config.OUTPUT_ASIS_DIR, f"{base_filename}_asis_report.md")
        
#         with open(output_md_path, 'w', encoding='utf-8') as f:
#             f.write(markdown_report)
            
#         print(f"AS-IS 분석 보고서가 다음 경로에 저장되었습니다: {output_md_path}")
#         return {"status": "success", "report_path": output_md_path}

#     except Exception as e:
#         print(f"AS-IS 문서 처리 중 심각한 오류 발생: {e}")
#         # import traceback; traceback.print_exc() # 디버깅 시 사용
#         return {"status": "error", "message": str(e)}


# app/services/background_asis_services.py
