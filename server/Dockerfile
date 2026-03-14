FROM python:3.11-slim

WORKDIR /app

# Cài dependencies hệ thống
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy và cài Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Tạo thư mục cho ảnh và logs
RUN mkdir -p /app/static/images && chmod 755 /app/static/images
RUN mkdir -p /app/logs && chmod 755 /app/logs

# Set environment variables
ENV FLASK_APP=app.py
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:5000/ || exit 1

# ĐÃ THÊM CỜ --preload VÀO ĐÂY
CMD ["gunicorn", \
     "--preload", \
     "--bind", "0.0.0.0:5000", \
     "--workers", "4", \
     "--worker-class", "sync", \
     "--timeout", "120", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "app:app"]