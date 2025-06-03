# DECASE

1. 저장소 클론
```
git clone {저장소 url}
cd DECASE-AI
```
2. 가상환경(poetry) 생성 및 활성화
```
poetry install
poetry shell
```
3. 프로젝트 실행
```
uvicorn main:app --reload --host 0.0.0.0 --port 8001
```
