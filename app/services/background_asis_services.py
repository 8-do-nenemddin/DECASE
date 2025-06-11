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

import os
import pypandoc  # PDF 변환을 위해 추가
from app.services import file_processing_service
from app.agents import asis_extraction_agent 
from app.core import config

# 헬퍼 함수: 마크다운을 PDF로 변환
def convert_md_to_pdf_with_pandoc(md_file_path: str):
    """
    pandoc을 사용하여 Markdown 파일을 PDF 파일로 변환합니다.
    (같은 이름, 확장자만 .pdf)
    """
    # 출력될 PDF 파일의 전체 경로를 지정합니다.
    output_pdf_path = os.path.splitext(md_file_path)[0] + ".pdf"
    print(f"'{os.path.basename(md_file_path)}'를 PDF로 변환 시작 -> '{os.path.basename(output_pdf_path)}'")
    
    try:
        # pypandoc.convert_file을 사용하여 변환합니다.
        # extra_args에 한글 폰트 및 PDF 엔진 설정을 추가합니다.
        pypandoc.convert_file(
            md_file_path,
            'pdf',
            outputfile=output_pdf_path,
            extra_args=[
                '--pdf-engine=xelatex',      # 한글 지원을 위해 xelatex 엔진 사용
                '-V', 'mainfont=NanumGothic', # 나눔고딕을 기본 폰트로 설정
            ]
        )
        print(f"PDF 변환 성공: {output_pdf_path}")
        return output_pdf_path
    except Exception as e:
        # PDF 변환에 실패하더라도 전체 프로세스가 중단되지 않도록 오류를 기록합니다.
        print(f"오류: PDF 변환 중 문제 발생 - {e}")
        return None

# === OpenAI(GPT)용 서비스 함수 (수정됨) ===
def process_asis_document_openai(file_path: str, file_type: str):
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
        
        os.makedirs(config.OUTPUT_ASIS_DIR, exist_ok=True)
        with open(output_md_path, 'w', encoding='utf-8') as f:
            f.write(markdown_report)
        print(f"AS-IS 분석 보고서(.md) 저장 완료: {output_md_path}")
        
        # 5. (추가된 부분) 생성된 마크다운 파일을 PDF로 변환
        pdf_path = convert_md_to_pdf_with_pandoc(output_md_path)

        return {
            "status": "success", 
            "report_md_path": output_md_path,
            "report_pdf_path": pdf_path  # 반환값에 PDF 경로 추가
        }

    except Exception as e:
        print(f"AS-IS 문서 처리(OpenAI) 중 오류 발생: {e}")
        return {"status": "error", "message": str(e)}