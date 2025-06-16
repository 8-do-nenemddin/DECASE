import os
import tempfile
from pathlib import Path
from markdown_pdf import MarkdownPdf, Section

# 다른 import 구문들은 이미 존재한다고 가정합니다.
from app.core.config import CHUNK_SIZE, CHUNK_OVERLAP
from app.services.file_processing_service import extract_pages_as_documents, create_chunks_from_documents
from app.agents.asis_extraction_agent import extract_asis_and_generate_report


def clean_markdown_fences(markdown_text: str) -> str:
    # (변경 없음)
    if not isinstance(markdown_text, str):
        return ""
    text = markdown_text.strip()
    # ... (이하 동일)
    if text.startswith("```markdown"):
        text = text[len("```markdown"):].lstrip()
    elif text.startswith("```"):
        text = text[len("```"):].lstrip()
    if text.endswith("```"):
        text = text[:-3].rstrip()
    return text


def run_as_is_analysis_and_return_bytes(pdf_content_bytes: bytes, output_pdf_path: Path) -> bytes:
    """
    (수정됨) PDF를 분석하여, 결과를 'output_pdf_path'에 파일로 저장하고,
    동시에 해당 파일의 내용을 바이트(bytes) 객체로 반환합니다.
    """
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_pdf:
        temp_pdf.write(pdf_content_bytes)
        temp_pdf_path = temp_pdf.name

    try:
        # 1 & 2. PDF 텍스트 추출 및 청크 분할 (이전과 동일)
        print(f"임시 파일 처리 시작: {temp_pdf_path}")
        docs = extract_pages_as_documents(temp_pdf_path)
        if not docs: raise ValueError("PDF에서 텍스트를 추출하지 못했습니다.")

        print("문서를 청크로 분할 중...")
        chunks = create_chunks_from_documents(docs, chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)
        if not chunks: raise ValueError("문서를 청크로 분할하지 못했습니다.")

        # 3 & 4. LLM 호출 및 결과 정리 (이전과 동일)
        print("AS-IS 보고서 생성 시작 (LLM 호출)...")
        markdown_report_raw = extract_asis_and_generate_report(chunks)
        markdown_report_clean = clean_markdown_fences(markdown_report_raw)
        
        # 5. PDF 생성
        print("마크다운 콘텐츠를 PDF로 변환 시작...")
        user_css = "body { font-family: 'NanumGothic', 'Malgun Gothic', sans-serif; } @page { margin: 1in; }"
        pdf_converter = MarkdownPdf(toc_level=2)
        pdf_converter.add_section(Section(markdown_report_clean), user_css=user_css)
        
        # 6-1. 지정된 경로에 파일로 먼저 저장합니다.
        print(f"PDF 파일 저장 중... 경로: {output_pdf_path}")
        pdf_converter.save(output_pdf_path)
        print("✅ PDF 파일 저장 성공!")

        # 6-2. 저장된 파일을 다시 '바이너리 읽기 모드(rb)'로 열어서 내용을 읽습니다.
        print(f"저장된 PDF 파일을 바이트로 읽는 중... 경로: {output_pdf_path}")
        with open(output_pdf_path, 'rb') as f:
            output_pdf_bytes = f.read()
        print("✅ PDF 바이트 변환 성공!")
        
        return output_pdf_bytes


    except Exception as e:
        print(f"❌ 분석/저장/변환 중 오류 발생: {e}")
        raise e
    
    finally:
        if os.path.exists(temp_pdf_path):
            os.remove(temp_pdf_path)
            print(f"임시 파일 삭제: {temp_pdf_path}")