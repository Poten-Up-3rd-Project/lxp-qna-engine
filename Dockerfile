FROM python:3.11-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
RUN apt-get update && apt-get install -y build-essential && rm -rf /var/lib/apt/lists/*

# Install runtime deps
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Install our package so console_script entrypoint is available
COPY pyproject.toml ./
COPY src ./src
RUN pip install --no-cache-dir .

CMD ["lxp-qna-engine"]
