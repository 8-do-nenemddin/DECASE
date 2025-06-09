import os
import traceback
from io import BytesIO

from fastapi import APIRouter, BackgroundTasks, UploadFile, File, HTTPException
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.enums import TA_JUSTIFY
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import markdown

from app.schemas.asis import AsIsReportResponse, TargetSection
from app.services.file_processing_service import (
    extract_text_with_page_info_from_pdf,
    get_toc_raw_text_from_page_list
)
from app.agents.asis_analysis_agent import (
    parse_toc_with_llm_agent,
    get_target_sections
)
from app.agents.report_generation_agent import generate_as_is_report_service

# 한글 폰트 등록
FONT_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'fonts', 'NanumGothic.ttf')
pdfmetrics.registerFont(TTFont('NanumGothic', FONT_PATH))

def run_as_is_analysis(pdf_content: bytes) -> bytes:
    try:
        print(f"As-Is background 분석 시작: {pdf_content}")
        # Create a temporary BytesIO object for the PDF content
        pdf_buffer = BytesIO(pdf_content)
        
        # Extract text from PDF
        page_texts, total_pages = extract_text_with_page_info_from_pdf(pdf_buffer)
        if not page_texts:
            raise ValueError("PDF에서 텍스트를 추출하지 못했습니다.")

        print(f"PDF 텍스트 추출 완료: 총 {total_pages}페이지")
        
        toc_raw_text = get_toc_raw_text_from_page_list(page_texts, toc_page_numbers=[2, 3]) # 예시 목차 페이지

        parsed_toc = None
        if toc_raw_text:
            parsed_toc = parse_toc_with_llm_agent(toc_raw_text)

        target_sections = []
        if parsed_toc:
            target_sections = get_target_sections(parsed_toc, total_pages)
        else: # 목차 파싱 실패 또는 목차 없음
            print("경고: 목차 정보가 없거나 파싱에 실패하여 전체 문서를 대상으로 분석합니다.")
            target_sections = [TargetSection(title='전체 문서', start_page=1, end_page=total_pages)]

        if not target_sections: # 이 경우는 get_target_sections_service가 빈 리스트를 반환했을 때 (예: 후보는 있지만 최종 타겟이 없을때)
            target_sections = [TargetSection(title='전체 문서 (대상 섹션 식별 실패)', start_page=1, end_page=total_pages)]

        # 마크다운 형식
        markdown_content = generate_as_is_report_service(
            page_texts_list=page_texts,
            total_pages=total_pages,
            target_sections=target_sections
        )

        # Convert markdown to HTML
        html_content = markdown.markdown(markdown_content)
        
        # Create PDF using ReportLab
        output_buffer = BytesIO()
        doc = SimpleDocTemplate(output_buffer, pagesize=letter)
        styles = getSampleStyleSheet()
        
        # Create custom style for better readability with Korean font
        custom_style = ParagraphStyle(
            'CustomStyle',
            parent=styles['Normal'],
            fontName='NanumGothic',
            fontSize=11,
            leading=14,
            alignment=TA_JUSTIFY,
            spaceBefore=6,
            spaceAfter=6
        )
        
        # Convert HTML content to paragraphs
        story = []
        for line in html_content.split('\n'):
            if line.strip():
                # Remove HTML tags for simplicity
                clean_text = line.replace('<p>', '').replace('</p>', '')
                p = Paragraph(clean_text, custom_style)
                story.append(p)
                story.append(Spacer(1, 6))
        
        # Build PDF
        doc.build(story)
        output_buffer.seek(0)
        
        return output_buffer.getvalue()

    except Exception as e:
        print(f"As-Is 분석 백그라운드 작업 중 오류: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
