# Multi-stage build for ActionsGuard GitHub Action

# Stage 1: Build Scorecard
FROM golang:1.21-alpine AS scorecard-builder
RUN apk add --no-cache git
RUN go install github.com/ossf/scorecard/v5/cmd/scorecard@latest

# Stage 2: Build ActionsGuard
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy Scorecard from builder
COPY --from=scorecard-builder /go/bin/scorecard /usr/local/bin/scorecard

# Set working directory
WORKDIR /app

# Copy application files
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY actionsguard ./actionsguard
COPY setup.py .
COPY pyproject.toml .
COPY README.md .

# Install ActionsGuard
RUN pip install --no-cache-dir -e .

# Copy entrypoint script
COPY .github-action/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Set GitHub workspace as working directory
WORKDIR /github/workspace

ENTRYPOINT ["/entrypoint.sh"]
