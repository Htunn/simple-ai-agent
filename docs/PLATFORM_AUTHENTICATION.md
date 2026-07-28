# Platform Authentication & Authorization Guide

## Overview

This document describes how to authenticate and integrate with real production platforms: Nutanix Prism Central, VMware vCenter, Kubernetes, and OpenShift.

---

## 🔐 Nutanix Prism Central Authentication

### Authentication Methods

Nutanix Prism Central supports two authentication methods:

#### 1. **Basic Authentication** (Username/Password)
```python
# Configuration
NUTANIX_HOST = "prism-central.example.com"
NUTANIX_PORT = 9440
NUTANIX_USERNAME = "admin"
NUTANIX_PASSWORD = "secure_password"

# Usage in platform client
client = NutanixClient(
    host=NUTANIX_HOST,
    port=NUTANIX_PORT,
    username=NUTANIX_USERNAME,
    password=NUTANIX_PASSWORD,
    verify_ssl=True  # Set to False for self-signed certs
)
```

#### 2. **API Key Authentication** (Recommended for production)
```python
# Generate API key in Prism Central:
# Settings → Local User Configuration → Generate API Keys

NUTANIX_API_KEY = "your-api-key-here"

client = NutanixClient(
    host=NUTANIX_HOST,
    port=NUTANIX_PORT,
    api_key=NUTANIX_API_KEY,
    verify_ssl=True
)
```

### Environment Variables
```bash
export NUTANIX_HOST="prism-central.example.com"
export NUTANIX_PORT="9440"
export NUTANIX_USERNAME="admin"
export NUTANIX_PASSWORD="your_password"
# OR
export NUTANIX_API_KEY="your-api-key"
export NUTANIX_VERIFY_SSL="true"
```

### Permissions Required
- **Read Operations**: `Viewer` role or higher
- **Write Operations** (power on/off, delete): `Operator` role
- **Full Management**: `Cluster Admin` role

### API Endpoints
```
Base URL: https://{host}:{port}/api/nutanix/v3
Authentication: Basic Auth (Base64 encoded username:password)
Headers:
  - Content-Type: application/json
  - Authorization: Basic {base64_credentials}
```

---

## 🔐 VMware vCenter Authentication

### Authentication Method: Session-Based

VMware vCenter uses a two-step authentication process:

#### Step 1: Login and Get Session Token
```python
# Configuration
VCENTER_HOST = "vcenter.example.com"
VCENTER_USERNAME = "administrator@vsphere.local"
VCENTER_PASSWORD = "secure_password"

# Login to get session ID
client = VMwareClient(
    host=VCENTER_HOST,
    username=VCENTER_USERNAME,
    password=VCENTER_PASSWORD,
    verify_ssl=True
)

# Session token is automatically managed
```

#### Step 2: Use Session Token for API Calls
The client automatically handles session management, including:
- Initial login
- Session refresh
- Re-authentication on session expiry

### Environment Variables
```bash
export VCENTER_HOST="vcenter.example.com"
export VCENTER_USERNAME="administrator@vsphere.local"
export VCENTER_PASSWORD="your_password"
export VCENTER_VERIFY_SSL="true"
```

### Permissions Required
- **Read-Only**: `Read-only` role
- **VM Operations**: `Virtual Machine Power User` role
- **Full Management**: `Administrator` role

### API Endpoints
```
Login: POST https://{host}/rest/com/vmware/cis/session
Headers:
  - Content-Type: application/json
  - Authorization: Basic {base64_credentials}

Response: { "value": "session_token_here" }

Subsequent Calls:
  - Headers: vmware-api-session-id: {session_token}
```

---

## 🔐 Kubernetes Authentication

### Authentication Methods

Kubernetes supports multiple authentication methods:

#### 1. **Bearer Token** (ServiceAccount - Recommended for Applications)
```python
# Get token from ServiceAccount
K8S_HOST = "https://k8s-api.example.com:6443"
K8S_TOKEN = "eyJhbGciOiJSUzI1NiIsImtpZCI6..."  # From ServiceAccount

client = KubernetesClient(
    host=K8S_HOST,
    token=K8S_TOKEN,
    verify_ssl=True
)
```

