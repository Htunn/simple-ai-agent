#!/bin/bash
# Start the AI Agent server locally with uvicorn

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo -e "${GREEN}🚀 Starting AIOps Orchestrator Server${NC}"
echo "=================================================="

# Change to project root
cd "$PROJECT_ROOT"

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo -e "${RED}❌ Virtual environment not found${NC}"
    echo "Please create it first: python3 -m venv .venv"
    exit 1
fi

# Activate virtual environment
echo -e "${YELLOW}📦 Activating virtual environment...${NC}"
source .venv/bin/activate

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}⚠️  .env file not found${NC}"
    echo "Please create .env from .env.example"
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Check if port 8000 is already in use
if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo -e "${YELLOW}⚠️  Port 8000 is already in use${NC}"
    read -p "Kill existing process and restart? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${YELLOW}🔄 Killing existing process...${NC}"
        lsof -ti:8000 | xargs kill -9 2>/dev/null || true
        sleep 2
    else
        exit 1
    fi
fi

# Parse command line arguments
HOST="${1:-0.0.0.0}"
PORT="${2:-8000}"
RELOAD="${3:---reload}"

echo -e "${GREEN}📡 Server configuration:${NC}"
echo "   Host: $HOST"
echo "   Port: $PORT"
echo "   Reload: $RELOAD"
echo ""

echo -e "${GREEN}✅ Starting uvicorn server...${NC}"
echo "=================================================="
echo ""
echo -e "${YELLOW}💡 Note: Database will be initialized automatically on startup${NC}"
echo ""

# Start server
python -m uvicorn src.main:app --host "$HOST" --port "$PORT" $RELOAD

# Cleanup on exit
trap "echo -e '\n${YELLOW}👋 Shutting down server...${NC}'" EXIT
