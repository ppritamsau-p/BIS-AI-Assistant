FROM python:3.12-slim

# Poppler and Tesseract enable OCR for scanned BIS PDFs. Without them ingestion
# still works, but scanned pages are reported as unindexed rather than skipped
# silently.
RUN apt-get update && apt-get install -y --no-install-recommends \
        poppler-utils tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt \
    && pip install --no-cache-dir pytesseract pdf2image

COPY backend/ backend/
COPY data/ data/
COPY scripts/ scripts/

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s \
    CMD python -c "import urllib.request;urllib.request.urlopen('http://127.0.0.1:8000/api/health')"

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
