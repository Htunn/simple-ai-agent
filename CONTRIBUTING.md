# Contributing to Simple AI Agent

Thank you for your interest in contributing! This document outlines the process for contributing to the project.

## Code of Conduct

Be respectful, inclusive, and constructive. We welcome contributions from everyone regardless of experience level.

## Getting Started

1. **Fork** the repository on GitHub
2. **Clone** your fork locally:
   ```bash
   git clone https://github.com/YOUR_USERNAME/simple-ai-agent.git
   cd simple-ai-agent
   ```
3. **Set up** the development environment:
   ```bash
   python3.12 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   pip install -r requirements-dev.txt  # if present
   ```
4. **Create a branch** for your change:
   ```bash
   git checkout -b feature/your-feature-name
   # or
   git checkout -b fix/issue-description
   ```

## Development Workflow

### Running Locally

```bash
cp .env.example .env
# Edit .env with your tokens
docker compose up -d postgres redis
python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

### Running Tests

```bash
pytest                       # all tests
pytest --cov=src             # with coverage
pytest -k "test_something"   # specific tests
```

### Code Quality

All code must pass these checks before merging:

```bash
black src/             # auto-format (line length 100)
ruff check src/        # linting
mypy src/              # type checking
```

## Commit Convention

We use [Conventional Commits](https://www.conventionalcommits.org/):

| Prefix | Use for |
|---|---|
| `feat:` | New features |
| `fix:` | Bug fixes |
| `docs:` | Documentation changes |
| `refactor:` | Code restructuring (no behaviour change) |
| `test:` | Adding or updating tests |
| `chore:` | Tooling, CI, dependency updates |
| `perf:` | Performance improvements |

**Examples:**
```
feat: add RCA engine integration to watchloop alerts
fix: handle timeout in SSE transport gracefully
docs: update AIOps configuration reference
```

## Pull Request Process

1. **Ensure tests pass** and code quality tools are clean
2. **Update documentation** — README, docstrings, or relevant `docs/` files
3. **Keep PRs focused** — one feature or fix per PR
4. **Describe your changes** clearly in the PR description, including:
   - What the PR does
   - Why it's needed
   - How to test it
5. **Reference any related issues**: `Closes #123`

PRs will be reviewed within a few days. Maintainers may request changes.

## Adding a New Channel Adapter

1. Create `src/channels/YOUR_CHANNEL_adapter.py` implementing `BaseAdapter`
2. Register it in `src/channels/router.py`
3. Add config fields to `src/config.py`
4. Update `.env.example` with new variables
5. Add documentation in `docs/` and update `README.md`

## Adding a New MCP Server

1. Add the server config to `.mcp-config.json`
2. If using a new transport type, implement a new `BaseMCPTransport` subclass in `src/mcp/`
3. Register the transport type in `MCPManager._create_transport()`
4. Document the tools in `docs/mcp-integration.md`

## Adding an AIOps Playbook

1. Implement your playbook steps in `src/aiops/playbooks.py` (see `PlaybookRegistry`)
2. Add matching rules in the rule engine configuration
3. Test with a mock `ClusterEvent`

## Reporting Issues

Use GitHub Issues with the appropriate label:
- `bug` — something is broken
- `enhancement` — new feature request
- `documentation` — docs improvements
- `question` — usage questions

Please include:
- Python version and OS
- Relevant configuration (with secrets removed)
- Steps to reproduce
- Expected vs actual behaviour
- Logs (use `LOG_LEVEL=DEBUG`)

## Security Issues

**Do not** open public GitHub Issues for security vulnerabilities.  
See [SECURITY.md](SECURITY.md) for the responsible disclosure process.
