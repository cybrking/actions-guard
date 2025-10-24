# Standalone Dockerfile for ActionsGuard
# For use outside of GitHub Actions

FROM golang:1.21-alpine AS scorecard-builder
RUN apk add --no-cache git
RUN go install github.com/ossf/scorecard/v5/cmd/scorecard@latest

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
COPY setup.py pyproject.toml README.md ./

# Install ActionsGuard
RUN pip install --no-cache-dir -e .

# Create reports directory
RUN mkdir /reports

WORKDIR /workspace

ENTRYPOINT ["actionsguard"]
CMD ["--help"]
