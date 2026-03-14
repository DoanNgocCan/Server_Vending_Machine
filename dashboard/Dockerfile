FROM python:3.11-slim

WORKDIR /app

# Cài dependencies hệ thống
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements trước
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Tạo thư mục Streamlit config
RUN mkdir -p /root/.streamlit && \
    echo "[server]\n\
headless = true\n\
port = 8501\n\
enableXsrfProtection = false\n\
enableCORS = false\n\
\n\
[client]\n\
showErrorDetails = true\n\
\n\
[logger]\n\
level = 'debug'" > /root/.streamlit/config.toml

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

CMD ["streamlit", "run", \
     "main.py", \
     "--server.port=8501", \
     "--server.address=0.0.0.0", \
     "--server.headless=true", \
     "--logger.level=debug"]