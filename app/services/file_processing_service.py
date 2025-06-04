# app/services/file_processing_service.py
import json
import csv
import fitz # PyMuPDF
import re
from typing import List, Tuple, Optional, Dict, Any

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

def extract_pages_as_documents(pdf_path: str) -> List[Document]:
    docs = []
    try:
        document_fitz = fitz.open(pdf_path)
        print(f"'{pdf_path}' 파일에서 텍스트 추출 중 (총 {len(document_fitz)} 페이지)...")
        for page_num in range(len(document_fitz)):
            page = document_fitz.load_page(page_num)
            text = page.get_text("text", sort=True)
            if text.strip(): # 내용이 있는 페이지만 추가
                docs.append(Document(page_content=text, metadata={"page_number": page_num + 1}))
            if (page_num + 1) % 10 == 0 or (page_num + 1) == len(document_fitz):
                 print(f"  {page_num + 1}/{len(document_fitz)} 페이지 처리 완료.")
        return docs
    except Exception as e:
        print(f"오류: PDF 파일 '{pdf_path}'에서 텍스트 추출 중 문제가 발생했습니다: {e}")
        return []

def create_chunks_from_documents(
    documents: List[Document],
    chunk_size: int = 2000,
    chunk_overlap: int = 200
) -> List[Document]:
    if not documents:
        return []

    print(f"Document 청킹 중 (청크 크기: {chunk_size}, 중복: {chunk_overlap})...")
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        separators=["\n\n\n", "\n\n", "\n", ". ", " ", ""],
        keep_separator=False
    )
    # split_documents는 Document 리스트를 받아 각 Document를 청킹하고,
    # 원본 Document의 metadata를 청크 Document로 복사해줌.
    chunked_documents = text_splitter.split_documents(documents)
    print(f"총 {len(chunked_documents)}개의 청크(Document) 생성 완료.")
    return chunked_documents

def extract_text_with_page_info_from_pdf(pdf_path: str) -> Tuple[Optional[List[str]], int]:
    # as_is_module.ipynb의 extract_text_with_page_info 함수 내용
    # 반환 타입을 (페이지 텍스트 리스트, 총 페이지 수)로 변경
    try:
        document = fitz.open(pdf_path)
        page_texts = []
        for page_num in range(document.page_count):
            page = document.load_page(page_num)
            text = page.get_text("text", sort=True) # 정렬된 텍스트 추출
            page_texts.append(text.strip())
        return page_texts, document.page_count
    except Exception as e:
        print(f"PDF 텍스트 추출 오류: {e}")
        return None, 0

def extract_text_for_pages_from_list(page_texts_list: List[str], start_page_num: int, end_page_num: int) -> str:
    # as_is_module.ipynb의 extract_text_for_pages 함수 내용 (입력을 리스트로 받도록 수정)
    start_idx = max(0, start_page_num - 1)
    end_idx = min(len(page_texts_list), end_page_num)
    if start_idx >= end_idx:
        return ""
    return "\\n".join(page_texts_list[start_idx:end_idx])


def get_toc_raw_text_from_page_list(page_texts_list: List[str], toc_page_numbers: List[int] = [2,3]) -> Optional[str]:
    # as_is_module.ipynb의 get_toc_raw_text_from_full_text 함수 내용 (입력을 리스트로 받도록 수정)
    toc_texts = []
    for page_num in toc_page_numbers:
        page_content = extract_text_for_pages_from_list(page_texts_list, page_num, page_num)
        if page_content:
            toc_texts.append(page_content)
        else:
            print(f"경고: 목차 페이지로 지정된 {page_num} 페이지에서 텍스트를 찾을 수 없습니다.")
    if not toc_texts:
        return None
    raw_toc = "\\n".join(toc_texts)
    raw_toc = re.sub(r'\\s+', ' ', raw_toc).strip()
    raw_toc = re.sub(r'\\.{2,}', '', raw_toc)
    raw_toc = re.sub(r'\\n{2,}', '\\n', raw_toc)
    return raw_toc

def load_requirements_from_json(filepath: str) -> List[Dict[str, Any]]:
    """지정된 경로에서 JSON 파일을 로드하여 요구사항 목록을 반환합니다."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if isinstance(data, list):
                return data
            else:
                print(f"Error: JSON 파일 ({filepath})이 리스트 형태가 아닙니다.")
                return []
    except FileNotFoundError:
        print(f"Error: JSON 파일을 찾을 수 없습니다 - {filepath}")
        return []
    except json.JSONDecodeError:
        print(f"Error: JSON 파일 디코딩 중 오류 발생 - {filepath}")
        return []
    except Exception as e:
        print(f"Error loading JSON file {filepath}: {e}")
        return []

def save_results_to_json(results: List[Dict[str, Any]], filepath: str):
    """결과 목록을 지정된 경로에 JSON 파일로 저장합니다."""
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"\n결과가 성공적으로 {filepath} 파일에 저장되었습니다.")
    except Exception as e:
        print(f"Error saving results to JSON file {filepath}: {e}")

def convert_json_to_csv(json_file_path: str, csv_file_path: str):
    """
    주어진 JSON 파일에서 데이터를 읽어 지정된 CSV 양식으로 변환하여 저장합니다.
    """
    csv_headers = [
        "요구사항 ID", "유형(기능/비기능)", "요구사항명", "요구사항 상세설명", 
        "대상 업무", "요건처리 상세", "대분류", "중분류", "소분류",
        "중요도", "난이도", "RFP"
    ]
    try:
        with open(json_file_path, 'r', encoding='utf-8') as json_file:
            requirements_data = json.load(json_file)
    except FileNotFoundError:
        print(f"오류: JSON 파일 '{json_file_path}'를 찾을 수 없습니다.")
        raise
    except json.JSONDecodeError as e:
        print(f"오류: JSON 파일 '{json_file_path}' 파싱 중 오류 발생: {e}")
        raise
    except Exception as e:
        print(f"오류: JSON 파일 '{json_file_path}'을 여는 중 오류 발생: {e}")
        raise

    if not isinstance(requirements_data, list):
        if isinstance(requirements_data, dict):
            requirements_data = [requirements_data]
        else:
            msg = f"오류: JSON 데이터의 최상위 구조가 리스트 또는 단일 객체가 아닙니다 (타입: {type(requirements_data)})."
            print(msg)
            raise ValueError(msg)
            
    try:
        with open(csv_file_path, 'w', newline='', encoding='utf-8-sig') as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow(csv_headers)
            for req in requirements_data:
                if not isinstance(req, dict):
                    print(f"경고: 요구사항 데이터 리스트 내에 딕셔너리가 아닌 항목 발견. 건너<0xEB><0x9A><0x84>니다: {req}")
                    continue
                
                row_to_write = [
                    req.get("id", ""),
                    req.get("type", ""),
                    req.get("description_name", ""),
                    req.get("description_content", ""),
                    req.get("target_task", ""),
                    req.get("processing_detail", ""),
                    req.get("category_large", ""),
                    req.get("category_medium", ""),
                    req.get("category_small", ""),
                    req.get("importance", ""),
                    req.get("difficulty", ""),
                    req.get("rfp_page", "")
                ]
                writer.writerow(row_to_write)
        print(f"성공: '{json_file_path}' 파일의 내용이 '{csv_file_path}' CSV 파일로 성공적으로 변환되었습니다.")
    except IOError as e:
        print(f"오류: CSV 파일 '{csv_file_path}'을(를) 쓰거나 여는 중 I/O 오류 발생: {e}")
        raise
    except Exception as e:
        print(f"CSV 변환 중 예기치 않은 오류 발생: {e}")
        raise