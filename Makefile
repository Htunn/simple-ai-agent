# Makefile for AIOps Orchestrator Testing
# Comprehensive test suite with mock servers and coverage reporting
#
# Usage:
#   make help          - Show available targets
#   make test          - Run all tests (unit + integration + e2e)
#   make test-unit     - Run unit tests only
#   make test-e2e      - Run E2E tests with mock servers
#   make test-coverage - Run all tests with coverage report
#   make clean         - Clean test artifacts

.PHONY: help test test-unit test-integration test-e2e test-aiops test-coverage \
        start-mock-servers stop-mock-servers check-mock-servers \
        test-quick test-full test-watch clean clean-all \
        lint format validate install-dev

# ════════════════════════════════════════════════════════════════════════════
# Configuration
# ════════════════════════════════════════════════════════════════════════════

# Virtual environment
VENV := .venv
VENV_BIN := $(VENV)/bin
PYTHON := $(VENV_BIN)/python3
PYTEST := $(VENV_BIN)/pytest
PIP := $(VENV_BIN)/pip3

# Pytest configuration
PYTEST_ARGS := -v --tb=short
COVERAGE_ARGS := --cov=src --cov-report=html --cov-report=term --cov-report=xml

# Mock server ports
MOCK_SERVER_PORT := 8000
OLLAMA_MOCK_PORT := 11434

# Platform mock server ports (for E2E tests)
PLATFORM_MOCK_COMPOSE := dev/docker-compose.mock.yml
PLATFORM_MOCK_PORTS := 5001 5002 5003 5004 5005 5006

# Test directories
UNIT_TESTS := tests/unit
E2E_TESTS := tests/e2e
INTEGRATION_TESTS := tests/test_vllm_ollama_e2e.py tests/test_vllm_ollama_e2e_real.py
AIOPS_E2E := tests/test_aiops_e2e.py

# Mock server script
MOCK_SERVERS := tests/mock_llm_servers.py

# Coverage threshold
COVERAGE_MIN := 70

# ════════════════════════════════════════════════════════════════════════════
# Help Target
# ════════════════════════════════════════════════════════════════════════════

help:
	@echo "════════════════════════════════════════════════════════════════════"
	@echo "  AIOps Orchestrator - Test Suite"
	@echo "════════════════════════════════════════════════════════════════════"
	@echo ""
	@echo "🧪 Testing Targets:"
	@echo "  make test              - Run ALL tests (unit + integration + e2e)"
	@echo "  make test-quick        - Run unit tests only (fast feedback)"
	@echo "  make test-unit         - Run unit tests with detailed output"
	@echo "  make test-integration  - Run integration tests (LLM clients)"
	@echo "  make test-e2e          - Run E2E tests (platforms, A2A, K8s)"
	@echo "  make test-aiops        - Run AIOps E2E tests (watchloop, RCA, approvals)"
	@echo "  make test-coverage     - Run all tests with coverage report"
	@echo "  make test-watch        - Run tests in watch mode (auto-rerun on changes)"
	@echo ""
	@echo "🔧 Mock Server Management:"
	@echo "  make start-mock-servers  - Start vLLM and Ollama mock servers"
	@echo "  make stop-mock-servers   - Stop all mock servers"
	@echo "  make check-mock-servers  - Verify mock servers are running"
	@echo "  make start-platform-mocks - Start platform mocks (for E2E tests)"
	@echo "  make stop-platform-mocks  - Stop platform mock servers"
	@echo "  make check-platform-mocks - Verify platform mocks are running"
	@echo ""
	@echo "📊 Code Quality:"
	@echo "  make lint              - Run linting (ruff)"
	@echo "  make format            - Auto-format code (black + ruff)"
	@echo "  make validate          - Run validation script (36 checks)"
	@echo ""
	@echo "🛠️  Development:"
	@echo "  make venv              - Create virtual environment (.venv)"
	@echo "  make setup-dev         - Setup venv + install all dependencies"
	@echo "  make install-dev       - Install development dependencies (venv must exist)"
	@echo "  make clean             - Clean test artifacts (cache, coverage)"
	@echo "  make clean-all         - Deep clean (cache, coverage, .pyc, __pycache__)"
	@echo ""
	@echo "Examples:"
	@echo "  make setup-dev                     # First time setup"
	@echo "  make test-quick                    # Fast unit tests"
	@echo "  make test-coverage                 # Full test suite with coverage"
	@echo "  make start-mock-servers test-e2e   # E2E with mock servers"
	@echo ""

