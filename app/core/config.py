# app/core/config.py
import os
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o") # 기본값 gpt-4o

if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY 환경 변수를 설정해주세요.")