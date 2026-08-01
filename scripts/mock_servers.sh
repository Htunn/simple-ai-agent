#!/bin/bash
# Quick start script for mock server development

set -e

echo "🚀 AIOps Orchestrator - Mock Server Quick Start"
echo "================================================"
echo ""

# Function to check if Docker is running
check_docker() {
    if ! docker info > /dev/null 2>&1; then
        echo "❌ Docker is not running. Please start Docker and try again."
        exit 1
    fi
    echo "✅ Docker is running"
}

# Function to check if port is available
check_port() {
    local port=$1
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1 ; then
        echo "⚠️  Port $port is already in use"
        return 1
    fi
    return 0
}

# Parse command line arguments
ACTION=${1:-"start"}

case "$ACTION" in
    start)
        echo "📦 Starting mock servers..."
        check_docker
        
        # Check critical ports
        echo ""
        echo "🔍 Checking ports..."
        check_port 5004 || echo "   (Kubernetes mock may fail to start)"
        
        echo ""
        echo "🐳 Starting Docker Compose..."
        cd dev
        docker compose -f docker-compose.mock.yml up -d
        
        echo ""
        echo "⏳ Waiting for services to be healthy..."
        sleep 5
        
        echo ""
        echo "✅ Mock servers started!"
        echo ""
        echo "📊 Service Status:"
        docker compose -f docker-compose.mock.yml ps
        
        echo ""
        echo "🔗 Available endpoints:"
        echo "   Nutanix Mock:    http://localhost:5001"
        echo "   VMware Mock:     http://localhost:5002"
        echo "   OpenShift Mock:  http://localhost:5003"
        echo "   Kubernetes Mock: http://localhost:5004"
        echo "   Custom API Mock: http://localhost:5005"
        echo "   A2A Agent Mock:  http://localhost:5006"
        echo ""
        echo "   Health Checks:"
        echo "   curl http://localhost:5001/health"
        echo "   curl http://localhost:5002/health"
        echo "   curl http://localhost:5003/health"
        echo "   curl http://localhost:5004/health"
        echo "   curl http://localhost:5005/health"
        echo "   curl http://localhost:5006/health"
        echo ""
        echo "📚 View logs:"
        echo "   docker compose -f dev/docker-compose.mock.yml logs -f"
        ;;
        
    stop)
        echo "🛑 Stopping mock servers..."
        cd dev
        docker compose -f docker-compose.mock.yml down
        echo "✅ Mock servers stopped"
        ;;
        
    restart)
        echo "🔄 Restarting mock servers..."
        cd dev
        docker compose -f docker-compose.mock.yml restart
        echo "✅ Mock servers restarted"
        ;;
        
    logs)
        echo "📋 Viewing logs (Ctrl+C to exit)..."
        cd dev
        docker compose -f docker-compose.mock.yml logs -f
        ;;
        
    test)
        echo "🧪 Running E2E tests against mock servers..."
        
        # Check if mock servers are running
        if ! curl -s http://localhost:5004/health > /dev/null; then
            echo "❌ Mock servers are not running. Start them first with: $0 start"
            exit 1
        fi
        
        echo "✅ Mock servers are running"
        echo ""
        echo "Running tests..."
        pytest tests/e2e/test_kubernetes_mock.py \
               tests/e2e/test_nutanix_mock.py \
               tests/e2e/test_vmware_mock.py \
               tests/e2e/test_openshift_mock.py \
               tests/e2e/test_custom_api_mock.py \
               tests/e2e/test_a2a_agent_mock.py -v
        ;;
        
    dev)
        SERVICE=${2:-"kubernetes"}
        PORT=${3:-"5004"}
        
        echo "🔧 Starting $SERVICE mock in development mode..."
        echo "   (Hot reload enabled)"
        echo ""
        
        cd dev/mock_servers
        
        # Check if venv exists
        if [ ! -d ".venv" ]; then
            echo "📦 Creating virtual environment..."
            python3.12 -m venv .venv
            source .venv/bin/activate
            pip install -r requirements.txt
        else
            source .venv/bin/activate
        fi
        
        cd $SERVICE
        echo "🚀 Starting $SERVICE mock on port $PORT..."
        echo "   Press Ctrl+C to stop"
        echo ""
        uvicorn main:app --reload --port $PORT
        ;;
        
    status)
        echo "📊 Mock Server Status:"
        echo ""
        cd dev
        docker compose -f docker-compose.mock.yml ps
        
        echo ""
        echo "🔍 Health Checks:"
        
        # Check Nutanix mock
        if curl -s http://localhost:5001/health > /dev/null; then
            echo "   ✅ Nutanix Mock (5001): Healthy"
        else
            echo "   ❌ Nutanix Mock (5001): Not responding"
        fi
        
        # Check VMware mock
        if curl -s http://localhost:5002/health > /dev/null; then
            echo "   ✅ VMware Mock (5002): Healthy"
        else
            echo "   ❌ VMware Mock (5002): Not responding"
        fi
        
        # Check OpenShift mock
        if curl -s http://localhost:5003/health > /dev/null; then
            echo "   ✅ OpenShift Mock (5003): Healthy"
        else
            echo "   ❌ OpenShift Mock (5003): Not responding"
        fi
        
        # Check Kubernetes mock
        if curl -s http://localhost:5004/health > /dev/null; then
            echo "   ✅ Kubernetes Mock (5004): Healthy"
        else
            echo "   ❌ Kubernetes Mock (5004): Not responding"
        fi
        
        # Check Custom API mock
        if curl -s http://localhost:5005/health > /dev/null; then
            echo "   ✅ Custom API Mock (5005): Healthy"
        else
            echo "   ❌ Custom API Mock (5005): Not responding"
        fi
        
        # Check A2A Agent mock
        if curl -s http://localhost:5006/health > /dev/null; then
            echo "   ✅ A2A Agent Mock (5006): Healthy"
        else
            echo "   ❌ A2A Agent Mock (5006): Not responding"
        fi
        ;;
        
    build)
        echo "🏗️  Building mock server images..."
        cd dev
        docker compose -f docker-compose.mock.yml build
        echo "✅ Build complete"
        ;;
        
    clean)
        echo "🧹 Cleaning up mock servers..."
        cd dev
        docker compose -f docker-compose.mock.yml down -v
        docker compose -f docker-compose.mock.yml rm -f
        echo "✅ Cleanup complete"
        ;;
        
    *)
        echo "Usage: $0 {start|stop|restart|logs|test|dev|status|build|clean}"
        echo ""
        echo "Commands:"
        echo "  start    - Start all mock servers (Docker Compose)"
        echo "  stop     - Stop all mock servers"
        echo "  restart  - Restart all mock servers"
        echo "  logs     - View logs from all mock servers"
        echo "  test     - Run E2E tests against mock servers"
        echo "  dev      - Start a mock server in development mode (hot reload)"
        echo "             Usage: $0 dev [service] [port]"
        echo "             Example: $0 dev kubernetes 5004"
        echo "  status   - Show status of all mock servers"
        echo "  build    - Rebuild Docker images"
        echo "  clean    - Remove all containers and volumes"
        echo ""
        echo "Examples:"
        echo "  $0 start              # Start all mocks"
        echo "  $0 dev kubernetes     # Start Kubernetes mock locally"
        echo "  $0 logs               # View logs"
        echo "  $0 test               # Run tests"
        exit 1
        ;;
esac