# ════════════════════════════════════════════════════════════════════════════
# Virtual Environment Setup
# ════════════════════════════════════════════════════════════════════════════

.PHONY: venv
venv: $(VENV)/bin/activate ## Create virtual environment

$(VENV)/bin/activate:
	@echo "🔨 Creating virtual environment..."
	@python3.12 -m venv $(VENV)
	@echo "✅ Virtual environment created at $(VENV)"
	@echo "   Activate with: source $(VENV)/bin/activate"

.PHONY: setup-dev
setup-dev: venv ## Complete development setup (venv + dependencies)
	@echo "📦 Installing all dependencies (production + testing)..."
	@bash -c "source $(VENV)/bin/activate && pip3 install --upgrade pip"
	@bash -c "source $(VENV)/bin/activate && pip3 install -r requirements.txt"
	@if [ -f "requirements-dev.txt" ]; then \
		bash -c "source $(VENV)/bin/activate && pip3 install -r requirements-dev.txt"; \
	fi
	@echo ""
	@echo "✅ Development environment ready!"
	@echo "   Python:  $(PYTHON)"
	@echo "   Pytest:  $(PYTEST)"
	@echo ""
	@echo "Next steps:"
	@echo "  make test-quick     # Run quick tests"
	@echo "  make test           # Run full test suite"

# ════════════════════════════════════════════════════════════════════════════
# Quick Test Targets
# ════════════════════════════════════════════════════════════════════════════

# Check if venv exists before running tests
.PHONY: check-venv
check-venv:
	@if [ ! -f "$(VENV)/bin/activate" ]; then \
		echo "❌ Virtual environment not found!"; \
		echo "   Run: make setup-dev"; \
		exit 1; \
	fi

.PHONY: test-quick
test-quick: check-venv ## Fast unit tests for quick feedback
	@echo "🚀 Running quick unit tests..."
	@$(PYTEST) $(UNIT_TESTS) $(PYTEST_ARGS) -x --ff

.PHONY: test
test: check-venv ## Run all tests (unit + integration + e2e)
	@echo "🧪 Running complete test suite..."
	@$(MAKE) test-unit
	@$(MAKE) test-integration
	@$(MAKE) test-e2e
	@$(MAKE) test-aiops
	@echo ""
	@echo "✅ All tests completed successfully!"

# ════════════════════════════════════════════════════════════════════════════
# Unit Tests
# ════════════════════════════════════════════════════════════════════════════

.PHONY: test-unit
test-unit: check-venv ## Run all unit tests
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "  Unit Tests"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@env -u http_proxy -u https_proxy -u HTTP_PROXY -u HTTPS_PROXY -u ALL_PROXY -u all_proxy \
	$(PYTEST) $(UNIT_TESTS) $(PYTEST_ARGS)
	@echo ""

# ════════════════════════════════════════════════════════════════════════════
# Integration Tests
# ════════════════════════════════════════════════════════════════════════════

.PHONY: test-integration
test-integration: check-venv check-mock-servers ## Run integration tests (requires mock servers)
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "  Integration Tests (LLM Clients)"
	@env -u http_proxy -u https_proxy -u HTTP_PROXY -u HTTPS_PROXY -u ALL_PROXY -u all_proxy \
	echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@$(PYTEST) $(INTEGRATION_TESTS) $(PYTEST_ARGS) -s
	@echo ""

# ════════════════════════════════════════════════════════════════════════════
# E2E Tests
# ════════════════════════════════════════════════════════════════════════════

.PHONY: test-e2e
test-e2e: check-venv check-platform-mocks ## Run E2E tests (platforms, A2A, K8s) - requires platform mocks
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "  E2E Tests (Platforms & A2A)"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@if [ -d "$(E2E_TESTS)" ]; then \
		env -u http_proxy -u https_proxy -u HTTP_PROXY -u HTTPS_PROXY -u ALL_PROXY -u all_proxy \
		$(PYTEST) $(E2E_TESTS) $(PYTEST_ARGS); \
	else \
		echo "⚠️  No E2E tests directory found at $(E2E_TESTS)"; \
	fi
	@echo ""

# ════════════════════════════════════════════════════════════════════════════
# AIOps E2E Tests
# ════════════════════════════════════════════════════════════════════════════

