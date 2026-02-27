#!/bin/bash
# Stop the AI Agent server

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}🛑 Stopping Simple AI Agent Server${NC}"
echo "=================================================="

# Find and kill uvicorn processes
if pgrep -f "uvicorn src.main:app" > /dev/null; then
    echo -e "${YELLOW}Stopping uvicorn processes...${NC}"
    pkill -f "uvicorn src.main:app" || true
    sleep 1
    
    # Force kill if still running
    if pgrep -f "uvicorn src.main:app" > /dev/null; then
        echo -e "${YELLOW}Force stopping...${NC}"
        pkill -9 -f "uvicorn src.main:app" || true
    fi
    
    echo -e "${GREEN}✅ Server stopped${NC}"
else
    echo -e "${RED}❌ No server processes found${NC}"
fi

# Also check port 8000
if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo -e "${YELLOW}Killing process on port 8000...${NC}"
    lsof -ti:8000 | xargs kill -9 2>/dev/null || true
    echo -e "${GREEN}✅ Port 8000 freed${NC}"
fi