**Create ServiceAccount:**
```bash
# Create ServiceAccount
kubectl create serviceaccount aiops-orchestrator -n default

# Create ClusterRole with permissions
kubectl create clusterrole aiops-reader \
  --verb=get,list,watch \
  --resource=pods,deployments,services,nodes,namespaces

# Bind role to ServiceAccount
kubectl create clusterrolebinding aiops-orchestrator-binding \
  --clusterrole=aiops-reader \
  --serviceaccount=default:aiops-orchestrator

# Get token (Kubernetes 1.24+)
kubectl create token aiops-orchestrator --duration=8760h

# Or get from secret (older versions)
kubectl get secret $(kubectl get sa aiops-orchestrator -o jsonpath='{.secrets[0].name}') \
  -o jsonpath='{.data.token}' | base64 -d
```

#### 2. **Kubeconfig File** (For Development/Testing)
```python
from kubernetes import client, config

# Load from default kubeconfig (~/.kube/config)
config.load_kube_config()

# Or specify kubeconfig path
config.load_kube_config(config_file="/path/to/kubeconfig")

# Create API client
v1 = client.CoreV1Api()
```

#### 3. **Certificate-Based Authentication**
```python
K8S_CA_CERT = "/path/to/ca.crt"
K8S_CLIENT_CERT = "/path/to/client.crt"
K8S_CLIENT_KEY = "/path/to/client.key"

client = KubernetesClient(
    host=K8S_HOST,
    ca_cert=K8S_CA_CERT,
    client_cert=K8S_CLIENT_CERT,
    client_key=K8S_CLIENT_KEY
)
```

### Environment Variables
```bash
export K8S_HOST="https://k8s-api.example.com:6443"
export K8S_TOKEN="your-bearer-token"
export K8S_CA_CERT="/path/to/ca.crt"
export K8S_VERIFY_SSL="true"
# OR
export KUBECONFIG="/path/to/kubeconfig"
```

### RBAC Permissions Required

**Minimum Read-Only Access:**
```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: aiops-orchestrator-viewer
rules:
  - apiGroups: [""]
    resources: ["pods", "pods/log", "services", "nodes", "namespaces", "events"]
    verbs: ["get", "list", "watch"]
  - apiGroups: ["apps"]
    resources: ["deployments", "replicasets", "statefulsets", "daemonsets"]
    verbs: ["get", "list", "watch"]
  - apiGroups: ["batch"]
    resources: ["jobs", "cronjobs"]
    verbs: ["get", "list", "watch"]
```

**With Write Access (scale, delete):**
```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: aiops-orchestrator-operator
rules:
  - apiGroups: [""]
    resources: ["pods", "services"]
    verbs: ["get", "list", "watch", "delete"]
  - apiGroups: ["apps"]
    resources: ["deployments", "deployments/scale"]
    verbs: ["get", "list", "watch", "update", "patch"]
```

---

## 🔐 OpenShift Authentication

### Authentication Methods

OpenShift extends Kubernetes authentication with OAuth:

#### 1. **OAuth Token** (Recommended)
```python
# Get token via oc CLI
# oc login https://api.openshift.example.com:6443
# oc whoami -t

OPENSHIFT_HOST = "https://api.openshift.example.com:6443"
OPENSHIFT_TOKEN = "sha256~your-oauth-token-here"

client = OpenShiftClient(
    host=OPENSHIFT_HOST,
    token=OPENSHIFT_TOKEN,
    verify_ssl=True
)
```

**Get Token Programmatically:**
```bash
# Login and get token
oc login https://api.openshift.example.com:6443 \
  --username=developer \
  --password=password

# Get token
export OPENSHIFT_TOKEN=$(oc whoami -t)
```

#### 2. **ServiceAccount Token** (For Applications)
```bash
# Create ServiceAccount
oc create serviceaccount aiops-orchestrator -n default

# Grant permissions
oc adm policy add-cluster-role-to-user view system:serviceaccount:default:aiops-orchestrator
oc adm policy add-cluster-role-to-user cluster-reader system:serviceaccount:default:aiops-orchestrator

# Get token
oc create token aiops-orchestrator --duration=8760h
```

