"""Kubernetes MCP handler for managing clusters via Telegram/Discord/Slack."""

import json
import re
from typing import Any, Dict, List, Optional

import structlog

logger = structlog.get_logger()


class KubernetesHandler:
    """
    Handles Kubernetes operations via MCP tools.
    
    This handler interprets natural language commands and executes
    the appropriate Kubernetes MCP operations.
    """

    def __init__(self, mcp_tools: Dict[str, Any]):
        """
        Initialize Kubernetes handler.
        
        Args:
            mcp_tools: Dictionary mapping tool names to tool functions
        """
        self.mcp_tools = mcp_tools
        self.k8s_keywords = [
            'pod', 'pods', 'deployment', 'service', 'namespace',
            'node', 'nodes', 'kubectl', 'k8s', 'kubernetes',
            'helm', 'container', 'scale', 'delete', 'deploy'
        ]
        logger.info("kubernetes_handler_initialized", tool_count=len(mcp_tools))

    def is_kubernetes_query(self, message: str) -> bool:
        """
        Check if a message is related to Kubernetes operations.
        
        Args:
            message: User message
            
        Returns:
            True if message is Kubernetes-related
        """
        message_lower = message.lower()
        return any(keyword in message_lower for keyword in self.k8s_keywords)

    async def handle_query(self, message: str, context: Optional[str] = None) -> str:
        """
        Handle a Kubernetes query from the user.
        
        Args:
            message: User message
            context: Optional context (selected namespace, etc.)
            
        Returns:
            Formatted response for the user
        """
        message_lower = message.lower()
        
        try:
            # List pods
            if any(phrase in message_lower for phrase in ['list pod', 'show pod', 'get pod', 'pods']):
                return await self._list_pods(message)
            
            # Get pod details
            elif 'describe pod' in message_lower or 'pod details' in message_lower:
                return await self._get_pod_details(message)
            
            # Pod logs
            elif 'log' in message_lower and 'pod' in message_lower:
                return await self._get_pod_logs(message)
            
            # List namespaces
            elif 'namespace' in message_lower and any(word in message_lower for word in ['list', 'show', 'get']):
                return await self._list_namespaces()
            
            # List nodes
            elif 'node' in message_lower and any(word in message_lower for word in ['list', 'show', 'get']):
                return await self._list_nodes()
            
            # Node stats
            elif 'node' in message_lower and any(word in message_lower for word in ['stats', 'top', 'usage']):
                return await self._node_stats(message)
            
            # List deployments
            elif 'deployment' in message_lower and any(word in message_lower for word in ['list', 'show', 'get']):
                return await self._list_deployments(message)
            
            # Scale deployment
            elif 'scale' in message_lower and 'deployment' in message_lower:
                return await self._scale_deployment(message)
            
            # List services
            elif 'service' in message_lower and any(word in message_lower for word in ['list', 'show', 'get']):
                return await self._list_services(message)
            
            # Helm releases
            elif 'helm' in message_lower and any(word in message_lower for word in ['list', 'show', 'release']):
                return await self._list_helm_releases()
            
            # List events
            elif 'event' in message_lower and any(word in message_lower for word in ['list', 'show', 'get']):
                return await self._list_events(message)
            
            # List contexts
            elif 'context' in message_lower and any(word in message_lower for word in ['list', 'show', 'get']):
                return await self._list_contexts()
            
            # View kubeconfig
            elif 'kubeconfig' in message_lower or 'config' in message_lower:
                return await self._view_config()
            
            # Generic resource query
            elif any(word in message_lower for word in ['list', 'show', 'get']) and 'resource' in message_lower:
                return await self._list_resources(message)
            
            else:
                return self._get_help_message()
        
        except Exception as e:
            logger.error("kubernetes_query_failed", error=str(e))
            return f"❌ Error executing Kubernetes command: {str(e)}"

    async def _list_pods(self, message: str) -> str:
        """List pods, optionally in a specific namespace."""
        # Extract namespace if mentioned
        namespace = self._extract_namespace(message)
        
        if 'mcp_kubernetes_pods_list' in self.mcp_tools:
            tool = self.mcp_tools['mcp_kubernetes_pods_list']
            params = {}
            if namespace:
                result = await tool(namespace=namespace)
            else:
                result = await tool()
            
            return self._format_pod_list(result)
        else:
            return "❌ Kubernetes pods list tool not available"

    async def _get_pod_details(self, message: str) -> str:
        """Get details of a specific pod."""
        pod_name = self._extract_pod_name(message)
        namespace = self._extract_namespace(message) or "default"
        
        if not pod_name:
            return "❌ Please specify a pod name. Example: 'describe pod nginx-123'"
        
        if 'mcp_kubernetes_pods_get' in self.mcp_tools:
            tool = self.mcp_tools['mcp_kubernetes_pods_get']
            result = await tool(name=pod_name, namespace=namespace)
            return self._format_pod_details(result)
        else:
            return "❌ Kubernetes pod get tool not available"

    async def _get_pod_logs(self, message: str) -> str:
        """Get logs from a pod."""
        pod_name = self._extract_pod_name(message)
        namespace = self._extract_namespace(message) or "default"
        
        if not pod_name:
            return "❌ Please specify a pod name. Example: 'logs from pod nginx-123'"
        
        if 'mcp_kubernetes_pods_log' in self.mcp_tools:
            tool = self.mcp_tools['mcp_kubernetes_pods_log']
            # Get last 50 lines by default
            lines = self._extract_number(message, default=50)
            result = await tool(name=pod_name, namespace=namespace, tail=lines)
            return self._format_logs(result, pod_name)
        else:
            return "❌ Kubernetes pod logs tool not available"

    async def _list_namespaces(self) -> str:
        """List all namespaces."""
        if 'mcp_kubernetes_namespaces_list' in self.mcp_tools:
            tool = self.mcp_tools['mcp_kubernetes_namespaces_list']
            result = await tool()
            return self._format_namespace_list(result)
        else:
            return "❌ Kubernetes namespaces list tool not available"

    async def _list_nodes(self) -> str:
        """List all nodes."""
        if 'mcp_kubernetes_resources_list' in self.mcp_tools:
            tool = self.mcp_tools['mcp_kubernetes_resources_list']
            result = await tool(kind="Node")
            return self._format_node_list(result)
        else:
            return "❌ Kubernetes nodes list tool not available"

    async def _node_stats(self, message: str) -> str:
        """Get node statistics."""
        if 'mcp_kubernetes_nodes_top' in self.mcp_tools:
            tool = self.mcp_tools['mcp_kubernetes_nodes_top']
            result = await tool()
            return self._format_node_stats(result)
        else:
            return "❌ Kubernetes node stats tool not available"

    async def _list_deployments(self, message: str) -> str:
        """List deployments."""
        namespace = self._extract_namespace(message)
        
        if 'mcp_kubernetes_resources_list' in self.mcp_tools:
            tool = self.mcp_tools['mcp_kubernetes_resources_list']
            params = {"kind": "Deployment"}
            if namespace:
                params["namespace"] = namespace
            result = await tool(**params)
            return self._format_deployment_list(result)
        else:
            return "❌ Kubernetes deployments list tool not available"

    async def _scale_deployment(self, message: str) -> str:
        """Scale a deployment."""
        deployment_name = self._extract_deployment_name(message)
        replicas = self._extract_number(message)
        namespace = self._extract_namespace(message) or "default"
        
        if not deployment_name:
            return "❌ Please specify deployment name. Example: 'scale deployment nginx to 3'"
        
        if replicas is None:
            return "❌ Please specify number of replicas. Example: 'scale deployment nginx to 3'"
        
        if 'mcp_kubernetes_resources_scale' in self.mcp_tools:
            tool = self.mcp_tools['mcp_kubernetes_resources_scale']
            result = await tool(
                kind="Deployment",
                name=deployment_name,
                namespace=namespace,
                replicas=replicas
            )
            return f"✅ Scaled deployment {deployment_name} to {replicas} replicas\n\n{result}"
        else:
            return "❌ Kubernetes scale tool not available"

    async def _list_services(self, message: str) -> str:
        """List services."""
        namespace = self._extract_namespace(message)
        
        if 'mcp_kubernetes_resources_list' in self.mcp_tools:
            tool = self.mcp_tools['mcp_kubernetes_resources_list']
            params = {"kind": "Service"}
            if namespace:
                params["namespace"] = namespace
            result = await tool(**params)
            return self._format_service_list(result)
        else:
            return "❌ Kubernetes services list tool not available"

    async def _list_helm_releases(self) -> str:
        """List Helm releases."""
        if 'mcp_kubernetes_helm_list' in self.mcp_tools:
            tool = self.mcp_tools['mcp_kubernetes_helm_list']
            result = await tool()
            return self._format_helm_list(result)
        else:
            return "❌ Kubernetes Helm list tool not available"

    async def _list_events(self, message: str) -> str:
        """List Kubernetes events."""
        namespace = self._extract_namespace(message)
        
        if 'mcp_kubernetes_events_list' in self.mcp_tools:
            tool = self.mcp_tools['mcp_kubernetes_events_list']
            params = {}
            if namespace:
                params["namespace"] = namespace
            result = await tool(**params)
            return self._format_events(result)
        else:
            return "❌ Kubernetes events list tool not available"

    async def _list_contexts(self) -> str:
        """List available Kubernetes contexts."""
        if 'mcp_kubernetes_configuration_contexts_list' in self.mcp_tools:
            tool = self.mcp_tools['mcp_kubernetes_configuration_contexts_list']
            result = await tool()
            return self._format_contexts(result)
        else:
            return "❌ Kubernetes contexts list tool not available"

    async def _view_config(self) -> str:
        """View Kubernetes configuration."""
        if 'mcp_kubernetes_configuration_view' in self.mcp_tools:
            tool = self.mcp_tools['mcp_kubernetes_configuration_view']
            result = await tool()
            return f"📋 **Kubernetes Configuration**\n\n```yaml\n{result}\n```"
        else:
            return "❌ Kubernetes configuration view tool not available"

    async def _list_resources(self, message: str) -> str:
        """List generic Kubernetes resources."""
        # Try to extract resource kind
        kind = self._extract_resource_kind(message)
        namespace = self._extract_namespace(message)
        
        if not kind:
            return "❌ Please specify resource kind. Example: 'list pods' or 'show deployments'"
        
        if 'mcp_kubernetes_resources_list' in self.mcp_tools:
            tool = self.mcp_tools['mcp_kubernetes_resources_list']
            params = {"kind": kind}
            if namespace:
                params["namespace"] = namespace
            result = await tool(**params)
            return self._format_resource_list(result, kind)
        else:
            return "❌ Kubernetes resources list tool not available"

    # Formatting methods
    
    def _format_pod_list(self, result: Any) -> str:
        """Format pod list for display."""
        try:
            if isinstance(result, str):
                data = json.loads(result) if result.startswith('{') or result.startswith('[') else result
            else:
                data = result
            
            if isinstance(data, str):
                return f"📦 **Pods**\n\n```\n{data}\n```"
            
            return f"📦 **Pods**\n\n{self._format_json(data)}"
        except Exception:
            return f"📦 **Pods**\n\n```\n{result}\n```"

    def _format_pod_details(self, result: Any) -> str:
        """Format pod details for display."""
        return f"🔍 **Pod Details**\n\n```yaml\n{self._format_result(result)}\n```"

    def _format_logs(self, result: Any, pod_name: str) -> str:
        """Format pod logs for display."""
        logs = self._format_result(result)
        # Truncate if too long
        max_length = 4000
        if len(logs) > max_length:
            logs = logs[-max_length:] + "\n\n... (truncated)"
        return f"📜 **Logs from pod: {pod_name}**\n\n```\n{logs}\n```"

    def _format_namespace_list(self, result: Any) -> str:
        """Format namespace list for display."""
        return f"🏢 **Namespaces**\n\n```\n{self._format_result(result)}\n```"

    def _format_node_list(self, result: Any) -> str:
        """Format node list for display."""
        return f"🖥️ **Nodes**\n\n```\n{self._format_result(result)}\n```"

    def _format_node_stats(self, result: Any) -> str:
        """Format node statistics for display."""
        return f"📊 **Node Statistics**\n\n```\n{self._format_result(result)}\n```"

    def _format_deployment_list(self, result: Any) -> str:
        """Format deployment list for display."""
        return f"🚀 **Deployments**\n\n```\n{self._format_result(result)}\n```"

    def _format_service_list(self, result: Any) -> str:
        """Format service list for display."""
        return f"🌐 **Services**\n\n```\n{self._format_result(result)}\n```"

    def _format_helm_list(self, result: Any) -> str:
        """Format Helm releases for display."""
        return f"⎈ **Helm Releases**\n\n```\n{self._format_result(result)}\n```"

    def _format_events(self, result: Any) -> str:
        """Format events for display."""
        return f"📰 **Events**\n\n```\n{self._format_result(result)}\n```"

    def _format_contexts(self, result: Any) -> str:
        """Format contexts list for display."""
        return f"🔧 **Kubernetes Contexts**\n\n```\n{self._format_result(result)}\n```"

    def _format_resource_list(self, result: Any, kind: str) -> str:
        """Format generic resource list for display."""
        return f"📋 **{kind}**\n\n```\n{self._format_result(result)}\n```"

    def _format_result(self, result: Any) -> str:
        """Format a result for display."""
        if isinstance(result, str):
            return result
        elif isinstance(result, (dict, list)):
            return json.dumps(result, indent=2)
        else:
            return str(result)

    def _format_json(self, data: Any) -> str:
        """Format JSON data for display."""
        try:
            return f"```json\n{json.dumps(data, indent=2)}\n```"
        except Exception:
            return f"```\n{data}\n```"

    # Extraction methods
    
    def _extract_pod_name(self, message: str) -> Optional[str]:
        """Extract pod name from message."""
        # Look for patterns like "pod nginx-123" or "pod: nginx-123"
        patterns = [
            r'pod\s+([a-z0-9-]+)',
            r'pod:\s*([a-z0-9-]+)',
            r'pod\s+"([^"]+)"',
            r"pod\s+'([^']+)'",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, message.lower())
            if match:
                return match.group(1)
        
        return None

    def _extract_deployment_name(self, message: str) -> Optional[str]:
        """Extract deployment name from message."""
        patterns = [
            r'deployment\s+([a-z0-9-]+)',
            r'deployment:\s*([a-z0-9-]+)',
            r'deployment\s+"([^"]+)"',
            r"deployment\s+'([^']+)'",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, message.lower())
            if match:
                return match.group(1)
        
        return None

    def _extract_namespace(self, message: str) -> Optional[str]:
        """Extract namespace from message."""
        patterns = [
            r'namespace\s+([a-z0-9-]+)',
            r'namespace:\s*([a-z0-9-]+)',
            r'in\s+namespace\s+([a-z0-9-]+)',
            r'-n\s+([a-z0-9-]+)',
            r'--namespace\s+([a-z0-9-]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, message.lower())
            if match:
                return match.group(1)
        
        return None

    def _extract_number(self, message: str, default: Optional[int] = None) -> Optional[int]:
        """Extract a number from message."""
        # Look for patterns like "to 3", "scale 5", "last 100"
        patterns = [
            r'to\s+(\d+)',
            r'scale\s+(\d+)',
            r'last\s+(\d+)',
            r'tail\s+(\d+)',
            r'(\d+)\s+replica',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, message.lower())
            if match:
                return int(match.group(1))
        
        # Look for any standalone number
        numbers = re.findall(r'\b(\d+)\b', message)
        if numbers:
            return int(numbers[0])
        
        return default

    def _extract_resource_kind(self, message: str) -> Optional[str]:
        """Extract Kubernetes resource kind from message."""
        message_lower = message.lower()
        
        # Map common terms to K8s resource kinds
        kind_mappings = {
            'pod': 'Pod',
            'pods': 'Pod',
            'deployment': 'Deployment',
            'deployments': 'Deployment',
            'service': 'Service',
            'services': 'Service',
            'svc': 'Service',
            'configmap': 'ConfigMap',
            'configmaps': 'ConfigMap',
            'secret': 'Secret',
            'secrets': 'Secret',
            'ingress': 'Ingress',
            'ingresses': 'Ingress',
            'node': 'Node',
            'nodes': 'Node',
            'namespace': 'Namespace',
            'namespaces': 'Namespace',
            'persistentvolumeclaim': 'PersistentVolumeClaim',
            'pvc': 'PersistentVolumeClaim',
            'persistentvolume': 'PersistentVolume',
            'pv': 'PersistentVolume',
            'statefulset': 'StatefulSet',
            'daemonset': 'DaemonSet',
            'job': 'Job',
            'cronjob': 'CronJob',
        }
        
        for term, kind in kind_mappings.items():
            if term in message_lower:
                return kind
        
        return None

    def _get_help_message(self) -> str:
        """Get help message for Kubernetes commands."""
        return """🤖 **Kubernetes Commands Help**

**Pods:**
- `list pods` or `show pods` - List all pods
- `list pods in namespace <name>` - List pods in a namespace
- `describe pod <name>` - Get pod details
- `logs from pod <name>` - Get pod logs
- `logs from pod <name> last 100` - Get last 100 lines

**Deployments:**
- `list deployments` - List all deployments
- `scale deployment <name> to <num>` - Scale a deployment

**Services:**
- `list services` - List all services

**Nodes:**
- `list nodes` - List all nodes
- `node stats` or `node top` - Get node resource usage

**Namespaces:**
- `list namespaces` - List all namespaces

**Helm:**
- `list helm releases` - List Helm releases

**Events:**
- `list events` - List recent events

**Configuration:**
- `list contexts` - List available contexts
- `show kubeconfig` - View Kubernetes configuration

**Examples:**
- "list pods in namespace production"
- "describe pod nginx-deployment-abc123"
- "scale deployment api-server to 5"
- "logs from pod backend-xyz last 50"
- "show node stats"
"""
