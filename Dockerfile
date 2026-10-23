FROM python:3.11-slim

# Install system dependencies including curl for healthchecks
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files, seeds, reports, logs, tests
COPY app/ ./app/
COPY seeds/ ./seeds/
COPY reports/ ./reports/
COPY logs/ ./logs/
COPY demo/ ./demo/
COPY tests/ ./tests/
COPY .env.example README.md ./

# Environment configuration
ENV PYTHONPATH=/workspace
ENV PYTHONUNBUFFERED=1
ENV API_PORT=8080

EXPOSE 8080

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
