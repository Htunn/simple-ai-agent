"""Core message handling service."""

import asyncio
import re
import subprocess
import uuid
from typing import Optional

import structlog

from src.ai import ContextBuilder, GitHubModelsClient, ModelSelector, PromptManager
from src.channels.base import ChannelMessage
from src.channels.router import MessageRouter
from src.database import get_db_session
from src.database.redis import RedisCache, get_redis
from src.mcp.mcp_manager import MCPManager
from src.services.session_manager import SessionManager

logger = structlog.get_logger()

# Kubernetes keywords for detection
K8S_KEYWORDS = [
    'pod', 'pods', 'deployment', 'deployments', 'service', 'services',
    'namespace', 'namespaces', 'node', 'nodes', 'kubectl', 'k8s', 'kubernetes',
    'helm', 'container', 'containers', 'scale', 'configmap', 'secret',
    'ingress', 'pvc', 'persistentvolume', 'statefulset', 'daemonset'
]

# Security scanning keywords for detection (simplePortChecker tools)
SECURITY_KEYWORDS = [
    'port', 'ports', 'open', 'closed', 'listening', 'scan',
    'security', 'certificate', 'cert', 'ssl', 'tls', 'https',
    'waf', 'cdn', 'cloudflare', 'protection', 'firewall',
    'mtls', 'mutual', 'owasp', 'vulnerability', 'vulnerabilities',
    'headers', 'security headers', 'hsts', 'csp', 'cors',
    'azure', 'hybrid identity', 'tenant'
]


