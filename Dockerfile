FROM python:3.11-slim

WORKDIR /app

# 필수 패키지 설치 및 apt 캐시 정리
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# pip 최신 버전으로 업그레이드
RUN python3 -m pip install --upgrade pip

# requirements 설치 (캐시 비활성화)
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 코드 복사
COPY . /app

EXPOSE 8000 8081 8080

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]