.PHONY: test-aiops
test-aiops: check-venv ## Run AIOps E2E tests (watchloop, RCA engine, approvals)
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "  AIOps E2E Tests"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@if [ -f "$(AIOPS_E2E)" ]; then \
		$(PYTHON) $(AIOPS_E2E); \
	else \
		echo "⚠️  AIOps E2E test not found at $(AIOPS_E2E)"; \
	fi
	@echo ""

# ════════════════════════════════════════════════════════════════════════════
# Coverage Testing
# ════════════════════════════════════════════════════════════════════════════

.PHONY: test-coverage
test-coverage: check-venv ## Run all tests with coverage report
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@env -u http_proxy -u https_proxy -u HTTP_PROXY -u HTTPS_PROXY -u ALL_PROXY -u all_proxy \
	echo "  Coverage Testing"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@$(PYTEST) $(UNIT_TESTS) $(E2E_TESTS) $(PYTEST_ARGS) $(COVERAGE_ARGS) \
		--cov-fail-under=$(COVERAGE_MIN)
	@echo ""
	@echo "📊 Coverage report generated:"
	@echo "   - HTML: htmlcov/index.html"
	@echo "   - XML:  coverage.xml"
	@echo "   - Terminal output above"
	@echo ""

# ════════════════════════════════════════════════════════════════════════════
# Mock Server Management
# ════════════════════════════════════════════════════════════════════════════

.PHONY: start-mock-servers
start-mock-servers: check-venv ## Start vLLM and Ollama mock servers in background
	@echo "🚀 Starting mock LLM servers..."
	@if pgrep -f "mock_llm_servers.py" > /dev/null; then \
		echo "⚠️  Mock servers already running (PID: $$(pgrep -f mock_llm_servers.py))"; \
	else \
		$(PYTHON) $(MOCK_SERVERS) > mock_servers.log 2>&1 & \
		echo $$! > .mock_servers.pid; \
		sleep 2; \
		if $(MAKE) check-mock-servers; then \
			echo "✅ Mock servers started successfully (PID: $$(cat .mock_servers.pid))"; \
			echo "   - vLLM mock:   http://localhost:$(MOCK_SERVER_PORT)/v1"; \
			echo "   - Ollama mock: http://localhost:$(OLLAMA_MOCK_PORT)/v1"; \
			echo "   - Logs:        tail -f mock_servers.log"; \
		else \
			echo "❌ Failed to start mock servers"; \
			cat mock_servers.log; \
			exit 1; \
		fi \
	fi

.PHONY: stop-mock-servers
stop-mock-servers: ## Stop all mock servers
	@echo "🛑 Stopping mock servers..."
	@if [ -f .mock_servers.pid ]; then \
		PID=$$(cat .mock_servers.pid); \
		if ps -p $$PID > /dev/null 2>&1; then \
			kill $$PID; \
			echo "✅ Mock servers stopped (PID: $$PID)"; \
		else \
			echo "⚠️  Process $$PID not running"; \
		fi; \
		rm -f .mock_servers.pid; \
	else \
		pkill -f "mock_llm_servers.py" && echo "✅ Mock servers stopped" || echo "ℹ️  No mock servers running"; \
	fi

.PHONY: check-mock-servers
check-mock-servers: ## Verify mock servers are running
	@echo -n "🔍 Checking mock servers... "
	@if curl -s http://localhost:$(MOCK_SERVER_PORT)/health > /dev/null 2>&1 && \
	   curl -s http://localhost:$(OLLAMA_MOCK_PORT)/health > /dev/null 2>&1; then \
		echo "✅ Running"; \
		exit 0; \
	else \
		echo "❌ Not running"; \
		echo ""; \
		echo "Run: make start-mock-servers"; \
		exit 1; \
	fi

# ════════════════════════════════════════════════════════════════════════════
# Platform Mock Servers (E2E Testing)
# ════════════════════════════════════════════════════════════════════════════

.PHONY: start-platform-mocks
start-platform-mocks: ## Start platform mock servers (Nutanix, VMware, OpenShift, K8s, etc.)
	@echo "🚀 Starting platform mock servers..."
	@cd dev && docker compose -f docker-compose.mock.yml up -d
	@echo "⏳ Waiting for services to be healthy..."
	@sleep 5
	@if $(MAKE) check-platform-mocks; then \
		echo "✅ Platform mock servers started successfully"; \
		echo "   - Nutanix:     http://localhost:5001"; \
		echo "   - VMware:      http://localhost:5002"; \
		echo "   - OpenShift:   http://localhost:5003"; \
		echo "   - Kubernetes:  http://localhost:5004"; \
		echo "   - Custom API:  http://localhost:5005"; \
		echo "   - A2A Agent:   http://localhost:5006"; \
		echo ""; \
		echo "   Logs: cd dev && docker compose -f docker-compose.mock.yml logs -f"; \
	else \
		echo "❌ Failed to start platform mock servers"; \
		cd dev && docker compose -f docker-compose.mock.yml logs; \
		exit 1; \
	fi

