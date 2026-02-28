#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# start_production.sh  –  Bootstrap data directories and start the full
#                          production docker-compose stack (app + monitoring).
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

echo -e "${GREEN}🚀  Simple AI Agent – Production Start${NC}"
echo "======================================================"

# ── 1. Validate .env ───────────────────────────────────────────────────────
if [[ ! -f .env ]]; then
    echo -e "${YELLOW}⚠️   .env not found – copying from .env.production.example${NC}"
    cp .env.production.example .env
    echo -e "${RED}❗  Edit .env and fill in secrets before re-running.${NC}"
    exit 1
fi

# Source .env to pick up DATA_DIR (default ./data)
# We only pick up specific shell variables we need in this script.
# We do NOT export the full .env into the shell — docker compose reads .env
# natively, and exporting localhost DATABASE_URL etc. would break in-container URLs.
_env_val() { grep -E "^${1}=" .env 2>/dev/null | head -1 | cut -d= -f2- | tr -d '"' | tr -d "'" || true; }
DATA_DIR="$(_env_val DATA_DIR)";               DATA_DIR="${DATA_DIR:-./data}"
POSTGRES_USER="$(_env_val POSTGRES_USER)";     POSTGRES_USER="${POSTGRES_USER:-aiagent}"
POSTGRES_PASSWORD="$(_env_val POSTGRES_PASSWORD)"; POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-aiagent_password}"
POSTGRES_DB="$(_env_val POSTGRES_DB)";         POSTGRES_DB="${POSTGRES_DB:-aiagent}"
APP_PORT="$(_env_val APP_PORT)";               APP_PORT="${APP_PORT:-8000}"
PROMETHEUS_PORT="$(_env_val PROMETHEUS_PORT)"; PROMETHEUS_PORT="${PROMETHEUS_PORT:-9090}"
ALERTMANAGER_PORT="$(_env_val ALERTMANAGER_PORT)"; ALERTMANAGER_PORT="${ALERTMANAGER_PORT:-9093}"
GRAFANA_PORT="$(_env_val GRAFANA_PORT)";       GRAFANA_PORT="${GRAFANA_PORT:-3000}"
GRAFANA_ADMIN_USER="$(_env_val GRAFANA_ADMIN_USER)"; GRAFANA_ADMIN_USER="${GRAFANA_ADMIN_USER:-admin}"
VERSION="$(_env_val VERSION)";                 VERSION="${VERSION:-1.0.0}"

# ── 2. Create required bind-mount directories ──────────────────────────────
echo -e "${YELLOW}📁  Creating data directories under ${DATA_DIR}…${NC}"
for dir in postgres redis prometheus alertmanager grafana kube; do
    mkdir -p "${DATA_DIR}/${dir}"
done
# Fix ownership for Prometheus/Alertmanager (run as UID 65534 / nobody)
if command -v chown &>/dev/null; then
    chown -R 65534:65534 "${DATA_DIR}/prometheus" "${DATA_DIR}/alertmanager" 2>/dev/null || true
fi

# ── 2b. Generate container-compatible kubeconfig ──────────────────────────
# The SSH-tunnel kubeconfig uses 127.0.0.1 for both the API server and the
# SOCKS proxy. Inside Docker, 127.0.0.1 is the container — not the host.
# Replace with host.docker.internal so the container can route through the
# host's SSH tunnel and SOCKS proxy.
KUBECONFIG_SRC="${KUBECONFIG:-${HOME}/.kube/config}"
KUBECONFIG_DOCKER="${DATA_DIR}/kube/config"
if [[ -f "${KUBECONFIG_SRC}" ]]; then
    # Only replace 127.0.0.1 on proxy-url lines, NOT on server lines.
    # The SOCKS proxy must be reachable at host.docker.internal:1080 (host loopback).
    # The server address (e.g. 127.0.0.1:6443) must stay as-is because the SOCKS
    # proxy forwards it to the remote K3s node via the SSH tunnel.
    sed '/proxy/s|127\.0\.0\.1|host.docker.internal|g' "${KUBECONFIG_SRC}" > "${KUBECONFIG_DOCKER}"
    chmod 600 "${KUBECONFIG_DOCKER}"
    echo -e "${GREEN}✅  Kubeconfig patched for Docker (proxy → host.docker.internal) → ${KUBECONFIG_DOCKER}${NC}"
