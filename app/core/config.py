# app/core/config.py
import os
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o") # 기본값 gpt-4o

INPUT_DIR = "app/docs"
OUTPUT_CSV_DIR = "app/output/SRS_csv"
OUTPUT_JSON_DIR = "app/output/SRS_json"
OUTPUT_ASIS_DIR = "app/output/ASIS_md"
OUTPUT_MOCKUP_DIR = "app/output/mockup_html"

CHUNK_SIZE = 2000
CHUNK_OVERLAP = 200

if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY 환경 변수를 설정해주세요.")