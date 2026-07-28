# Platform Authentication Quick Reference

**AIOps Orchestrator v2.1.0** - Platform credential configuration guide

---

## Quick Start

### Option 1: Environment Variables (Recommended for Dev/Test)

```bash
# .env file or export
NUTANIX_ENDPOINT=http://localhost:5001
NUTANIX_USERNAME=admin
NUTANIX_PASSWORD=admin
NUTANIX_VERIFY_SSL=false

VMWARE_ENDPOINT=http://localhost:5002
VMWARE_USERNAME=administrator@vsphere.local
VMWARE_PASSWORD=admin
VMWARE_VERIFY_SSL=false

K8S_ENDPOINT=http://localhost:5004
K8S_TOKEN=mock-bearer-token-12345
K8S_VERIFY_SSL=false

OPENSHIFT_ENDPOINT=http://localhost:5003
OPENSHIFT_TOKEN=mock-bearer-token-12345
OPENSHIFT_VERIFY_SSL=false
```

### Option 2: Database (Recommended for Production)

```sql
-- Insert platform configuration
INSERT INTO platform_configs (
    name,
    platform_type,
    endpoint,
    username,
    password_encrypted,
    verify_ssl,
    enabled,
    timeout,
    max_retries
) VALUES (
    'production-nutanix',
    'nutanix',
    'https://prism-central.example.com:9440',
    'admin',
    'encrypted_password_here',  -- Use encryption in production
    true,
    true,
    30,
    3
);
```

---

## Testing Platform Connections

### 1. Using Test Script

```bash
python3 scripts/test_platform_auth.py
```

**Expected output:**
```
✅ Nutanix: Connected to prism-central.example.com
   - VMs: 42 found
   - Clusters: 2 available

✅ VMware: Session created for vcenter.example.com
   - VMs: 156 found
   - Hosts: 8 available

✅ Kubernetes: Authenticated to k8s-api.example.com
   - Nodes: 5 ready
   - Pods: 234 running

✅ OpenShift: Authenticated to api.openshift.example.com
   - Projects: 12 found
   - Pods: 187 running
```

### 2. Using Python REPL

```python
from src.services.platform_registry import PlatformRegistry
from src.platforms import PlatformType
import asyncio

async def test_platforms():
    registry = PlatformRegistry()
    await registry.initialize()
    
    # List configured platforms
    print(f"Platforms: {list(registry._configs.keys())}")
    
    # Test Nutanix connection
    nutanix = await registry.get_client("nutanix-env")
    health = await nutanix.health_check()
    print(f"Nutanix health: {health.status}")
    
    # List VMs
    vms = await nutanix.list_vms()
    print(f"VMs found: {len(vms)}")
    for vm in vms[:5]:
        print(f"  - {vm.name} ({vm.power_state})")

asyncio.run(test_platforms())
```

### 3. Using HTTP API

```bash
# Check platform health
curl http://localhost:8000/health/platforms

# Expected response:
{
  "nutanix-env": {
    "status": "healthy",
    "latency_ms": 45,
    "endpoint": "http://localhost:5001"
  },
  "vmware-env": {
    "status": "healthy",
    "latency_ms": 32,
    "endpoint": "http://localhost:5002"
  }
}
```

---

## Common Operations

### Nutanix Operations

```python
# List VMs
vms = await nutanix_client.list_vms()

# Get specific VM
vm = await nutanix_client.get_vm(vm_uuid="11111111-1111-1111-1111-111111111111")

# Power operations
await nutanix_client.power_on_vm(vm_uuid="...")
await nutanix_client.power_off_vm(vm_uuid="...")
await nutanix_client.reset_vm(vm_uuid="...")

# Delete VM
await nutanix_client.delete_vm(vm_uuid="...")
```

### VMware Operations

```python
# List VMs
vms = await vmware_client.list_vms()

# Get specific VM
vm = await vmware_client.get_vm(vm_id="vm-1001")

# Power operations
await vmware_client.power_on_vm(vm_id="vm-1001")
await vmware_client.power_off_vm(vm_id="vm-1001")
await vmware_client.reset_vm(vm_id="vm-1001")

# List hosts
hosts = await vmware_client.list_hosts()

# Disconnect host
await vmware_client.disconnect_host(host_id="host-10")
```

### Kubernetes Operations

```python
# List pods
pods = await k8s_client.list_pods(namespace="production")

# Get specific pod
pod = await k8s_client.get_pod(namespace="production", name="api-server-abc123")

# Delete pod
await k8s_client.delete_pod(namespace="production", name="api-server-abc123")

# List nodes
nodes = await k8s_client.list_nodes()
```

### OpenShift Operations

