"""
Base transport interface for MCP servers.

This module defines the abstract base class for MCP transports,
supporting multiple communication protocols (stdio, SSE, WebSocket, etc.).
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class BaseMCPTransport(ABC):
    """
    Abstract base class for MCP transports.
    
    Implementations handle different communication protocols:
    - StdioTransport: JSON-RPC over stdin/stdout (subprocess)
    - SSETransport: Server-Sent Events over HTTP
    - WebSocketTransport: WebSocket connections (future)
    """

    @abstractmethod
    async def start(self) -> bool:
        """
        Start the transport connection.
        
        Returns:
            True if started successfully
        """
        pass

    @abstractmethod
    async def stop(self):
        """Stop the transport connection."""
        pass

    @abstractmethod
    async def send_request(
        self,
        method: str,
        params: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Send a JSON-RPC request.
        
        Args:
            method: JSON-RPC method name
            params: Method parameters
            
        Returns:
            JSON-RPC response or None if failed
        """
        pass

    @abstractmethod
    async def initialize(self, client_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Initialize the MCP connection.
        
        Args:
            client_info: Client information (name, version)
            
        Returns:
            Server information and capabilities
        """
        pass

    @abstractmethod
    async def list_tools(self) -> List[Dict[str, Any]]:
        """
        List available tools.
        
        Returns:
            List of tool definitions
        """
        pass

    @abstractmethod
    async def call_tool(
        self,
        tool_name: str,
        arguments: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Call a tool with arguments.
        
        Args:
            tool_name: Name of the tool to call
            arguments: Tool arguments
            
        Returns:
            Tool execution result
        """
        pass

    @abstractmethod
    def is_connected(self) -> bool:
        """
        Check if transport is connected.
        
        Returns:
            True if connected and ready
        """
        pass