### Environment Variables
```bash
export OPENSHIFT_HOST="https://api.openshift.example.com:6443"
export OPENSHIFT_TOKEN="your-oauth-token"
export OPENSHIFT_VERIFY_SSL="true"
```

### Permissions Required

**Read-Only Access:**
```bash
oc adm policy add-cluster-role-to-user view system:serviceaccount:default:aiops-orchestrator
oc adm policy add-cluster-role-to-user cluster-reader system:serviceaccount:default:aiops-orchestrator
```

**Operator Access (with write permissions):**
```bash
oc adm policy add-cluster-role-to-user edit system:serviceaccount:default:aiops-orchestrator
```

**Full Admin Access:**
```bash
oc adm policy add-cluster-role-to-user cluster-admin system:serviceaccount:default:aiops-orchestrator
```

### OpenShift-Specific Resources

OpenShift adds additional resources beyond Kubernetes:
- **Projects**: Namespace + RBAC + quotas
- **Routes**: Layer 7 load balancing
- **BuildConfigs**: Source-to-Image (S2I) builds
- **DeploymentConfigs**: OpenShift-specific deployment strategy
- **ImageStreams**: Image repository abstraction

---

## 🔧 Configuration File

### config/platforms.yml

```yaml
platforms:
  nutanix:
    enabled: true
    host: "${NUTANIX_HOST}"
    port: 9440
    auth_method: "api_key"  # or "basic"
    api_key: "${NUTANIX_API_KEY}"
    # Or for basic auth:
    # username: "${NUTANIX_USERNAME}"
    # password: "${NUTANIX_PASSWORD}"
    verify_ssl: true
    timeout: 30
    
  vmware:
    enabled: true
    host: "${VCENTER_HOST}"
    auth_method: "session"
    username: "${VCENTER_USERNAME}"
    password: "${VCENTER_PASSWORD}"
    verify_ssl: true
    session_timeout: 300  # 5 minutes
    timeout: 30
    
  kubernetes:
    enabled: true
    host: "${K8S_HOST}"
    auth_method: "token"  # or "kubeconfig" or "cert"
    token: "${K8S_TOKEN}"
    # Or for kubeconfig:
    # kubeconfig_path: "~/.kube/config"
    # Or for cert auth:
    # ca_cert: "/path/to/ca.crt"
    # client_cert: "/path/to/client.crt"
    # client_key: "/path/to/client.key"
    verify_ssl: true
    namespace: "default"  # Default namespace
    timeout: 30
    
  openshift:
    enabled: true
    host: "${OPENSHIFT_HOST}"
    auth_method: "oauth_token"
    token: "${OPENSHIFT_TOKEN}"
    verify_ssl: true
    namespace: "default"
    timeout: 30
```

---

## 🔒 Security Best Practices

### 1. **Never Hardcode Credentials**
❌ **Bad:**
```python
password = "admin123"  # Never do this!
```

✅ **Good:**
```python
import os
password = os.getenv("NUTANIX_PASSWORD")
if not password:
    raise ValueError("NUTANIX_PASSWORD environment variable not set")
```

### 2. **Use Secrets Management**

**Kubernetes Secrets:**
```bash
kubectl create secret generic platform-credentials \
  --from-literal=nutanix-api-key='your-key' \
  --from-literal=vcenter-password='your-password' \
  --from-literal=k8s-token='your-token'
```

**HashiCorp Vault:**
```python
import hvac
client = hvac.Client(url='http://vault:8200', token='your-vault-token')
nutanix_creds = client.secrets.kv.v2.read_secret_version(path='nutanix/production')
```

### 3. **Rotate Credentials Regularly**
- API keys: Every 90 days
- OAuth tokens: Every 30 days
- ServiceAccount tokens: Set expiration (--duration flag)

### 4. **Use SSL/TLS Verification**
Always verify SSL certificates in production:
```python
verify_ssl=True  # Always use this in production
```

For development with self-signed certs:
```python
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
verify_ssl=False  # Only for development!
```

### 5. **Least Privilege Principle**
Grant minimum permissions required:
- Read-only for monitoring
- Specific write permissions only when needed
- Avoid cluster-admin unless absolutely necessary

