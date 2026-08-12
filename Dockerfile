# Production Dockerfile for Microinvest Bank Statement OCR & Delta Pro Automation Service
FROM python:3.11-slim

# Install Tesseract OCR, Bulgarian language packs, and system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-bul \
    tesseract-ocr-eng \
    poppler-utils \
    curl \
    git \
    && rm -rf /var/lib/apt-get/lists/*

WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt || \
    pip install --no-cache-dir pymupdf pillow pytesseract vncdotool requests

# Copy source code and scripts
COPY src/ ./src/
COPY scripts/ ./scripts/
COPY data/ ./data/

EXPOSE 8090

# Default environment variables
ENV PYTHONUNBUFFERED=1
ENV INFISICAL_URL=http://100.83.83.8:8080
ENV SUPABASE_URL=http://100.83.83.8:8002
ENV N8N_WEBHOOK_URL=http://100.83.83.8:5679/webhook/microinvest-ocr

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:8090/ || exit 1

CMD ["python3", "scripts/microinvest_n8n_service.py"]