```python
# List projects
projects = await openshift_client.list_projects()

# List pods in project
pods = await openshift_client.list_pods(namespace="production")

# List routes
routes = await openshift_client.list_routes(namespace="production")

# List builds
builds = await openshift_client.list_builds(namespace="production")
```

---

## Troubleshooting

### Error: "Platform not found"

**Cause**: No configuration in database or environment variables

**Solution**:
```bash
# Check environment variables
env | grep -E "(NUTANIX|VMWARE|K8S|OPENSHIFT)_ENDPOINT"

# Or add to .env
echo "NUTANIX_ENDPOINT=https://your-endpoint" >> .env
```

### Error: "Authentication failed"

**Cause**: Invalid credentials

**Solution**:
```bash
# Nutanix - Test with curl
curl -u admin:password https://prism-central.example.com:9440/api/nutanix/v3/users/me

# VMware - Test session creation
curl -X POST -u admin:password https://vcenter.example.com/rest/com/vmware/cis/session

# Kubernetes - Test token
curl -H "Authorization: Bearer $K8S_TOKEN" https://k8s-api.example.com:6443/api/v1/nodes
```

### Error: "SSL verification failed"

**Cause**: Self-signed certificates

**Solution**:
```bash
# Development only - disable SSL verification
export NUTANIX_VERIFY_SSL=false
export VMWARE_VERIFY_SSL=false
export K8S_VERIFY_SSL=false

# Production - install CA certificate
# Then set verify_ssl=true
```

### Error: "Connection timeout"

**Cause**: Network connectivity issues or firewall

**Solution**:
```bash
# Test network connectivity
nc -zv prism-central.example.com 9440
nc -zv vcenter.example.com 443
nc -zv k8s-api.example.com 6443

# Check firewall rules
# Ensure ports are accessible from AIOps Orchestrator
```

---

## Security Best Practices

### ✅ DO

- ✅ Use database configuration in production
- ✅ Encrypt passwords at rest (`password_encrypted` column)
- ✅ Enable SSL verification (`verify_ssl: true`)
- ✅ Use least-privilege service accounts
- ✅ Rotate credentials every 90 days
- ✅ Use environment variables for local dev only
- ✅ Store secrets in Kubernetes Secrets or Vault

### ❌ DON'T

- ❌ Commit credentials to version control
- ❌ Use admin accounts (use dedicated service accounts)
- ❌ Disable SSL verification in production
- ❌ Share credentials across environments
- ❌ Store plaintext passwords in database
- ❌ Use infinite token expiration

---

## Production Deployment

### Kubernetes (Recommended)

```yaml
# secrets.yaml
apiVersion: v1
kind: Secret
metadata:
  name: aiops-platform-creds
type: Opaque
stringData:
  # Nutanix
  NUTANIX_ENDPOINT: "https://prism-central.example.com:9440"
  NUTANIX_USERNAME: "svc-aiops"
  NUTANIX_PASSWORD: "{{ from_vault }}"
  
  # VMware
  VMWARE_ENDPOINT: "https://vcenter.example.com"
  VMWARE_USERNAME: "svc-aiops@vsphere.local"
  VMWARE_PASSWORD: "{{ from_vault }}"
  
  # Kubernetes (for multi-cluster)
  K8S_ENDPOINT: "https://remote-cluster-api.example.com:6443"
  K8S_TOKEN: "{{ from_vault }}"

---
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: aiops-orchestrator
spec:
  template:
    spec:
      containers:
      - name: aiops
        envFrom:
        - secretRef:
            name: aiops-platform-creds
```

### Docker Compose

```yaml
# docker-compose.yml
services:
  aiops-orchestrator:
    image: aiops-orchestrator:v2.1.0
    env_file:
      - .env.production
    environment:
      # Platform auth loaded from .env.production
      - NUTANIX_ENDPOINT=${NUTANIX_ENDPOINT}
      - NUTANIX_USERNAME=${NUTANIX_USERNAME}
      - NUTANIX_PASSWORD=${NUTANIX_PASSWORD}
```

---

## Reference

| Document | Link |
|----------|------|
| **Full Production Guide** | [docs/PRODUCTION_READINESS.md](PRODUCTION_READINESS.md) |
| **Platform Authentication Details** | [docs/PLATFORM_AUTHENTICATION.md](PLATFORM_AUTHENTICATION.md) |
| **Implementation Summary** | [docs/PLATFORM_AUTH_IMPLEMENTATION_SUMMARY.md](PLATFORM_AUTH_IMPLEMENTATION_SUMMARY.md) |
| **Architecture** | [docs/architecture.md](architecture.md) |
| **README** | [README.md](../README.md) |

---