.PHONY: stop-platform-mocks
stop-platform-mocks: ## Stop platform mock servers
	@echo "🛑 Stopping platform mock servers..."
	@cd dev && docker compose -f docker-compose.mock.yml down
	@echo "✅ Platform mock servers stopped"

.PHONY: check-platform-mocks
check-platform-mocks: ## Verify platform mock servers are running
	@echo -n "🔍 Checking platform mock servers... "
	@FAILED_PORTS=""; \
	for port in $(PLATFORM_MOCK_PORTS); do \
		env -u http_proxy -u https_proxy -u HTTP_PROXY -u HTTPS_PROXY -u ALL_PROXY -u all_proxy \
		curl -sf http://localhost:$$port/health > /dev/null || FAILED_PORTS="$$FAILED_PORTS $$port"; \
	done; \
	if [ -z "$$FAILED_PORTS" ]; then \
		echo "✅ All running"; \
	else \
		echo "❌ Not all running (failed:$$FAILED_PORTS)"; \
		echo ""; \
		echo "Run: make start-platform-mocks"; \
		exit 1; \
	fi

# ════════════════════════════════════════════════════════════════════════════
# Watch Mode
# ════════════════════════════════════════════════════════════════════════════

.PHONY: test-watch
test-watch: ## Run tests in watch mode (requires pytest-watch)
	@echo "👀 Running tests in watch mode (auto-rerun on file changes)..."
	@echo "   Press Ctrl+C to stop"
	@echo ""
	@if command -v ptw > /dev/null; then \
		ptw -- $(UNIT_TESTS) $(PYTEST_ARGS); \
	else \
		echo "❌ pytest-watch not installed"; \
		echo "   Install: pip install pytest-watch"; \
		exit 1; \
	fi

# ════════════════════════════════════════════════════════════════════════════
# Code Quality
# ════════════════════════════════════════════════════════════════════════════

.PHONY: lint
lint: ## Run linting with ruff
	@echo "🔍 Running linter (ruff)..."
	@if command -v ruff > /dev/null; then \
		ruff check src/ tests/; \
	else \
		echo "⚠️  ruff not installed. Install: pip install ruff"; \
	fi

.PHONY: format
format: ## Auto-format code with black and ruff
	@echo "🎨 Formatting code..."
	@if command -v black > /dev/null; then \
		black src/ tests/ --line-length 100; \
	else \
		echo "⚠️  black not installed. Install: pip install black"; \
	fi
	@if command -v ruff > /dev/null; then \
		ruff check src/ tests/ --fix; \
	fi

.PHONY: validate
validate: ## Run comprehensive validation script (36 checks)
	@echo "✅ Running validation script..."
	@if [ -f "tests/validate_implementation.sh" ]; then \
		bash tests/validate_implementation.sh; \
	else \
		echo "⚠️  Validation script not found at tests/validate_implementation.sh"; \
	fi

# ════════════════════════════════════════════════════════════════════════════
# Development Setup
# ════════════════════════════════════════════════════════════════════════════

.PHONY: install-dev
install-dev: check-venv ## Install development dependencies (venv must exist, use setup-dev for first time)
	@echo "📦 Installing all dependencies (production + testing)..."
	@bash -c "source $(VENV)/bin/activate && pip3 install --upgrade pip"
	@bash -c "source $(VENV)/bin/activate && pip3 install -r requirements.txt"
	@if [ -f "requirements-dev.txt" ]; then \
		bash -c "source $(VENV)/bin/activate && pip3 install -r requirements-dev.txt"; \
	fi
	@echo "✅ Development dependencies installed"
	@echo ""
	@echo "💡 For first-time setup, use: make setup-dev"

# ════════════════════════════════════════════════════════════════════════════
# Cleanup
# ════════════════════════════════════════════════════════════════════════════