### 6. **Audit Logging**
Enable audit logging for all platform access:
```python
import logging
logger = logging.getLogger(__name__)

def api_call_with_audit(func):
    def wrapper(*args, **kwargs):
        logger.info(f"API call: {func.__name__} user={current_user} args={args}")
        result = func(*args, **kwargs)
        logger.info(f"API call completed: {func.__name__} status=success")
        return result
    return wrapper
```

---

## 📝 Testing Authentication

### Test Script: `scripts/test_platform_auth.py`

```python
#!/usr/bin/env python3
"""Test platform authentication."""
import os
import sys
from src.platforms import NutanixClient, VMwareClient
from src.k8s.client import KubernetesClient

def test_nutanix_auth():
    """Test Nutanix authentication."""
    try:
        client = NutanixClient(
            host=os.getenv("NUTANIX_HOST"),
            port=int(os.getenv("NUTANIX_PORT", "9440")),
            api_key=os.getenv("NUTANIX_API_KEY"),
            verify_ssl=os.getenv("NUTANIX_VERIFY_SSL", "true").lower() == "true"
        )
        health = client.health_check()
        print(f"✅ Nutanix: {health.status}")
        return True
    except Exception as e:
        print(f"❌ Nutanix: {e}")
        return False

def test_vmware_auth():
    """Test VMware authentication."""
    try:
        client = VMwareClient(
            host=os.getenv("VCENTER_HOST"),
            username=os.getenv("VCENTER_USERNAME"),
            password=os.getenv("VCENTER_PASSWORD"),
            verify_ssl=os.getenv("VCENTER_VERIFY_SSL", "true").lower() == "true"
        )
        health = client.health_check()
        print(f"✅ VMware: {health.status}")
        return True
    except Exception as e:
        print(f"❌ VMware: {e}")
        return False

def test_kubernetes_auth():
    """Test Kubernetes authentication."""
    try:
        client = KubernetesClient(
            host=os.getenv("K8S_HOST"),
            token=os.getenv("K8S_TOKEN"),
            verify_ssl=os.getenv("K8S_VERIFY_SSL", "true").lower() == "true"
        )
        health = client.health_check()
        print(f"✅ Kubernetes: {health.status}")
        return True
    except Exception as e:
        print(f"❌ Kubernetes: {e}")
        return False

if __name__ == "__main__":
    results = [
        test_nutanix_auth(),
        test_vmware_auth(),
        test_kubernetes_auth()
    ]
    
    if all(results):
        print("\n✅ All platform authentications successful!")
        sys.exit(0)
    else:
        print("\n❌ Some platform authentications failed")
        sys.exit(1)
```

---

## 🚀 Quick Start

### 1. Set Environment Variables
```bash
# Copy example env file
cp .env.example .env

# Edit with your credentials
vi .env
```

### 2. Test Connection
```bash
python scripts/test_platform_auth.py
```

### 3. Run AIOps Orchestrator
```bash
make setup-dev
make start-platform-mocks  # For testing
# OR connect to real platforms
export USE_REAL_PLATFORMS=true
make run
```

---

## 📚 References

- **Nutanix API**: https://www.nutanix.dev/api-reference/prism-central-v3/
- **VMware vSphere API**: https://developer.vmware.com/apis/vsphere-automation/latest/
- **Kubernetes API**: https://kubernetes.io/docs/reference/using-api/
- **OpenShift API**: https://docs.openshift.com/container-platform/latest/rest_api/index.html

---

## ⚠️ Troubleshooting

### Common Issues

**1. SSL Certificate Verification Failed**
```bash
# For development only - disable SSL verification
export NUTANIX_VERIFY_SSL=false
export VCENTER_VERIFY_SSL=false
```

**2. Token Expired**
```bash
# Regenerate Kubernetes token
kubectl create token aiops-orchestrator --duration=8760h

# Regenerate OpenShift token
oc login && oc whoami -t
```

**3. Permission Denied**
```bash
# Check current permissions
kubectl auth can-i --list

# For OpenShift
oc adm policy who-can get pods
```

**4. Connection Timeout**
```bash
# Test connectivity
curl -k https://{host}:{port}/api/
nc -zv {host} {port}
```
