"""
Kubernetes MCP Server - stdio-based MCP server for Kubernetes operations.

This server implements the MCP specification for Kubernetes management,
providing tools to interact with Kubernetes clusters via kubectl.
"""

import asyncio
import json
import logging
import os
import sys
from typing import Any, Dict, List, Optional

import structlog

from src.mcp.stdio_transport import StdioTransport

# Configure logging to stderr only (stdout is for JSON-RPC)
logging.basicConfig(
    format="%(message)s",
    stream=sys.stderr,
    level=logging.INFO
)

structlog.configure(
    processors=[
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer(colors=False),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(file=sys.stderr),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


class KubernetesMCPServer:
    """
    MCP Server for Kubernetes operations.
    
    Implements the Model Context Protocol for Kubernetes management,
    exposing kubectl operations as MCP tools.
    
    Protocol methods:
    - initialize: Initialize the server
    - tools/list: List available tools
    - tools/call: Execute a tool
    """

    def __init__(self):
        """Initialize the Kubernetes MCP server."""
        self.server_info = {
            "name": "kubernetes-mcp-server",
            "version": "1.0.0"
        }
        self.capabilities = {
            "tools": {}
        }
        self.transport = StdioTransport()
        self.initialized = False
        
        # Tool definitions following MCP specification
        self.tools = self._define_tools()
        
        logger.info("kubernetes_mcp_server_initialized", tools_count=len(self.tools))

    def _define_tools(self) -> List[Dict[str, Any]]:
        """
        Define available Kubernetes tools with their schemas.
        
        Returns:
            List of tool definitions with inputSchema
        """
        return [
            {
                "name": "k8s_get_pods",
                "description": "List pods in a Kubernetes namespace",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "namespace": {
                            "type": "string",
                            "description": "Kubernetes namespace (default: current context namespace)"
                        },
                        "label_selector": {
                            "type": "string",
                            "description": "Label selector to filter pods"
                        }
                    }
                }
            },
            {
                "name": "k8s_get_nodes",
                "description": "List all nodes in the Kubernetes cluster",
                "inputSchema": {
                    "type": "object",
                    "properties": {}
                }
            },
            {
                "name": "k8s_get_deployments",
                "description": "List deployments in a namespace",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "namespace": {
                            "type": "string",
                            "description": "Kubernetes namespace"
                        }
                    }
                }
            },
            {
                "name": "k8s_get_services",
                "description": "List services in a namespace",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "namespace": {
                            "type": "string",
                            "description": "Kubernetes namespace"
                        }
                    }
                }
            },
            {
                "name": "k8s_get_namespaces",
                "description": "List all namespaces in the cluster",
                "inputSchema": {
                    "type": "object",
                    "properties": {}
                }
            },
            {
                "name": "k8s_get_logs",
                "description": "Get logs from a pod",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "pod_name": {
                            "type": "string",
                            "description": "Name of the pod"
                        },
                        "namespace": {
                            "type": "string",
                            "description": "Namespace of the pod"
                        },
                        "container": {
                            "type": "string",
                            "description": "Container name (optional)"
                        },
                        "tail_lines": {
                            "type": "integer",
                            "description": "Number of lines to tail (default: 50)"
                        }
                    },
                    "required": ["pod_name"]
                }
            },
            {
                "name": "k8s_scale_deployment",
                "description": "Scale a deployment",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "deployment": {
                            "type": "string",
                            "description": "Deployment name"
                        },
                        "replicas": {
                            "type": "integer",
                            "description": "Number of replicas"
                        },
                        "namespace": {
                            "type": "string",
                            "description": "Namespace"
                        }
                    },
                    "required": ["deployment", "replicas"]
                }
            },
            {
                "name": "k8s_describe_resource",
                "description": "Describe a Kubernetes resource",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "resource_type": {
                            "type": "string",
                            "description": "Resource type (pod, deployment, service, etc.)"
                        },
                        "resource_name": {
                            "type": "string",
                            "description": "Resource name"
                        },
                        "namespace": {
                            "type": "string",
                            "description": "Namespace"
                        }
                    },
                    "required": ["resource_type", "resource_name"]
                }
            },
            {
                "name": "k8s_get_events",
                "description": "Get events in a namespace",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "namespace": {
                            "type": "string",
                            "description": "Namespace"
                        }
                    }
                }
            },
            {
                "name": "k8s_top_pods",
                "description": "Show resource usage for pods",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "namespace": {
                            "type": "string",
                            "description": "Namespace"
                        }
                    }
                }
            },
            {
                "name": "k8s_top_nodes",
                "description": "Show resource usage for nodes",
                "inputSchema": {
                    "type": "object",
                    "properties": {}
                }
            },
            {
                "name": "k8s_get_contexts",
                "description": "List available kubectl contexts",
                "inputSchema": {
                    "type": "object",
                    "properties": {}
                }
            },
            {
                "name": "k8s_current_context",
                "description": "Get the current kubectl context",
                "inputSchema": {
                    "type": "object",
                    "properties": {}
                }
            }
        ]

    async def start(self):
        """Start the MCP server on stdio."""
        logger.info("starting_kubernetes_mcp_server")
        await self.transport.start(self._handle_request)

    async def _handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle incoming JSON-RPC requests.
        
        Args:
            request: JSON-RPC request object
            
        Returns:
            JSON-RPC response object
        """
        method = request.get("method")
        params = request.get("params", {})
        request_id = request.get("id")

        logger.debug("handling_request", method=method, id=request_id)

        try:
            if method == "initialize":
                result = await self._handle_initialize(params)
            elif method == "tools/list":
                result = await self._handle_tools_list()
            elif method == "tools/call":
                result = await self._handle_tools_call(params)
            else:
                return self._create_error_response(
                    request_id,
                    -32601,
                    f"Method not found: {method}"
                )

            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": result
            }

        except Exception as e:
            logger.error("request_handling_error", method=method, error=str(e))
            return self._create_error_response(
                request_id,
                -32603,
                "Internal error",
                str(e)
            )

    async def _handle_initialize(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle initialize request.
        
        Args:
            params: Initialize parameters
            
        Returns:
            Server info and capabilities
        """
        self.initialized = True
        logger.info("server_initialized", client_info=params.get("clientInfo"))
        
        return {
            "protocolVersion": "2024-11-05",
            "capabilities": self.capabilities,
            "serverInfo": self.server_info
        }

    async def _handle_tools_list(self) -> Dict[str, Any]:
        """
        Handle tools/list request.
        
        Returns:
            List of available tools
        """
        logger.debug("listing_tools", count=len(self.tools))
        return {"tools": self.tools}

    async def _handle_tools_call(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle tools/call request.
        
        Args:
            params: Tool call parameters with 'name' and 'arguments'
            
        Returns:
            Tool execution result
        """
        tool_name = params.get("name")
        arguments = params.get("arguments", {})

        logger.info("calling_tool", tool=tool_name, args=arguments)

        # Route to appropriate tool handler
        handler_map: Dict[str, Any] = {
            "k8s_get_pods": self._kubectl_get_pods,
            "k8s_get_nodes": self._kubectl_get_nodes,
            "k8s_get_deployments": self._kubectl_get_deployments,
            "k8s_get_services": self._kubectl_get_services,
            "k8s_get_namespaces": self._kubectl_get_namespaces,
            "k8s_get_logs": self._kubectl_get_logs,
            "k8s_scale_deployment": self._kubectl_scale_deployment,
            "k8s_describe_resource": self._kubectl_describe_resource,
            "k8s_get_events": self._kubectl_get_events,
            "k8s_top_pods": self._kubectl_top_pods,
            "k8s_top_nodes": self._kubectl_top_nodes,
            "k8s_get_contexts": self._kubectl_get_contexts,
            "k8s_current_context": self._kubectl_current_context,
        }

        if not tool_name or tool_name not in handler_map:
            raise ValueError(f"Unknown tool: {tool_name}")
        
        handler = handler_map[tool_name]

        result = await handler(arguments)
        
        return {
            "content": [
                {
                    "type": "text",
                    "text": result
                }
            ]
        }

    async def _run_kubectl(self, args: List[str]) -> str:
        """
        Execute a kubectl command.
        
        Args:
            args: kubectl command arguments
            
        Returns:
            Command output
        """
        try:
            cmd = ["kubectl"] + args
            logger.debug("executing_kubectl", args=args)
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                error_msg = stderr.decode().strip()
                logger.error("kubectl_error", args=args, error=error_msg)
                return f"Error: {error_msg}"
            
            output = stdout.decode().strip()
            logger.debug("kubectl_success", args=args, output_length=len(output))
            return output
            
        except Exception as e:
            logger.error("kubectl_execution_error", error=str(e))
            return f"Error executing kubectl: {str(e)}"

    # Tool implementations
    
    async def _kubectl_get_pods(self, args: Dict[str, Any]) -> str:
        """Get pods in a namespace."""
        namespace = args.get("namespace", "default")
        label_selector = args.get("label_selector")
        
        cmd_args = ["get", "pods", "-n", namespace]
        if label_selector:
            cmd_args.extend(["-l", label_selector])
        
        return await self._run_kubectl(cmd_args)

    async def _kubectl_get_nodes(self, args: Dict[str, Any]) -> str:
        """Get all nodes."""
        return await self._run_kubectl(["get", "nodes"])

    async def _kubectl_get_deployments(self, args: Dict[str, Any]) -> str:
        """Get deployments in a namespace."""
        namespace = args.get("namespace", "default")
        return await self._run_kubectl(["get", "deployments", "-n", namespace])

    async def _kubectl_get_services(self, args: Dict[str, Any]) -> str:
        """Get services in a namespace."""
        namespace = args.get("namespace", "default")
        return await self._run_kubectl(["get", "services", "-n", namespace])

    async def _kubectl_get_namespaces(self, args: Dict[str, Any]) -> str:
        """Get all namespaces."""
        return await self._run_kubectl(["get", "namespaces"])

    async def _kubectl_get_logs(self, args: Dict[str, Any]) -> str:
        """Get logs from a pod."""
        pod_name = args["pod_name"]
        namespace = args.get("namespace", "default")
        container = args.get("container")
        tail_lines = args.get("tail_lines", 50)
        
        cmd_args = ["logs", pod_name, "-n", namespace, "--tail", str(tail_lines)]
        if container:
            cmd_args.extend(["-c", container])
        
        return await self._run_kubectl(cmd_args)

    async def _kubectl_scale_deployment(self, args: Dict[str, Any]) -> str:
        """Scale a deployment."""
        deployment = args["deployment"]
        replicas = args["replicas"]
        namespace = args.get("namespace", "default")
        
        return await self._run_kubectl([
            "scale", "deployment", deployment,
            "--replicas", str(replicas),
            "-n", namespace
        ])

    async def _kubectl_describe_resource(self, args: Dict[str, Any]) -> str:
        """Describe a Kubernetes resource."""
        resource_type = args["resource_type"]
        resource_name = args["resource_name"]
        namespace = args.get("namespace")
        
        cmd_args = ["describe", resource_type, resource_name]
        if namespace:
            cmd_args.extend(["-n", namespace])
        
        return await self._run_kubectl(cmd_args)

    async def _kubectl_get_events(self, args: Dict[str, Any]) -> str:
        """Get events in a namespace."""
        namespace = args.get("namespace", "default")
        return await self._run_kubectl(["get", "events", "-n", namespace])

    async def _kubectl_top_pods(self, args: Dict[str, Any]) -> str:
        """Show resource usage for pods."""
        namespace = args.get("namespace", "default")
        return await self._run_kubectl(["top", "pods", "-n", namespace])

    async def _kubectl_top_nodes(self, args: Dict[str, Any]) -> str:
        """Show resource usage for nodes."""
        return await self._run_kubectl(["top", "nodes"])

    async def _kubectl_get_contexts(self, args: Dict[str, Any]) -> str:
        """List kubectl contexts."""
        return await self._run_kubectl(["config", "get-contexts"])

    async def _kubectl_current_context(self, args: Dict[str, Any]) -> str:
        """Get current kubectl context."""
        return await self._run_kubectl(["config", "current-context"])

    def _create_error_response(
        self,
        request_id: Any,
        code: int,
        message: str,
        data: Optional[Any] = None
    ) -> Dict[str, Any]:
        """Create a JSON-RPC error response."""
        response = {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {
                "code": code,
                "message": message
            }
        }
        
        if data is not None:
            response["error"]["data"] = data
            
        return response


async def main():
    """Main entry point for the MCP server."""
    server = KubernetesMCPServer()
    await server.start()


if __name__ == "__main__":
    asyncio.run(main())
