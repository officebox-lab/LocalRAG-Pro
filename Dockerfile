# LocalRAG_Pro - API サーバー用 Dockerfile
# ビルド: docker build -t localrag-pro .
# 起動:   docker-compose up

FROM python:3.11-slim

# Tesseract OCR（日本語 + 英語）
RUN apt-get update && apt-get install -y --no-install-recommends \
        tesseract-ocr \
        tesseract-ocr-jpn \
        tesseract-ocr-eng \
        poppler-utils \
        libgl1 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /localrag

# 依存パッケージを先にインストール（レイヤーキャッシュ活用）
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# アプリコードをコピー
COPY app/ ./app/

# Windows cp932 問題を回避するため UTF-8 を強制
ENV PYTHONIOENCODING=utf-8
ENV PYTHONUNBUFFERED=1

EXPOSE 5050

CMD ["python", "app/api_server.py"]