.PHONY: clean
clean: ## Clean test artifacts (cache, coverage, logs)
	@echo "🧹 Cleaning test artifacts..."
	@rm -rf .pytest_cache
	@rm -rf htmlcov
	@rm -f coverage.xml
	@rm -f .coverage
	@rm -f mock_servers.log
	@rm -f .mock_servers.pid
	@echo "✅ Test artifacts cleaned"

.PHONY: clean-all
clean-all: clean stop-mock-servers ## Deep clean (cache, coverage, .pyc, __pycache__)
	@echo "🧹 Deep cleaning..."
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete
	@find . -type f -name "*.pyo" -delete
	@find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	@rm -rf .ruff_cache
	@rm -rf .mypy_cache
	@echo "✅ Deep clean completed"

.PHONY: clean-venv
clean-venv: clean-all ## Remove virtual environment (use with caution)
	@echo "🧹 Removing virtual environment..."
	@if [ -d "$(VENV)" ]; then \
		rm -rf $(VENV); \
		echo "✅ Virtual environment removed"; \
		echo "   Run 'make setup-dev' to recreate"; \
	else \
		echo "ℹ️  No virtual environment found"; \
	fi

# ════════════════════════════════════════════════════════════════════════════
# Advanced Testing Targets
# ════════════════════════════════════════════════════════════════════════════

.PHONY: test-full
test-full: clean setup-dev start-mock-servers ## Complete test workflow (setup, start servers, test, coverage)
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "  Full Test Suite (Install → Servers → Tests → Coverage)"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@sleep 2
	@$(MAKE) test-coverage
	@$(MAKE) validate
	@$(MAKE) stop-mock-servers
	@echo ""
	@echo "✅ Full test suite completed successfully!"
	@echo "   Check htmlcov/index.html for coverage report"

.PHONY: test-specific
test-specific: check-venv ## Run specific test file (use: make test-specific FILE=tests/unit/test_log_analyzer.py)
	@if [ -z "$(FILE)" ]; then \
		echo "❌ Usage: make test-specific FILE=<test_file_path>"; \
		echo "   Example: make test-specific FILE=tests/unit/test_log_analyzer.py"; \
		exit 1; \
	fi
	@echo "🧪 Running specific test: $(FILE)"
	@$(PYTEST) $(FILE) $(PYTEST_ARGS) -v

.PHONY: test-by-marker
test-by-marker: check-venv ## Run tests by marker (use: make test-by-marker MARKER=integration)
	@if [ -z "$(MARKER)" ]; then \
		echo "❌ Usage: make test-by-marker MARKER=<marker_name>"; \
		echo "   Example: make test-by-marker MARKER=slow"; \
		exit 1; \
	fi
	@echo "🧪 Running tests with marker: $(MARKER)"
	@$(PYTEST) -m $(MARKER) $(PYTEST_ARGS)

# ════════════════════════════════════════════════════════════════════════════
# CI/CD Targets
# ════════════════════════════════════════════════════════════════════════════

.PHONY: ci
ci: clean ## CI/CD pipeline (lint, test, coverage)
	@echo "🤖 Running CI/CD pipeline..."
	@$(MAKE) lint
	@$(MAKE) test-coverage
	@echo "✅ CI/CD pipeline completed"

.PHONY: ci-full
ci-full: clean setup-dev ## Full CI/CD pipeline (setup, lint, validate, test, coverage)
	@echo "🤖 Running full CI/CD pipeline..."
	@$(MAKE) lint
	@$(MAKE) validate
	@$(MAKE) start-mock-servers
	@$(MAKE) test-coverage
	@$(MAKE) stop-mock-servers
	@echo "✅ Full CI/CD pipeline completed"

# ════════════════════════════════════════════════════════════════════════════
# Docker Testing
# ════════════════════════════════════════════════════════════════════════════

.PHONY: test-docker
test-docker: ## Run tests inside Docker container
	@echo "🐳 Running tests in Docker..."
	@docker compose run --rm aiops-orchestrator pytest $(PYTEST_ARGS)

.PHONY: test-docker-coverage
test-docker-coverage: ## Run tests with coverage inside Docker
	@echo "🐳 Running coverage tests in Docker..."
	@docker compose run --rm aiops-orchestrator pytest $(PYTEST_ARGS) $(COVERAGE_ARGS)

# ════════════════════════════════════════════════════════════════════════════
# Default Target
# ════════════════════════════════════════════════════════════════════════════

.DEFAULT_GOAL := help