else
    # No kubeconfig available; create an empty placeholder so the volume mount doesn't fail
    echo '{}' > "${KUBECONFIG_DOCKER}"
    echo -e "${YELLOW}⚠️   No kubeconfig found at ${KUBECONFIG_SRC}; K8s features will be disabled.${NC}"
fi

echo -e "${GREEN}✅  Data directories ready.${NC}"

# ── 3. Pull latest third-party images (skip locally-built services) ────────
echo -e "${YELLOW}⬇️   Pulling third-party Docker images…${NC}"
docker compose pull --ignore-buildable --quiet

# ── 3b. Tear down any stale containers from a previous run ─────────────────
# (keeps volumes intact so persistent data is not lost)
echo -e "${YELLOW}🧹  Stopping existing containers (data preserved)…${NC}"
docker compose down --remove-orphans 2>/dev/null || true

# ── 4. Build application image ────────────────────────────────────────────
echo -e "${YELLOW}🔨  Building application image…${NC}"
docker compose build \
    --build-arg BUILD_DATE="$(date -u +"%Y-%m-%dT%H:%M:%SZ")" \
    --build-arg VCS_REF="$(git rev-parse --short HEAD 2>/dev/null || echo dev)" \
    --build-arg VERSION="${VERSION:-1.0.0}"

# ── 5. Run database migrations ────────────────────────────────────────────
echo -e "${YELLOW}🗄️   Starting postgres for migrations…${NC}"
docker compose up -d --force-recreate postgres
echo "Waiting for postgres to be healthy…"
deadline=$(( SECONDS + 60 ))
until docker compose exec -T postgres pg_isready -U "${POSTGRES_USER:-aiagent}" &>/dev/null; do
    if (( SECONDS >= deadline )); then
        echo -e "${RED}❌  Timed out waiting for PostgreSQL.${NC}"
        exit 1
    fi
    sleep 2
done
echo -e "${GREEN}✅  PostgreSQL is ready.${NC}"

echo -e "${YELLOW}🔄  Running Alembic migrations…${NC}"
# Override DATABASE_URL so the in-container alembic uses the Docker-network
# 'postgres' hostname instead of whatever is set in the local .env file.
docker compose run --rm \
    -e DATABASE_URL="postgresql+asyncpg://${POSTGRES_USER:-aiagent}:${POSTGRES_PASSWORD:-aiagent_password}@postgres:5432/${POSTGRES_DB:-aiagent}" \
    app alembic upgrade head

# ── 6. Start the full stack ───────────────────────────────────────────────
echo -e "${YELLOW}▶️   Starting all services…${NC}"
docker compose up -d --force-recreate

# ── 7. Health check ───────────────────────────────────────────────────────
echo "Waiting for application health check…"
deadline=$(( SECONDS + 90 ))
until curl -sf "http://localhost:${APP_PORT:-8000}/health" &>/dev/null; do
    if (( SECONDS >= deadline )); then
        echo -e "${RED}❌  Timed out waiting for app health check.${NC}"
        docker compose logs --tail=30 app
        exit 1
    fi
    sleep 3
done
echo -e "${GREEN}✅  Application is healthy.${NC}"

echo ""
echo -e "${GREEN}======================================================"
echo -e "🎉  Stack is up!"
echo -e "  App:          http://localhost:${APP_PORT:-8000}"
echo -e "  Prometheus:   http://localhost:${PROMETHEUS_PORT:-9090}"
echo -e "  Alertmanager: http://localhost:${ALERTMANAGER_PORT:-9093}"
echo -e "  Grafana:      http://localhost:${GRAFANA_PORT:-3000}"
echo -e "  (Grafana login: ${GRAFANA_ADMIN_USER:-admin} / <GRAFANA_ADMIN_PASSWORD>)"
echo -e "======================================================${NC}"
