# Standalone Dockerfile for ActionsGuard
# For use outside of GitHub Actions

FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Download Scorecard binary
RUN curl -L -o /usr/local/bin/scorecard https://github.com/ossf/scorecard/releases/latest/download/scorecard_linux_amd64 \
    && chmod +x /usr/local/bin/scorecard

# Set working directory
WORKDIR /app

# Copy application files
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY actionsguard ./actionsguard
COPY setup.py pyproject.toml README.md ./

# Install ActionsGuard
RUN pip install --no-cache-dir -e .

# Create reports directory
RUN mkdir /reports

WORKDIR /workspace

ENTRYPOINT ["actionsguard"]
CMD ["--help"]
