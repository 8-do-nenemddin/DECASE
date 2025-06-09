import os
import traceback

from fastapi import APIRouter, BackgroundTasks, UploadFile, File, HTTPException

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
from app.core.config import OUTPUT_ASIS_DIR


def run_as_is_analysis_background(pdf_path: str, report_filename: str):
    try:
        print(f"As-Is 분석 백그라운드 작업 시작: {pdf_path}")
        page_texts, total_pages = extract_text_with_page_info_from_pdf(pdf_path)
        if not page_texts:
            raise ValueError("PDF에서 텍스트를 추출하지 못했습니다.")

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


        as_is_report_content = generate_as_is_report_service(
            page_texts_list=page_texts,
            total_pages=total_pages,
            target_sections=target_sections
        )

        output_report_path = os.path.join(OUTPUT_ASIS_DIR, report_filename)
        with open(output_report_path, "w", encoding="utf-8") as f:
            f.write(as_is_report_content)

        print(f"As-Is 보고서 생성 완료: {output_report_path}")

    except Exception as e:
        print(f"As-Is 분석 백그라운드 작업 중 오류: {e}")
        traceback.print_exc()
        # (선택) 에러 상태를 파일이나 DB에 기록
    finally:
        # 임시 PDF 파일 삭제
        if os.path.exists(pdf_path):
            try:
                os.remove(pdf_path)
                print(f"임시 PDF 파일 삭제: {pdf_path}")
            except Exception as e_del:
                print(f"임시 PDF 파일 삭제 오류: {e_del}")