class MessageHandler:
    """Handles incoming messages and orchestrates responses."""

    def __init__(
        self,
        router: MessageRouter,
        ai_client: GitHubModelsClient,
        mcp_manager: Optional[MCPManager] = None,
    ):
        self.router = router
        self.ai_client = ai_client
        self.mcp_manager = mcp_manager
        logger.info(
            "message_handler_initialized",
            mcp_enabled=mcp_manager is not None,
        )
    
    def _format_kubectl_table(self, output: str, resource_type: str = "pods") -> str:
        """
        Format kubectl table output for better readability in chat.
        
        Args:
            output: Raw kubectl output
            resource_type: Type of resource (pods, nodes, deployments, etc.)
            
        Returns:
            Formatted string for chat display
        """
        lines = output.strip().split('\n')
        if len(lines) <= 1:
            return output
        
        # Parse header and rows
        header_line = lines[0]
        data_lines = lines[1:]
        
        # For pods, show key information in a compact format
        if resource_type == "pods":
            formatted = []
            for line in data_lines:
                parts = line.split()
                if len(parts) >= 5:
                    name = parts[0]
                    ready = parts[1]
                    status = parts[2]
                    restarts = parts[3]
                    age = parts[4]
                    
                    # Status emoji
                    status_emoji = "✅" if status == "Running" and "/" in ready else "⚠️"
                    if status in ["CrashLoopBackOff", "Error", "ImagePullBackOff"]:
                        status_emoji = "❌"
                    elif status in ["Pending", "ContainerCreating"]:
                        status_emoji = "⏳"
                    elif status == "Completed":
                        status_emoji = "✔️"
                    
                    formatted.append(f"{status_emoji} **{name}**\n   Status: {status} | Ready: {ready} | Restarts: {restarts} | Age: {age}")
            
            return "\n\n".join(formatted) if formatted else "No resources found"
        
        # For nodes, show compact format
        elif resource_type == "nodes":
            formatted = []
            for line in data_lines:
                parts = line.split()
                if len(parts) >= 5:
                    name = parts[0]
                    status = parts[1]
                    roles = parts[2]
                    age = parts[3]
                    version = parts[4]
                    
                    status_emoji = "✅" if status == "Ready" else "❌"
                    formatted.append(f"{status_emoji} **{name}**\n   Status: {status} | Role: {roles} | Version: {version} | Age: {age}")
            
            return "\n\n".join(formatted) if formatted else "No nodes found"
        
        # For deployments, show compact format
        elif resource_type == "deployments":
            formatted = []
            for line in data_lines:
                parts = line.split()
                if len(parts) >= 4:
                    name = parts[0]
                    ready = parts[1]
                    up_to_date = parts[2]
                    available = parts[3]
                    age = parts[4] if len(parts) > 4 else "N/A"
                    
                    # Check if deployment is healthy
                    status_emoji = "✅" if "/" in ready else "⚠️"
                    try:
                        current, desired = ready.split('/')
                        if current != desired:
                            status_emoji = "⚠️"
                    except:
                        pass
                    
                    formatted.append(f"{status_emoji} **{name}**\n   Ready: {ready} | Up-to-date: {up_to_date} | Available: {available} | Age: {age}")
            
            return "\n\n".join(formatted) if formatted else "No deployments found"
        
        # For services and other resources, use table format but truncate
        else:
            # Keep header and limit column widths
            formatted = [f"```\n{header_line}"]
            for line in data_lines[:20]:  # Limit to 20 rows
                formatted.append(line)
            
            if len(data_lines) > 20:
                formatted.append(f"... and {len(data_lines) - 20} more")
            
            formatted.append("```")
            return "\n".join(formatted)

    async def _run_kubectl_command(self, args: list[str]) -> tuple[bool, str]:
        """
        Run a kubectl command and return the output.
        
        Args:
            args: kubectl command arguments (without 'kubectl' prefix)
            
        Returns:
            Tuple of (success, output)
        """
        try:
            cmd = ["kubectl"] + args
            logger.info("running_kubectl", command=" ".join(cmd))
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                output = stdout.decode('utf-8').strip()
                return True, output
            else:
                error = stderr.decode('utf-8').strip()
                logger.error("kubectl_command_failed", error=error, returncode=process.returncode)
                return False, error
                
        except FileNotFoundError:
            logger.error("kubectl_not_found")
            return False, "kubectl command not found. Please ensure kubectl is installed and in your PATH."
        except Exception as e:
            logger.error("kubectl_command_error", error=str(e))
            return False, f"Error executing kubectl command: {str(e)}"

    def _format_tools_for_prompt(self, tools: list) -> str:
        """
        Format MCP tools for inclusion in AI prompt.
        
        Args:
            tools: List of tool definitions
            
        Returns:
            Formatted string describing available tools
        """
        tool_descriptions = []
        for tool in tools:
            name = tool.get("name", "unknown")
            description = tool.get("description", "No description")
            params = tool.get("inputSchema", {}).get("properties", {})
            server = tool.get("_server", "unknown")
            
            param_list = []
            for param_name, param_info in params.items():
                param_type = param_info.get("type", "any")
                param_desc = param_info.get("description", "")
                param_list.append(f"  - {param_name} ({param_type}): {param_desc}")
            
            params_str = "\n".join(param_list) if param_list else "  No parameters"
            
            tool_descriptions.append(
                f"Tool: {name} (Server: {server})\n"
                f"Description: {description}\n"
                f"Parameters:\n{params_str}"
            )

        return "\n\n".join(tool_descriptions)

    async def _execute_tool_from_text(self, text: str) -> Optional[str]:
        """
        Parse AI response for tool calls and execute them.
        
        Looks for patterns like:
        TOOL_CALL: tool_name(arg1="value1", arg2="value2")
        
        Args:
            text: AI model response text
            
        Returns:
            Tool execution result or None
        """
        import re
        
        pattern = r'TOOL_CALL:\s*(\w+)\((.*?)\)'
        matches = re.findall(pattern, text)
        
        if not matches:
            return None
        
        results = []
        for tool_name, args_str in matches:
            # Parse arguments (simple key=value parsing)
            arguments = {}
            if args_str.strip():
                for arg_pair in args_str.split(','):
                    if '=' in arg_pair:
                        key, value = arg_pair.split('=', 1)
                        key = key.strip()
                        value = value.strip().strip('"\'')
                        arguments[key] = value
            
            # Execute tool via MCP manager
            if not self.mcp_manager:
                continue
            
            logger.info("executing_tool_from_ai_response", tool=tool_name)
            result = await self.mcp_manager.call_tool(tool_name, arguments)
            
            if result and not result.get("isError"):
                # Extract text from content
                content = result.get("content", [])
                if content and len(content) > 0:
                    text_content = content[0].get("text", "")
                    results.append(f"Tool '{tool_name}' result:\n{text_content}")
            else:
                # Handle error
                content = result.get("content", [])
                if content and len(content) > 0:
                    error_text = content[0].get("text", "Unknown error")
                    results.append(f"Tool '{tool_name}' failed: {error_text}")
        
        return "\n\n".join(results) if results else None

    async def handle_message(self, message: ChannelMessage) -> None:
        """
        Handle incoming message from any channel.

        Args:
            message: Incoming channel message
        """
        logger.info(
            "message_received",
            channel_type=message.channel_type,
            user_id=message.user_id,
            content_length=len(message.content),
        )

        # Check for commands
        if message.content.startswith("/"):
            await self._handle_command(message)
            return
        
        # Check if it's a Kubernetes-related query
        if self._is_kubernetes_query(message.content):
            await self._handle_kubernetes_query(message)
            return
        
        # Check if it's a security scanning query
        if self._is_security_query(message.content):
            await self._handle_security_query(message)
            return

        # Process regular message
        await self._process_message(message)

    def _is_kubernetes_query(self, message_text: str) -> bool:
        """Check if message is related to Kubernetes."""
        message_lower = message_text.lower()
        return any(keyword in message_lower for keyword in K8S_KEYWORDS)

    def _is_security_query(self, message_text: str) -> bool:
        """Check if message is related to security scanning/checking."""
        message_lower = message_text.lower()
        return any(keyword in message_lower for keyword in SECURITY_KEYWORDS)

    async def _handle_kubernetes_query(self, message: ChannelMessage) -> None:
        """Handle Kubernetes-related queries."""
        logger.info(
            "kubernetes_query_detected",
            channel_type=message.channel_type,
            user_id=message.user_id,
            query=message.content,
        )
        
        # Parse natural language query
        query_lower = message.content.lower()
        response = None
        
        # Extract namespace if mentioned
        namespace = None
        namespace_patterns = [
            r'(?:in|from|on)\s+(?:the\s+)?([a-z0-9\-]+)(?:\s+namespace)?',
            r'([a-z0-9\-]+)\s+namespace',  # "pos-order4u namespace" - name before "namespace" keyword
            r'namespace\s+([a-z0-9\-]+)',
            r'-n\s+([a-z0-9\-]+)',
        ]
        for pattern in namespace_patterns:
            match = re.search(pattern, query_lower)
            if match:
                namespace = match.group(1)
                # Skip if it's a common kubernetes keyword, not a namespace
                if namespace not in ['pod', 'pods', 'deployment', 'service', 'node', 'container', 'the', 'check', 'show', 'list', 'get', 'and']:
                    break
                namespace = None
        
        # Detect intent and execute appropriate command
        try:
            # List pods
            if any(word in query_lower for word in ['pod', 'pods', 'container', 'containers']):
                if 'log' in query_lower:
                    # Extract pod name
                    pod_match = re.search(r'(?:pod|container)\s+(\S+)', query_lower)
                    if pod_match:
                        pod_name = pod_match.group(1)
                        kubectl_args = ["logs", pod_name]
                        if namespace:
                            kubectl_args.extend(["-n", namespace])
                        else:
                            kubectl_args.extend(["-n", "default"])
                        
                        success, output = await self._run_kubectl_command(kubectl_args)
                        if success:
                            lines = output.split('\n')
                            if len(lines) > 50:
                                output = '\n'.join(lines[-50:]) + f"\n\n(Showing last 50 lines of {len(lines)} total)"
                            response = f"📜 **Logs from pod {pod_name}:**\n\n```\n{output}\n```"
                        else:
                            response = f"❌ Error getting logs: {output}"
                    else:
                        response = "❌ Please specify a pod name. Example: 'show logs from pod nginx-abc123'"
                else:
                    # Detect status filter
                    status_filter = None
                    filter_description = ""
                    
                    if any(word in query_lower for word in ['error', 'errors', 'failed', 'failing', 'crash', 'crashloop', 'crashloopbackoff']):
                        status_filter = "problem"
                        filter_description = " with issues"
                    elif any(word in query_lower for word in ['unhealthy', 'not ready', 'notready']):
                        status_filter = "notready"
                        filter_description = " not ready"
                    elif 'pending' in query_lower:
                        status_filter = "pending"
                        filter_description = " pending"
                    elif any(word in query_lower for word in ['running', 'healthy', 'ready']):
                        status_filter = "running"
                        filter_description = " running"
                    
                    # List pods
                    kubectl_args = ["get", "pods", "-o", "wide"]
                    if namespace:
                        kubectl_args.extend(["-n", namespace])
                    else:
                        kubectl_args.append("--all-namespaces")
                    
                    success, output = await self._run_kubectl_command(kubectl_args)
                    if success:
                        # Apply status filtering if requested
                        if status_filter:
                            lines = output.split('\n')
                            header = lines[0] if lines else ""
                            filtered_lines = [header]
                            
                            for line in lines[1:]:
                                if not line.strip():
                                    continue
                                    
                                if status_filter == "problem":
                                    # Show pods that are not Running or Completed
                                    if any(status in line for status in ['Error', 'CrashLoopBackOff', 'ImagePullBackOff', 'Pending', 'Failed', 'Unknown', 'Terminating', 'ContainerCreating']):
                                        filtered_lines.append(line)
                                    # Also check for Running pods with restarts
                                    elif 'Running' in line:
                                        parts = line.split()
                                        # Check READY column (usually 2nd or 3rd column depending on namespace)
                                        for part in parts:
                                            if '/' in part:
                                                ready, total = part.split('/')
                                                if ready != total:  # Not all containers ready
                                                    filtered_lines.append(line)
                                                    break
                                elif status_filter == "notready":
                                    # Show pods where READY != total or status not Running
                                    if 'Running' not in line or any(status in line for status in ['Pending', 'Error', 'CrashLoop']):
                                        filtered_lines.append(line)
                                    else:
                                        parts = line.split()
                                        for part in parts:
                                            if '/' in part:
                                                ready, total = part.split('/')
                                                if ready != total:
                                                    filtered_lines.append(line)
                                                    break
                                elif status_filter == "pending":
                                    if 'Pending' in line or 'ContainerCreating' in line:
                                        filtered_lines.append(line)
                                elif status_filter == "running":
                                    if 'Running' in line:
                                        # Check if all containers are ready
                                        parts = line.split()
                                        is_healthy = False
                                        for part in parts:
                                            if '/' in part:
                                                ready, total = part.split('/')
                                                if ready == total:
                                                    is_healthy = True
                                                break
                                        if is_healthy:
                                            filtered_lines.append(line)
                            
                            if len(filtered_lines) > 1:
                                output = '\n'.join(filtered_lines)
                                formatted_output = self._format_kubectl_table(output, "pods")
                                response = f"📦 **Pods{filter_description}{f' in namespace {namespace}' if namespace else ' (all namespaces)'}:**\n\n{formatted_output}"
                            else:
                                response = f"✅ **No pods{filter_description} found{f' in namespace {namespace}' if namespace else ' (all namespaces)'}**\n\nAll pods appear to be running normally! 🎉"
                        else:
                            formatted_output = self._format_kubectl_table(output, "pods")
                            response = f"📦 **Pods{f' in namespace {namespace}' if namespace else ' (all namespaces)'}:**\n\n{formatted_output}"
                    else:
                        response = f"❌ Error getting pods: {output}"
            
            # List deployments
            elif any(word in query_lower for word in ['deployment', 'deployments', 'deploy']):
                if 'scale' in query_lower:
                    # Extract deployment name and replica count
                    deploy_match = re.search(r'(?:deployment|deploy)\s+(\S+)', query_lower)
                    replica_match = re.search(r'(?:to\s+)?(\d+)\s+(?:replica|replicas|instance)', query_lower)
                    
                    if deploy_match and replica_match:
                        deployment = deploy_match.group(1)
                        replicas = replica_match.group(1)
                        kubectl_args = ["scale", "deployment", deployment, f"--replicas={replicas}"]
                        if namespace:
                            kubectl_args.extend(["-n", namespace])
                        else:
                            kubectl_args.extend(["-n", "default"])
                        
                        success, output = await self._run_kubectl_command(kubectl_args)
                        if success:
                            response = f"⚖️ **Scaled deployment {deployment} to {replicas} replicas:**\n\n{output}"
                        else:
                            response = f"❌ Error scaling deployment: {output}"
                    else:
                        response = "❌ Please specify deployment name and replica count. Example: 'scale api-server deployment to 3 replicas'"
                else:
                    # List deployments
                    kubectl_args = ["get", "deployments", "-o", "wide"]
                    if namespace:
                        kubectl_args.extend(["-n", namespace])
                    else:
                        kubectl_args.append("--all-namespaces")
                    
                    success, output = await self._run_kubectl_command(kubectl_args)
                    if success:
                        formatted_output = self._format_kubectl_table(output, "deployments")
                        response = f"🚀 **Deployments{f' in namespace {namespace}' if namespace else ' (all namespaces)'}:**\n\n{formatted_output}"
                    else:
                        response = f"❌ Error getting deployments: {output}"
            
            # List services
            elif any(word in query_lower for word in ['service', 'services', 'svc']):
                kubectl_args = ["get", "services", "-o", "wide"]
                if namespace:
                    kubectl_args.extend(["-n", namespace])
                else:
                    kubectl_args.append("--all-namespaces")
                
                success, output = await self._run_kubectl_command(kubectl_args)
                if success:
                    response = f"🌐 **Services{f' in namespace {namespace}' if namespace else ' (all namespaces)'}:**\n\n```\n{output}\n```"
                else:
                    response = f"❌ Error getting services: {output}"
            
            # List nodes
            elif any(word in query_lower for word in ['node', 'nodes', 'cluster']):
                success, output = await self._run_kubectl_command(["get", "nodes", "-o", "wide"])
                if success:
                    response = f"🖥️ **Nodes:**\n\n```\n{output}\n```"
                else:
                    response = f"❌ Error getting nodes: {output}"
            
            # List namespaces
            elif 'namespace' in query_lower and not namespace:
                success, output = await self._run_kubectl_command(["get", "namespaces"])
                if success:
                    response = f"🏢 **Namespaces:**\n\n```\n{output}\n```"
                else:
                    response = f"❌ Error getting namespaces: {output}"
            
            # Show events
            elif any(word in query_lower for word in ['event', 'events', 'what happened', "what's happening"]):
                kubectl_args = ["get", "events"]
                if namespace:
                    kubectl_args.extend(["-n", namespace])
                else:
                    kubectl_args.append("--all-namespaces")
                
                success, output = await self._run_kubectl_command(kubectl_args)
                if success:
                    response = f"📰 **Events{f' in namespace {namespace}' if namespace else ' (all namespaces)'}:**\n\n```\n{output}\n```"
                else:
                    response = f"❌ Error getting events: {output}"
            
            # Default: show help
            else:
                response = """🔧 **Kubernetes Integration**

I couldn't understand your query. Try using `/k8s` commands:

• `/k8s pods [namespace]` - List pods
• `/k8s nodes` - List nodes
• `/k8s deployments [namespace]` - List deployments
• `/k8s services [namespace]` - List services
• `/k8s namespaces` - List namespaces
• `/k8s logs <pod-name> [namespace]` - Get logs
• `/k8s scale <deployment> <replicas> [namespace]` - Scale deployment

**Natural Language Examples:**
• "show me pods in production namespace"
• "show me error pods in pos-order4u"
• "list failed pods"
• "show unhealthy pods in staging"
• "list all deployments"
• "get logs from pod nginx-abc123"
• "scale api-server deployment to 3 replicas"
• "what are my nodes"

**Status Filters:**
• error/failed/crash - Show pods with issues
• unhealthy/not ready - Show pods not ready
• pending - Show pending pods
• running/healthy - Show healthy running pods

Try `/k8s help` for all commands!
"""
        
        except Exception as e:
            logger.error("k8s_query_error", error=str(e), query=message.content)
            response = f"❌ Error processing Kubernetes query: {str(e)}\n\nTry using `/k8s` commands instead. Type `/k8s help` for options."
        
        # Send response
        await self.router.send_message(
            message.channel_type, message.user_id, response
        )

    async def _handle_security_query(self, message: ChannelMessage) -> None:
        """Handle security scanning queries using simplePortChecker MCP server."""
        logger.info(
            "security_query_detected",
            channel_type=message.channel_type,
            user_id=message.user_id,
            query=message.content,
        )
        
        if not self.mcp_manager:
            response = "❌ Security tools are not available. MCP manager not initialized."
            await self.router.send_message(
                message.channel_type, message.user_id, response
            )
            return
        
        query_lower = message.content.lower()
        response = None
        
        try:
            # Get available tools from simplePortChecker
            tools = await self.mcp_manager.list_all_tools()
            security_tools = [t for t in tools if t.get('_server') == 'simplePortChecker']
            
            if not security_tools:
                response = "❌ Security tools not available. SimplePortChecker MCP server may not be connected."
            else:
                # Pattern matching for different security queries
                import re
                
                # 1. Port scanning: "is port 443 open on lobehub.com"
                port_pattern = r'port\s+(\d+)\s+(?:open\s+)?(?:on|at|for)\s+([a-zA-Z0-9\.\-]+)'
                port_match = re.search(port_pattern, query_lower)
                
                # 2. Certificate check: "check certificate for lobehub.com", "ssl cert on example.com"
                cert_pattern = r'(?:check|analyze|verify)?\s*(?:ssl|tls|https)?\s*(?:cert|certificate)\s+(?:for|on|of)?\s+([a-zA-Z0-9\.\-]+)'
                cert_match = re.search(cert_pattern, query_lower)
                
                # 3. WAF/CDN detection: "check waf on example.com", "detect cdn for site.com"
                waf_pattern = r'(?:check|detect)?\s*(?:waf|cdn|cloudflare|protection|firewall)\s+(?:for|on)?\s+([a-zA-Z0-9\.\-]+)'
                waf_match = re.search(waf_pattern, query_lower)
                
                # 4. mTLS check: "check mtls on api.example.com"
                mtls_pattern = r'(?:check|verify)?\s*mtls\s+(?:for|on)?\s+([a-zA-Z0-9\.\-]+)'
                mtls_match = re.search(mtls_pattern, query_lower)
                
                # 5. Security headers: "check security headers for example.com"
                headers_pattern = r'(?:check|scan)?\s*(?:security\s+)?headers\s+(?:for|on)?\s+([a-zA-Z0-9\.\-]+)'
                headers_match = re.search(headers_pattern, query_lower)
                
                # 6. OWASP scan: "scan owasp vulnerabilities on example.com"
                owasp_pattern = r'(?:scan|check)?\s*owasp\s+(?:vulnerabilities)?\s+(?:for|on)?\s+([a-zA-Z0-9\.\-]+)'
                owasp_match = re.search(owasp_pattern, query_lower)
                
                # 7. Full security scan: "full security scan on example.com", "security assessment for site.com"
                full_scan_pattern = r'(?:full|complete|comprehensive)?\s*security\s+(?:scan|assessment|check)\s+(?:for|on)?\s+([a-zA-Z0-9\.\-]+)'
                full_scan_match = re.search(full_scan_pattern, query_lower)
                
                # 8. Extract just a hostname for general security info
                host_pattern = r'(?:for|on|of|at)\s+([a-zA-Z0-9\.\-]+)'
                host_match = re.search(host_pattern, query_lower)
                
                # Route to appropriate tool
                if port_match:
                    port = port_match.group(1)
                    host = port_match.group(2)
                    logger.info("calling_security_tool", tool="scan_ports", host=host, port=port)
                    result = await self.mcp_manager.call_tool(
                        "scan_ports",
                        {"target": host, "ports": [int(port)]}
                    )
                    response = self._format_tool_result(result, "🔌 Port Scan", host)
                    
                elif cert_match:
                    host = cert_match.group(1)
                    logger.info("calling_security_tool", tool="analyze_certificate", host=host)
                    result = await self.mcp_manager.call_tool(
                        "analyze_certificate",
                        {"target": host}
                    )
                    response = self._format_tool_result(result, "🔒 Certificate Analysis", host)
                    
                elif waf_match:
                    host = waf_match.group(1)
                    logger.info("calling_security_tool", tool="detect_l7_protection", host=host)
                    result = await self.mcp_manager.call_tool(
                        "detect_l7_protection",
                        {"target": host}
                    )
                    response = self._format_tool_result(result, "🛡️ WAF/CDN Detection", host)
                    
                elif mtls_match:
                    host = mtls_match.group(1)
                    logger.info("calling_security_tool", tool="check_mtls", host=host)
                    result = await self.mcp_manager.call_tool(
                        "check_mtls",
                        {"target": host}
                    )
                    response = self._format_tool_result(result, "🔐 mTLS Check", host)
                    
                elif headers_match:
                    host = headers_match.group(1)
                    logger.info("calling_security_tool", tool="check_security_headers", host=host)
                    result = await self.mcp_manager.call_tool(
                        "check_security_headers",
                        {"target": host}
                    )
                    response = self._format_tool_result(result, "📋 Security Headers", host)
                    
                elif owasp_match:
                    host = owasp_match.group(1)
                    logger.info("calling_security_tool", tool="scan_owasp_vulnerabilities", host=host)
                    result = await self.mcp_manager.call_tool(
                        "scan_owasp_vulnerabilities",
                        {"target": host}
                    )
                    response = self._format_tool_result(result, "🔍 OWASP Vulnerability Scan", host)
                    
                elif full_scan_match:
                    host = full_scan_match.group(1)
                    logger.info("calling_security_tool", tool="full_security_scan", host=host)
                    result = await self.mcp_manager.call_tool(
                        "full_security_scan",
                        {"target": host}
                    )
                    response = self._format_tool_result(result, "🔎 Full Security Assessment", host)
                    
                else:
                    # Show help with all available tools
                    tool_names = [t.get('name', 'Unknown') for t in security_tools]
                    response = f"""🔧 **Security Tools Available**

I have {len(security_tools)} security tools from SimplePortChecker:

**Port Scanning:**
• "is port 443 open on example.com"
• "scan ports on example.com"

**Certificate Analysis:**
• "check certificate for example.com"
• "analyze ssl cert on example.com"

**WAF/CDN Detection:**
• "detect waf on example.com"
• "check cloudflare protection for site.com"

**mTLS Verification:**
• "check mtls on api.example.com"

**Security Headers:**
• "check security headers for example.com"
• "scan headers on site.com"

**OWASP Scanning:**
• "scan owasp vulnerabilities on example.com"

**Full Security Assessment:**
• "full security scan on example.com"
• "comprehensive security assessment for site.com"

**Available Tools:** {', '.join(tool_names)}"""
                    
        except Exception as e:
            logger.error("security_query_error", error=str(e))
            response = f"❌ Error executing security scan: {str(e)}"
        
        # Send response
        if response:
            await self.router.send_message(
                message.channel_type, message.user_id, response
            )
    
    def _format_tool_result(self, result: dict, title: str, target: str) -> str:
        """Format tool execution result for display."""
        if result and not result.get("isError"):
            content = result.get("content", [])
            if content and len(content) > 0:
                result_text = content[0].get("text", "No result")
                return f"{title}\n\n**Target:** {target}\n\n{result_text}"
            return f"✅ {title} completed for {target} (no detailed output)"
        else:
            content = result.get("content", [])
            if content and len(content) > 0:
                error_text = content[0].get("text", "Unknown error")
                return f"❌ **{title} Failed**\n\n{error_text}"
            return f"❌ Error executing {title} on {target}"

    async def _handle_command(self, message: ChannelMessage) -> None:
        """Handle command messages."""
        command_parts = message.content.split()
        command = command_parts[0].lower()
        
        logger.info("command_received", command=command, parts=command_parts)

        async with get_db_session() as db_session:
            session_mgr = SessionManager(RedisCache(get_redis()), db_session)
            session_data = await session_mgr.get_or_create_session(
                message.channel_type, message.user_id, message.username
            )

            if command == "/help":
                response = PromptManager.get_command_help()

            elif command == "/reset":
                await session_mgr.clear_session(message.channel_type, message.user_id)
                response = "Conversation reset! Starting fresh."

            elif command == "/status":
                context_builder = ContextBuilder(db_session)
                stats = await context_builder.get_message_stats(
                    uuid.UUID(session_data.conversation_id)
                )
                model_selector = ModelSelector(db_session)
                current_model = await model_selector.select_model(
                    uuid.UUID(session_data.user_id),
                    uuid.UUID(session_data.conversation_id),
                    message.channel_type,
                )
                response = f"""📊 Status:
Model: {current_model}
Messages: {stats['message_count']}
Tokens: {stats['total_tokens']}"""

            elif command == "/model":
                if len(command_parts) < 2:
                    response = "Usage: /model <gpt-4|claude-3-opus|llama-3-70b>"
                else:
                    new_model = command_parts[1]
                    if self.ai_client.is_model_supported(new_model):
                        model_selector = ModelSelector(db_session)
                        await model_selector.set_user_model(
                            uuid.UUID(session_data.user_id), new_model
                        )
                        response = f"Model set to: {new_model}"
                    else:
                        supported = ", ".join(self.ai_client.list_supported_models())
                        response = f"Unsupported model. Available: {supported}"

            elif command == "/k8s":
                logger.info("k8s_command_received", args=command_parts[1:])
                try:
                    response = await self._handle_k8s_command(command_parts[1:] if len(command_parts) > 1 else [])
                    logger.info("k8s_command_processed", response_length=len(response))
                except Exception as e:
                    logger.error("k8s_command_failed", error=str(e), error_type=type(e).__name__)
                    response = f"Error processing Kubernetes command: {str(e)}"

            else:
                response = "Unknown command. Try /help"

            # Send response
            await self.router.send_message(
                message.channel_type, message.user_id, response
            )

    async def _handle_k8s_command(self, args: list[str]) -> str:
        """
        Handle Kubernetes commands.
        
        Args:
            args: Command arguments (everything after /k8s)
            
        Returns:
            Response message
        """
        if not args or args[0] == "help":
            return """🔧 Kubernetes Commands

Pod Management:
• /k8s pods - List all pods
• /k8s pods <namespace> - List pods in namespace
• /k8s describe pod <name> [namespace] - Get pod details
• /k8s logs <pod-name> [namespace] - Get pod logs
• /k8s top pods - Show pod resource usage

Deployment Management:
• /k8s deployments [namespace] - List deployments
• /k8s scale <deployment> <replicas> [namespace] - Scale deployment
• /k8s rollout status <deployment> [namespace] - Check rollout status

Service Management:
• /k8s services [namespace] - List services
• /k8s endpoints [namespace] - List endpoints

Node Management:
• /k8s nodes - List nodes
• /k8s top nodes - Show node resource usage
• /k8s describe node <name> - Get node details

Namespace Management:
• /k8s namespaces - List all namespaces

Helm:
• /k8s helm list - List Helm releases
• /k8s helm status <release> - Get Helm release status

Events & Logs:
• /k8s events [namespace] - Show recent events
• /k8s logs <pod> [namespace] - Get pod logs

Configuration:
• /k8s contexts - List available contexts
• /k8s config - View current configuration

Examples:
  /k8s pods production
  /k8s logs nginx-abc123 production
  /k8s scale api-server 5 production
  /k8s nodes
  /k8s deployments

Note: Kubernetes MCP tools are integrated. You can manage your cluster directly from this chat!
"""
        
        subcommand = args[0].lower()
        
        try:
            # Handle different subcommands with kubectl
            if subcommand == "pods":
                namespace = args[1] if len(args) > 1 else None
                logger.info("k8s_listing_pods", namespace=namespace)
                
                kubectl_args = ["get", "pods"]
                if namespace:
                    kubectl_args.extend(["-n", namespace])
                else:
                    kubectl_args.append("--all-namespaces")
                
                success, output = await self._run_kubectl_command(kubectl_args)
                if success:
                    formatted_output = self._format_kubectl_table(output, "pods")
                    return f"📦 **Pods{f' in namespace {namespace}' if namespace else ' (all namespaces)'}:**\n\n{formatted_output}"
                else:
                    return f"❌ Error getting pods: {output}"
            
            elif subcommand == "nodes":
                logger.info("k8s_listing_nodes")
                success, output = await self._run_kubectl_command(["get", "nodes"])
                if success:
                    formatted_output = self._format_kubectl_table(output, "nodes")
                    return f"🖥️ **Nodes:**\n\n{formatted_output}"
                else:
                    return f"❌ Error getting nodes: {output}"
            
            elif subcommand == "namespaces":
                logger.info("k8s_listing_namespaces")
                success, output = await self._run_kubectl_command(["get", "namespaces"])
                if success:
                    return f"🏢 **Namespaces:**\n\n```\n{output}\n```"
                else:
                    return f"❌ Error getting namespaces: {output}"
            
            elif subcommand == "deployments":
                namespace = args[1] if len(args) > 1 else None
                logger.info("k8s_listing_deployments", namespace=namespace)
                kubectl_args = ["get", "deployments"]
                if namespace:
                    kubectl_args.extend(["-n", namespace])
                else:
                    kubectl_args.append("--all-namespaces")
                success, output = await self._run_kubectl_command(kubectl_args)
                if success:
                    formatted_output = self._format_kubectl_table(output, "deployments")
                    return f"🚀 **Deployments{f' in namespace {namespace}' if namespace else ' (all namespaces)'}:**\n\n{formatted_output}"
                else:
                    return f"❌ Error getting deployments: {output}"
            
            elif subcommand == "services":
                namespace = args[1] if len(args) > 1 else None
                logger.info("k8s_listing_services", namespace=namespace)
                kubectl_args = ["get", "services"]
                if namespace:
                    kubectl_args.extend(["-n", namespace])
                else:
                    kubectl_args.append("--all-namespaces")
                success, output = await self._run_kubectl_command(kubectl_args)
                if success:
                    return f"🌐 **Services{f' in namespace {namespace}' if namespace else ' (all namespaces)'}:**\n\n```\n{output}\n```"
                else:
                    return f"❌ Error getting services: {output}"
            
            elif subcommand == "contexts":
                logger.info("k8s_listing_contexts")
                success, output = await self._run_kubectl_command(["config", "get-contexts"])
                if success:
                    return f"🔧 **Contexts:**\n\n```\n{output}\n```"
                else:
                    return f"❌ Error getting contexts: {output}"
            
            elif subcommand == "logs":
                if len(args) < 2:
                    return "❌ Usage: /k8s logs <pod-name> [namespace]"
                pod_name = args[1]
                namespace = args[2] if len(args) > 2 else "default"
                logger.info("k8s_getting_logs", pod=pod_name, namespace=namespace)
                success, output = await self._run_kubectl_command(["logs", pod_name, "-n", namespace])
                if success:
                    # Limit log output to last 50 lines for readability
                    lines = output.split('\n')
                    if len(lines) > 50:
                        output = '\n'.join(lines[-50:]) + f"\n\n(Showing last 50 lines of {len(lines)} total)"
                    return f"📜 **Logs from pod {pod_name} in namespace {namespace}:**\n\n```\n{output}\n```"
                else:
                    return f"❌ Error getting logs: {output}"
            
            elif subcommand == "scale":
                if len(args) < 3:
                    return "❌ Usage: /k8s scale <deployment> <replicas> [namespace]"
                deployment = args[1]
                replicas = args[2]
                namespace = args[3] if len(args) > 3 else "default"
                logger.info("k8s_scaling_deployment", deployment=deployment, replicas=replicas, namespace=namespace)
                success, output = await self._run_kubectl_command([
                    "scale", "deployment", deployment,
                    f"--replicas={replicas}",
                    "-n", namespace
                ])
                if success:
                    return f"⚖️ **Scaling deployment {deployment} to {replicas} replicas in namespace {namespace}:**\n\n{output}"
                else:
                    return f"❌ Error scaling deployment: {output}"
            
            elif subcommand == "events":
                namespace = args[1] if len(args) > 1 else None
                logger.info("k8s_listing_events", namespace=namespace)
                kubectl_args = ["get", "events"]
                if namespace:
                    kubectl_args.extend(["-n", namespace])
                else:
                    kubectl_args.append("--all-namespaces")
                success, output = await self._run_kubectl_command(kubectl_args)
                if success:
                    return f"📰 **Events{f' in namespace {namespace}' if namespace else ' (all namespaces)'}:**\n\n```\n{output}\n```"
                else:
                    return f"❌ Error getting events: {output}"
            
            elif subcommand == "describe":
                if len(args) < 3:
                    return "❌ Usage: /k8s describe <resource-type> <name> [namespace]"
                resource_type = args[1]
                name = args[2]
                namespace = args[3] if len(args) > 3 else "default"
                logger.info("k8s_describe", resource_type=resource_type, name=name, namespace=namespace)
                
                kubectl_args = ["describe", resource_type, name]
                # Don't add namespace for cluster-scoped resources like nodes
                if resource_type.lower() not in ["node", "nodes", "namespace", "namespaces"]:
                    kubectl_args.extend(["-n", namespace])
                
                success, output = await self._run_kubectl_command(kubectl_args)
                if success:
                    return f"🔍 **{resource_type} {name}:**\n\n```\n{output}\n```"
                else:
                    return f"❌ Error describing {resource_type}: {output}"
            
            elif subcommand == "helm":
                if len(args) < 2:
                    return "❌ Usage: /k8s helm <list|status|...> [args...]"
                helm_command = args[1]
                logger.info("k8s_helm_command", command=helm_command)
                
                if helm_command == "list":
                    success, output = await self._run_kubectl_command(["get", "all", "-A", "-l", "app.kubernetes.io/managed-by=Helm"])
                    if success:
                        return f"⎈ **Helm-managed Resources:**\n\n```\n{output}\n```\n\n_Note: For full Helm functionality, install helm CLI and use: helm list --all-namespaces_"
                    else:
                        return f"❌ Error listing Helm resources: {output}"
                else:
                    return f"⎈ Helm command '{helm_command}' requires helm CLI. This bot focuses on kubectl commands.\n\nFor Helm: install helm and run: `helm {helm_command}`"
            
            elif subcommand == "top":
                if len(args) < 2:
                    return "❌ Usage: /k8s top <pods|nodes> [namespace]"
                resource = args[1]
                logger.info("k8s_top", resource=resource)
                
                kubectl_args = ["top", resource]
                if resource == "pods" and len(args) > 2:
                    kubectl_args.extend(["-n", args[2]])
                elif resource == "pods":
                    kubectl_args.append("--all-namespaces")
                
                success, output = await self._run_kubectl_command(kubectl_args)
                if success:
                    namespace_info = f" in namespace {args[2]}" if resource == "pods" and len(args) > 2 else ""
                    return f"📊 **{resource.capitalize()} Resource Usage{namespace_info}:**\n\n```\n{output}\n```"
                else:
                    if "metrics-server" in output.lower():
                        return f"❌ Metrics Server not available. Install it with:\n```\nkubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml\n```"
                    return f"❌ Error getting resource usage: {output}"
            
            elif subcommand == "config":
                logger.info("k8s_viewing_config")
                success, output = await self._run_kubectl_command(["config", "view"])
                if success:
                    # Limit output for security - don't show full config in chat
                    lines = output.split('\n')[:20]
                    truncated = '\n'.join(lines)
                    return f"📋 **Kubernetes Configuration (first 20 lines):**\n\n```yaml\n{truncated}\n...\n```\n\n_For full config, use: kubectl config view_"
                else:
                    return f"❌ Error viewing config: {output}"
            
            else:
                return f"❌ Unknown Kubernetes command: {subcommand}\n\nTry `/k8s help` for available commands."
        
        except Exception as e:
            logger.error("k8s_command_error", error=str(e), subcommand=subcommand)
            return f"❌ Error executing Kubernetes command: {str(e)}\n\nPlease check your cluster configuration and try again."

    async def _process_message(self, message: ChannelMessage) -> None:
        """Process regular message and generate AI response."""
        try:
            async with get_db_session() as db_session:
                # Initialize managers
                redis_cache = RedisCache(get_redis())
                session_mgr = SessionManager(redis_cache, db_session)
                context_builder = ContextBuilder(db_session)
                model_selector = ModelSelector(db_session)

                # Get or create session
                session_data = await session_mgr.get_or_create_session(
                    message.channel_type, message.user_id, message.username
                )

                conversation_id = uuid.UUID(session_data.conversation_id)
                user_id = uuid.UUID(session_data.user_id)

                # Add user message to database
                await context_builder.add_user_message(
                    conversation_id, message.content
                )

                # Build conversation context
                system_prompt = PromptManager.get_system_prompt(message.channel_type)
                
                # Add MCP tools to system prompt if available
                if self.mcp_manager:
                    try:
                        tools = await self.mcp_manager.list_all_tools()
                        if tools:
                            tools_description = self._format_tools_for_prompt(tools)
                            system_prompt += f"\n\nAvailable Custom Tools:\n{tools_description}\n\nTo use a tool, include in your response: TOOL_CALL: tool_name(arg1=\"value1\", arg2=\"value2\")"
                    except Exception as e:
                        logger.warning("failed_to_get_mcp_tools", error=str(e))
                
                context = await context_builder.build_context(
                    conversation_id, system_prompt=system_prompt
                )

                # Select model
                model = await model_selector.select_model(
                    user_id, conversation_id, message.channel_type
                )

                # Generate AI response
                logger.info(
                    "generating_ai_response",
                    model=model,
                    conversation_id=str(conversation_id),
                )

                response_content, token_count = await self.ai_client.generate_response(
                    messages=context, model=model
                )

                # Check if AI wants to execute an MCP tool
                if self.mcp_manager and "TOOL_CALL:" in response_content:
                    logger.info("ai_requested_tool_execution")
                    try:
                        tool_result = await self._execute_tool_from_text(response_content)
                        if tool_result:
                            # Add tool result to the response
                            response_content = f"{response_content}\n\n{tool_result}"
                            logger.info("tool_execution_successful")
                    except Exception as e:
                        logger.error("tool_execution_failed", error=str(e))
                        response_content += "\n\n(Note: Tool execution failed)"

                # Save assistant message
                await context_builder.add_assistant_message(
                    conversation_id,
                    response_content,
                    model_used=model,
                    token_count=token_count,
                )

                # Update session activity
                await session_mgr.update_session_activity(
                    message.channel_type, message.user_id
                )
                await session_mgr.increment_message_count(
                    message.channel_type, message.user_id
                )

                # Send response through channel
                await self.router.send_message(
                    message.channel_type, message.user_id, response_content
                )

                logger.info(
                    "message_processed_successfully",
                    conversation_id=str(conversation_id),
                    model=model,
                    tokens=token_count,
                )

        except Exception as e:
            logger.error(
                "message_processing_failed",
                error=str(e),
                error_type=type(e).__name__,
                channel_type=message.channel_type,
                user_id=message.user_id,
            )

            # Send error message to user
            error_message = "Sorry, I encountered an error processing your message. Please try again."
            await self.router.send_message(
                message.channel_type, message.user_id, error_message
            )
