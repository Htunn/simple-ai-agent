# Security Policy

## Supported Versions

| Version | Supported |
|---|---|
| `main` branch | Yes |
| Tagged releases | Latest tag only |

## Reporting a Vulnerability

**Please do NOT report security vulnerabilities via public GitHub Issues.**

To report a security vulnerability, please use one of these methods:

1. **GitHub Private Vulnerability Reporting** (preferred):
   - Go to the repository → Security → Report a vulnerability
   - Fill in the report form with as much detail as possible

2. **Email**: If private reporting is unavailable, email the maintainer directly.
   - Include `[SECURITY]` in the subject line
   - Encrypt your report if possible

### What to Include

- Description of the vulnerability and its potential impact
- Steps to reproduce (proof-of-concept if possible)
- Affected components and versions
- Any suggested mitigations

### What to Expect

- **Acknowledgement** within 48 hours
- **Initial assessment** within 5 business days
- **Fix timeline** communicated once scope is clear
- **Credit** in the release notes (unless you prefer anonymity)

We ask that you:
- Give us reasonable time to fix the issue before public disclosure
- Not exploit the vulnerability beyond what is needed to demonstrate it
- Not access or modify other users' data

## Security Best Practices for Deployment

### Secrets Management

- Never commit `.env`, `.env.production`, or any file containing secrets to git
- Use a secrets manager in production (AWS Secrets Manager, HashiCorp Vault, Doppler)
- Rotate all bot tokens and API keys regularly
- Use different credentials per environment (dev/staging/production)

### Container Security

- The Docker image runs as non-root user UID 1000
- `no-new-privileges` security option is enforced
- Kubeconfig is mounted read-only
- Regularly rebuild images to pick up base image security patches:
  ```bash
  docker compose build --no-cache
  ```

### Network Security

- All services run on an isolated Docker bridge network
- Only the `app` service port (8000) should be exposed externally
- Use TLS termination (nginx/Caddy/traefik) in front of the application
- Database and Redis ports are not exposed publicly in the default compose file

### Kubernetes MCP Security

- Use a **read-only** kubeconfig where possible
- Apply least-privilege RBAC — the agent only needs read access for monitoring
- For remediation actions, scope permissions to specific namespaces
- Regularly audit which playbooks have HIGH risk steps enabled

### API Security

- Rate limiting is enabled by default (60 req/min per IP)
- Slack webhook signature verification is enforced
- Alertmanager webhook supports shared-secret validation (`ALERTMANAGER_WEBHOOK_SECRET`)
- All inputs are validated via Pydantic models

### Dependency Security

```bash
# Audit dependencies for known vulnerabilities
pip audit

# Or using safety
pip install safety
safety check -r requirements.txt
```

Keep dependencies up to date and monitor [GitHub Dependabot alerts](https://docs.github.com/en/code-security/dependabot).
