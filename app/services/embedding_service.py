# app/services/embedding_service.py
from sentence_transformers import SentenceTransformer
from app.core.config import SENTENCE_TRANSFORMER_MODEL
from tqdm import tqdm # 백그라운드 실행 시 tqdm 로그는 파일로 리디렉션 필요
from typing import List, Optional

# 모델은 애플리케이션 시작 시 한 번 로드하거나, 첫 호출 시 로드 (지연 로딩)
# 여기서는 간단하게 모듈 로드 시 초기화
try:
    hf_model = SentenceTransformer(SENTENCE_TRANSFORMER_MODEL)
    print(f"SentenceTransformer 모델 '{SENTENCE_TRANSFORMER_MODEL}' 로드 완료.")
except Exception as e:
    hf_model = None
    print(f"SentenceTransformer 모델 로드 실패: {e}")

def get_embeddings_for_texts(texts: List[str]) -> List[Optional[List[float]]]:
    if not hf_model:
        print("오류: 임베딩 모델이 로드되지 않았습니다.")
        return [None] * len(texts)

    embeddings_list: List[Optional[List[float]]] = []
    try:
        # SentenceTransformer는 리스트를 직접 받아 배치 처리 가능
        # show_progress_bar는 콘솔 환경에서 유용, FastAPI 백그라운드에서는 다른 로깅 방식 고려
        raw_embeddings = hf_model.encode(texts, show_progress_bar=True)
        embeddings_list = [emb.tolist() for emb in raw_embeddings]
    except Exception as e:
        print(f"텍스트 임베딩 중 오류 발생: {e}")
        # 오류 발생 시, 각 텍스트에 대해 None 반환 또는 부분 성공 처리
        # 여기서는 전체 실패로 간주하고 모든 텍스트에 대해 None 반환
        return [None] * len(texts)
    return embeddings_list