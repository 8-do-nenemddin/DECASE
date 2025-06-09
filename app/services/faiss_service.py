# app/services/faiss_service.py
import os
import json
import numpy as np
import faiss
from typing import List, Dict, Any, Tuple, Optional

from app.services.file_processing_service import prepare_data_for_faiss
from app.services.embedding_service import get_embeddings_for_texts, hf_model # 모델 차원 접근 위해 hf_model 임포트
from app.core.config import FAISS_INDEX_DIR, METADATA_STORAGE_DIR

def build_and_save_faiss_index(
    processed_data_items: List[Dict[str, Any]], # prepare_data_for_faiss의 결과
    faiss_index_filename: str, # 예: "my_index.faiss"
    metadata_filename: str     # 예: "my_metadata.json"
) -> Tuple[Optional[str], Optional[str]]:
    """
    처리된 데이터로부터 텍스트를 추출하여 임베딩하고, FAISS 인덱스와 메타데이터를 저장합니다.
    성공 시 (인덱스 파일 경로, 메타데이터 파일 경로) 튜플을, 실패 시 (None, None)을 반환합니다.
    """
    if not processed_data_items:
        print("FAISS 인덱싱을 위한 데이터가 없습니다.")
        return None, None

    texts_to_embed = [item["embedding_text_source"] for item in processed_data_items]
    all_metadata = [item["metadata"] for item in processed_data_items]

    embeddings = get_embeddings_for_texts(texts_to_embed)

    valid_embeddings_np_list = []
    final_metadata_list_for_valid_embeddings = []

    for metadata_item, emb_vector in zip(all_metadata, embeddings):
        if emb_vector is not None:
            valid_embeddings_np_list.append(emb_vector)
            final_metadata_list_for_valid_embeddings.append(metadata_item)

    if not valid_embeddings_np_list:
        print("유효한 임베딩이 없어 FAISS 인덱스를 생성할 수 없습니다.")
        return None, None
    
    embeddings_array = np.array(valid_embeddings_np_list).astype('float32')

    try:
        if hf_model is None: # 임베딩 모델 로드 확인
             raise ValueError("SentenceTransformer 모델이 로드되지 않았습니다.")
        dimension = hf_model.get_sentence_embedding_dimension() # 모델로부터 차원 가져오기
        
        index = faiss.IndexFlatL2(dimension)
        index.add(embeddings_array)
        print(f"FAISS 인덱스 생성 완료. {len(valid_embeddings_np_list)}개 벡터 추가됨.")
    except Exception as e:
        print(f"FAISS 인덱스 생성 중 오류: {e}")
        return None, None

    index_file_full_path = os.path.join(FAISS_INDEX_DIR, faiss_index_filename)
    metadata_file_full_path = os.path.join(METADATA_STORAGE_DIR, metadata_filename)

    try:
        faiss.write_index(index, index_file_full_path)
        with open(metadata_file_full_path, "w", encoding="utf-8") as f_meta:
            json.dump(final_metadata_list_for_valid_embeddings, f_meta, ensure_ascii=False, indent=2)
        print(f"저장 완료: 인덱스 -> {index_file_full_path}, 메타데이터 -> {metadata_file_full_path}")
        return index_file_full_path, metadata_file_full_path
    except Exception as e:
        print(f"FAISS 인덱스 또는 메타데이터 파일 저장 중 오류: {e}")
        return None, None