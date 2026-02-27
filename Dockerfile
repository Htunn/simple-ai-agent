# Stage 1: Builder
FROM python:3.12-slim-bookworm AS builder

# Set build arguments for versioning and metadata
ARG BUILD_DATE
ARG VCS_REF
ARG VERSION=1.0.0

LABEL org.opencontainers.image.created="${BUILD_DATE}" \
      org.opencontainers.image.authors="Simple AI Agent Team" \
      org.opencontainers.image.url="https://github.com/yourorg/simple-ai-agent" \
      org.opencontainers.image.source="https://github.com/yourorg/simple-ai-agent" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.revision="${VCS_REF}" \
      org.opencontainers.image.title="Simple AI Agent" \
      org.opencontainers.image.description="Production-ready multi-channel AI agent with MCP integration"

# Install build dependencies
# kubectl required for Kubernetes MCP server
RUN apt-get update && apt-get install -y --no-install-recommends \
      gcc \
      g++ \
      libpq-dev \
      curl \
      apt-transport-https \
      ca-certificates \
      gnupg \
    && curl -fsSL https://pkgs.k8s.io/core:/stable:/v1.28/deb/Release.key | gpg --dearmor -o /etc/apt/keyrings/kubernetes-apt-keyring.gpg \
    && echo 'deb [signed-by=/etc/apt/keyrings/kubernetes-apt-keyring.gpg] https://pkgs.k8s.io/core:/stable:/v1.28/deb/ /' | tee /etc/apt/sources.list.d/kubernetes.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends kubectl \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# Stage 2: Runtime
FROM python:3.12-slim-bookworm

# Install runtime dependencies
# kubectl, curl for health checks, ca-certificates for HTTPS
RUN apt-get update && apt-get install -y --no-install-recommends \
      libpq5 \
      curl \
      ca-certificates \
      apt-transport-https \
      gnupg \
    && curl -fsSL https://pkgs.k8s.io/core:/stable:/v1.28/deb/Release.key | gpg --dearmor -o /etc/apt/keyrings/kubernetes-apt-keyring.gpg \
    && echo 'deb [signed-by=/etc/apt/keyrings/kubernetes-apt-keyring.gpg] https://pkgs.k8s.io/core:/stable:/v1.28/deb/ /' | tee /etc/apt/sources.list.d/kubernetes.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends kubectl \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Set working directory
WORKDIR /app

# Create non-root user with specific UID/GID for consistency
RUN groupadd -g 1000 appuser && \
    useradd -m -u 1000 -g appuser appuser && \
    chown -R appuser:appuser /app && \
    mkdir -p /app/logs /app/.kube && \
    chown -R appuser:appuser /app/logs /app/.kube

# Copy application code
COPY --chown=appuser:appuser src/ ./src/
COPY --chown=appuser:appuser scripts/ ./scripts/
COPY --chown=appuser:appuser alembic.ini .
COPY --chown=appuser:appuser .mcp-config.json .

# Switch to non-root user
USER appuser

# Set environment variables
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    # MCP configuration
    MCP_CONFIG_PATH=/app/.mcp-config.json \
    # Production settings
    ENVIRONMENT=production \
    LOG_LEVEL=INFO \
    # Optimize Python
    PYTHONOPTIMIZE=1

# Expose port
EXPOSE 8000

# Health check with proper intervals for production
# Increased start-period to allow for initialization
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Use exec form for proper signal handling
CMD ["python", "-m", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]

