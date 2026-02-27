"""MCP Tools Registry - Manages native and HTTP-based MCP tools."""

from typing import Any, Callable, Dict, Optional

import structlog

logger = structlog.get_logger()


class MCPToolsRegistry:
    """
    Registry for MCP tools that can be invoked from the message handler.
    
    This class manages both native VS Code MCP tools and HTTP-based MCP tools.
    """

    def __init__(self):
        self.tools: Dict[str, Callable] = {}
        self._registered_prefixes = []

    def register_tool(self, name: str, tool_func: Callable):
        """Register a single MCP tool."""
        self.tools[name] = tool_func
        logger.debug("mcp_tool_registered", name=name)

    def register_kubernetes_tools(self, tool_search_func: Callable):
        """
        Register Kubernetes MCP tools dynamically.
        
        Args:
            tool_search_func: Function to search and load tools
        """
        # Load all Kubernetes MCP tools
        k8s_patterns = [
            'mcp_kubernetes_pods',
            'mcp_kubernetes_resources',
            'mcp_kubernetes_namespaces',
            'mcp_kubernetes_nodes',
            'mcp_kubernetes_helm',
            'mcp_kubernetes_events',
            'mcp_kubernetes_configuration',
        ]
        
        for pattern in k8s_patterns:
            try:
                # Use tool_search to find and register these tools
                logger.info("loading_k8s_tools", pattern=pattern)
                # Tools will be loaded via the tool_search mechanism
                self._registered_prefixes.append(pattern)
            except Exception as e:
                logger.warning("failed_to_load_k8s_tools", pattern=pattern, error=str(e))

    def get_tool(self, name: str) -> Optional[Callable]:
        """Get a tool by name."""
        return self.tools.get(name)

    def has_kubernetes_tools(self) -> bool:
        """Check if Kubernetes tools are available."""
        return any(name.startswith('mcp_kubernetes_') for name in self.tools.keys())

    def list_tools(self) -> list[str]:
        """List all registered tool names."""
        return list(self.tools.keys())

    def get_kubernetes_tools(self) -> Dict[str, Callable]:
        """Get all Kubernetes-related tools."""
        return {
            name: func
            for name, func in self.tools.items()
            if name.startswith('mcp_kubernetes_')
        }


# Global registry instance
_registry = MCPToolsRegistry()


def get_mcp_registry() -> MCPToolsRegistry:
    """Get the global MCP tools registry."""
    return _registry
