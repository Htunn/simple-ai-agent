"""
MCP Manager - Manages multiple MCP servers with different transports.

This module handles initialization, lifecycle, and routing for multiple
MCP servers (stdio-based, SSE-based, etc.).
"""

import asyncio
import json
import os
from typing import Any, Dict, List, Optional

import structlog

from src.config import get_settings
from src.mcp.base_transport import BaseMCPTransport
from src.mcp.sse_transport import SSETransport

logger = structlog.get_logger()
settings = get_settings()


class MCPManager:
    """
    Manages multiple MCP servers with different transport protocols.
    
    Supports:
    - stdio: subprocess-based servers (e.g., Kubernetes)
    - SSE: HTTP-based servers with Server-Sent Events
    - Future: WebSocket, gRPC, etc.
    """

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize MCP manager.
        
        Args:
            config_path: Path to .mcp-config.json file
        """
        self.config_path = config_path or self._get_default_config_path()
        self.servers: Dict[str, BaseMCPTransport] = {}
        self.server_configs: Dict[str, Dict[str, Any]] = {}
        self.tool_registry: Dict[str, str] = {}  # tool_name -> server_name
        logger.info("mcp_manager_initialized", config_path=self.config_path)

    def _get_default_config_path(self) -> str:
        """Get the default MCP configuration file path."""
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        return os.path.join(project_root, '.mcp-config.json')

    async def start(self) -> bool:
        """
        Start all configured MCP servers.
        
        Returns:
            True if at least one server started successfully
        """
        try:
            # Load configuration
            if not os.path.exists(self.config_path):
                logger.warning("mcp_config_not_found", path=self.config_path)
                return False

            with open(self.config_path, 'r') as f:
                config = json.load(f)

            mcp_servers = config.get('mcpServers', {})
            global_env = config.get('env', {})

            if not mcp_servers:
                logger.warning("no_mcp_servers_configured")
                return False

            # Initialize each server
            success_count = 0
            for server_name, server_config in mcp_servers.items():
                try:
                    if await self._start_server(server_name, server_config, global_env):
                        success_count += 1
                except Exception as e:
                    logger.error("server_start_failed", server=server_name, error=str(e))

            logger.info("mcp_manager_started", servers=success_count, total=len(mcp_servers))
            return success_count > 0

        except Exception as e:
            logger.error("mcp_manager_start_failed", error=str(e))
            return False

    async def _start_server(
        self,
        server_name: str,
        server_config: Dict[str, Any],
        global_env: Dict[str, str]
    ) -> bool:
        """
        Start a single MCP server.
        
        Args:
            server_name: Name of the server
            server_config: Server configuration
            global_env: Global environment variables
            
        Returns:
            True if started successfully
        """
        server_type = server_config.get('type', 'stdio')  # Default to stdio for backwards compatibility
        
        logger.info("starting_mcp_server", server=server_name, type=server_type)

        # Create appropriate transport
        if server_type == 'sse':
            transport = await self._create_sse_transport(server_name, server_config)
        elif server_type == 'stdio':
            transport = await self._create_stdio_transport(server_name, server_config, global_env)
        else:
            logger.error("unsupported_server_type", server=server_name, type=server_type)
            return False

        if not transport:
            return False

        # Initialize the server
        try:
            await transport.initialize({
                "name": "simple-ai-agent",
                "version": "1.0.0"
            })

            # Register tools
            tools = await transport.list_tools()
            for tool in tools:
                tool_name = tool.get('name')
                if tool_name:
                    self.tool_registry[tool_name] = server_name
                    logger.debug("tool_registered", tool=tool_name, server=server_name)

            self.servers[server_name] = transport
            self.server_configs[server_name] = server_config
            
            logger.info("mcp_server_started", server=server_name, tools=len(tools))
            return True

        except Exception as e:
            logger.error("server_initialization_failed", server=server_name, error=str(e))
            return False

    async def _create_sse_transport(
        self,
        server_name: str,
        server_config: Dict[str, Any]
    ) -> Optional[BaseMCPTransport]:
        """Create and start an SSE transport."""
        url = server_config.get('url')
        if not url:
            logger.error("sse_server_missing_url", server=server_name)
            return None

        api_key = server_config.get('apiKey') or server_config.get('api_key')
        
        transport = SSETransport(url, api_key)
        if await transport.start():
            return transport
        
        return None

    async def _create_stdio_transport(
        self,
        server_name: str,
        server_config: Dict[str, Any],
        global_env: Dict[str, str]
    ) -> Optional[BaseMCPTransport]:
        """Create and start a stdio transport."""
        # Import here to avoid circular dependency
        from src.services.mcp_client import MCPClient
        
        command = server_config.get('command')
        args = server_config.get('args', [])
        
        if not command:
            logger.error("stdio_server_missing_command", server=server_name)
            return None

        # Merge environment variables
        env = {**global_env, **server_config.get('env', {})}
        
        # Create MCPClient (it already implements the stdio transport)
        client = MCPClient(
            server_command=[command] + args,
            env=env
        )
        
        if await client.start():
            return client
        
        return None

    async def stop(self):
        """Stop all MCP servers."""
        logger.info("stopping_mcp_servers", count=len(self.servers))
        
        for server_name, transport in self.servers.items():
            try:
                await transport.stop()
                logger.debug("mcp_server_stopped", server=server_name)
            except Exception as e:
                logger.error("server_stop_failed", server=server_name, error=str(e))
        
        self.servers.clear()
        self.tool_registry.clear()
        logger.info("mcp_manager_stopped")

    async def call_tool(
        self,
        tool_name: str,
        arguments: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Call a tool by name, routing to the appropriate server.
        
        Args:
            tool_name: Name of the tool to call
            arguments: Tool arguments
            
        Returns:
            Tool execution result
        """
        # Find which server has this tool
        server_name = self.tool_registry.get(tool_name)
        if not server_name:
            logger.error("tool_not_found", tool=tool_name)
            return {
                "content": [{
                    "type": "text",
                    "text": f"Error: Tool '{tool_name}' not found"
                }],
                "isError": True
            }

        transport = self.servers.get(server_name)
        if not transport:
            logger.error("server_not_found", server=server_name, tool=tool_name)
            return {
                "content": [{
                    "type": "text",
                    "text": f"Error: Server '{server_name}' not available"
                }],
                "isError": True
            }

        try:
            result = await transport.call_tool(tool_name, arguments)
            logger.debug("tool_called", tool=tool_name, server=server_name, success=True)
            return result
        except Exception as e:
            logger.error("tool_call_failed", tool=tool_name, server=server_name, error=str(e))
            return {
                "content": [{
                    "type": "text",
                    "text": f"Error calling tool: {str(e)}"
                }],
                "isError": True
            }

    async def list_all_tools(self) -> List[Dict[str, Any]]:
        """
        List all tools from all servers.
        
        Returns:
            List of tool definitions with server information
        """
        all_tools = []
        
        for server_name, transport in self.servers.items():
            try:
                tools = await transport.list_tools()
                for tool in tools:
                    tool['_server'] = server_name  # Add server information
                    all_tools.append(tool)
            except Exception as e:
                logger.error("failed_to_list_tools", server=server_name, error=str(e))
        
        logger.debug("listed_all_tools", count=len(all_tools), servers=len(self.servers))
        return all_tools

    def get_server_info(self) -> Dict[str, Any]:
        """
        Get information about all connected servers.
        
        Returns:
            Dictionary with server status and capabilities
        """
        info = {
            "servers": {},
            "total_tools": len(self.tool_registry),
            "connected_servers": len(self.servers)
        }
        
        for server_name, transport in self.servers.items():
            info["servers"][server_name] = {
                "type": self.server_configs.get(server_name, {}).get("type", "stdio"),
                "connected": transport.is_connected(),
                "tools": [name for name, server in self.tool_registry.items() if server == server_name]
            }
        
        return info
