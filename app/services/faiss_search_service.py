# app/services/faiss_search_service.py
import os
import json
import numpy as np
import faiss
from typing import List, Tuple, Dict, Any, Optional
from app.core.config import FAISS_INDEX_DIR, METADATA_STORAGE_DIR
from app.services.embedding_service import get_embeddings_for_texts # 단일 텍스트 임베딩 함수도 필요할 수 있음, 또는 배치 사용

# 임베딩 모델은 embedding_service에서 로드된 것을 공유하거나 여기서도 로드할 수 있음
# from app.services.embedding_service import hf_model

def load_faiss_index_and_metadata(
    index_filename: str,
    metadata_filename: str
) -> Tuple[Optional[faiss.Index], Optional[List[Dict[str, Any]]]]:
    index_path = os.path.join(FAISS_INDEX_DIR, index_filename)
    metadata_path = os.path.join(METADATA_STORAGE_DIR, metadata_filename)

    if not os.path.exists(index_path) or not os.path.exists(metadata_path):
        print(f"FAISS 인덱스({index_path}) 또는 메타데이터 파일({metadata_path})을 찾을 수 없습니다.")
        return None, None
    
    try:
        index = faiss.read_index(index_path)
        with open(metadata_path, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
        return index, metadata
    except Exception as e:
        print(f"FAISS 인덱스 또는 메타데이터 로드 중 오류: {e}")
        return None, None

def search_similar_requirements(
    faiss_index: faiss.Index,
    metadata_list: List[Dict[str, Any]],
    query_text: str,
    top_k: int = 1
) -> List[Tuple[Dict[str, Any], float]]:
    """
    주어진 쿼리 텍스트와 가장 유사한 기존 요구사항을 FAISS에서 검색합니다.
    """
    query_embedding_list = get_embeddings_for_texts([query_text]) # 배치 함수 사용, 단일 텍스트라도 리스트로 전달
    if not query_embedding_list or query_embedding_list[0] is None:
        print(f"쿼리 텍스트 임베딩 실패: {query_text[:100]}")
        return []
    
    query_vector = np.array([query_embedding_list[0]]).astype('float32')
    
    distances, indices = faiss_index.search(query_vector, top_k)
    
    results = []
    for i in range(len(indices[0])):
        idx = indices[0][i]
        if idx != -1: # 유효한 인덱스인 경우
            # metadata_list의 각 항목은 원본 요구사항 item 또는 선택된 필드를 담은 dict
            results.append((metadata_list[idx], float(distances[0][i])))
    return results