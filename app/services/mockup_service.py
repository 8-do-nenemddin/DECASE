# app/services/mockup_service.py
import os
from typing import Optional
from app.core.config import INPUT_DIR, OUTPUT_MOCKUP_DIR
from app.services.file_processing_service import sanitize_filename
from fastapi import UploadFile
from app.agents.mockup_agent import UiMockupAgent


def run_mockup_generation_pipeline(
        input_file_path: str, 
        output_html_path: str
):
    
    agent = UiMockupAgent(input_file_path, os.getenv("OPENAI_API_KEY"))
    agent.run(output_dir=os.path.join(OUTPUT_MOCKUP_DIR, sanitize_filename(output_html_path or "mockup")))