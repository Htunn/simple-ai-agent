"""
SSE (Server-Sent Events) transport for MCP servers.

This module implements MCP communication over HTTP with SSE for responses.
Used for cloud-based MCP servers that expose HTTP endpoints.
"""

import asyncio
import json
from typing import Any, Dict, List, Optional
import structlog
import httpx

from src.mcp.base_transport import BaseMCPTransport

logger = structlog.get_logger()


class SSETransport(BaseMCPTransport):
    """
    Handles MCP communication over HTTP with SSE.
    
    Protocol:
    - Send requests via HTTP POST
    - Receive responses via Server-Sent Events (SSE)
    - Maintains persistent HTTP connection for streaming
    """

    def __init__(self, url: str, api_key: Optional[str] = None):
        """
        Initialize SSE transport.
        
        Args:
            url: Base URL of the MCP server
            api_key: Optional API key for authentication
        """
        self.url = url.rstrip('/')
        self.api_key = api_key
        self.client: Optional[httpx.AsyncClient] = None
        self._request_id = 0
        self._initialized = False
        self._server_info: Optional[Dict[str, Any]] = None
        logger.info("sse_transport_initialized", url=self.url)

    async def start(self) -> bool:
        """Start the SSE transport connection."""
        try:
            # Create HTTP client with extended timeout for SSE
            headers = {
                "Accept": "application/json, text/event-stream",
                "Content-Type": "application/json"
            }
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            
            self.client = httpx.AsyncClient(
                timeout=httpx.Timeout(30.0, read=300.0),  # Long read timeout for SSE
                headers=headers,
                follow_redirects=True
            )
            
            logger.info("sse_transport_started", url=self.url)
            return True
            
        except Exception as e:
            logger.error("sse_transport_start_failed", error=str(e))
            return False

    async def stop(self):
        """Stop the SSE transport."""
        if self.client:
            await self.client.aclose()
            self.client = None
        self._initialized = False
        logger.info("sse_transport_stopped")

    async def send_request(
        self,
        method: str,
        params: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Send a JSON-RPC request via HTTP POST.
        
        Args:
            method: JSON-RPC method name
            params: Method parameters
            
        Returns:
            JSON-RPC response or None if failed
        """
        if not self.client:
            logger.error("sse_transport_not_started")
            return None

        self._request_id += 1
        request = {
            "jsonrpc": "2.0",
            "id": self._request_id,
            "method": method
        }
        
        if params is not None:
            request["params"] = params

        try:
            logger.debug("sending_sse_request", method=method, url=self.url)
            
            # Send request via POST
            # Headers are already set in the client, but we can override if needed
            response = await self.client.post(
                self.url,
                json=request
            )
            
            response.raise_for_status()
            
            # Parse SSE response format (event: message\ndata: {...})
            # SSE may return multiple messages (notifications + result)
            # We need to find the message with matching request ID
            response_text = response.text
            result = None
            
            # SSE responses have lines like:
            # event: message
            # data: {"jsonrpc": "2.0", ...}
            import json
            for line in response_text.split('\n'):
                line = line.strip()
                if line.startswith('data: '):
                    json_str = line[6:]  # Remove 'data: ' prefix
                    try:
                        message = json.loads(json_str)
                        # Check if this message has our request ID (it's the result)
                        if message.get("id") == self._request_id:
                            result = message
                            break
                        # If no ID, it might be a notification - keep looking
                    except json.JSONDecodeError:
                        logger.warning("sse_invalid_json_line", line=json_str[:100])
                        continue
            
            if result is None:
                logger.error("sse_no_matching_response", request_id=self._request_id, response_text=response_text[:500])
                return None
            
            logger.debug("received_sse_response", method=method, has_result="result" in result)
            
            return result
            
        except httpx.HTTPStatusError as e:
            logger.error("sse_request_http_error", method=method, status=e.response.status_code, error=str(e))
            return None
        except Exception as e:
            logger.error("sse_request_failed", method=method, error=str(e), error_type=type(e).__name__)
            return None

    async def initialize(self, client_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Initialize the MCP connection.
        
        Args:
            client_info: Client information
            
        Returns:
            Server information and capabilities
        """
        response = await self.send_request(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": client_info
            }
        )
        
        if response and "result" in response:
            self._initialized = True
            self._server_info = response["result"]
            server_info = self._server_info.get("serverInfo") if self._server_info else None
            logger.info("sse_server_initialized", server_info=server_info)
            return self._server_info if self._server_info else {}
        else:
            raise Exception("Failed to initialize SSE MCP server")

    async def list_tools(self) -> List[Dict[str, Any]]:
        """
        List available tools from the MCP server.
        
        Returns:
            List of tool definitions
        """
        if not self._initialized:
            raise Exception("SSE transport not initialized")

        response = await self.send_request("tools/list", {})
        
        if response and "result" in response and "tools" in response["result"]:
            tools = response["result"]["tools"]
            logger.info("sse_tools_listed", count=len(tools))
            return tools
        
        logger.warning("sse_no_tools_found")
        return []

    async def call_tool(
        self,
        tool_name: str,
        arguments: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Call a tool on the MCP server.
        
        Args:
            tool_name: Name of the tool to call
            arguments: Tool arguments
            
        Returns:
            Tool execution result
        """
        if not self._initialized:
            raise Exception("SSE transport not initialized")

        response = await self.send_request(
            "tools/call",
            {
                "name": tool_name,
                "arguments": arguments or {}
            }
        )
        
        if response and "result" in response:
            logger.debug("sse_tool_called", tool=tool_name, success=True)
            return response["result"]
        elif response and "error" in response:
            error = response["error"]
            logger.error("sse_tool_failed", tool=tool_name, error=error.get("message"))
            return {
                "content": [{
                    "type": "text",
                    "text": f"Error: {error.get('message', 'Unknown error')}"
                }],
                "isError": True
            }
        else:
            logger.error("sse_tool_no_response", tool=tool_name)
            return {
                "content": [{
                    "type": "text",
                    "text": "Error: No response from server"
                }],
                "isError": True
            }

    def is_connected(self) -> bool:
        """Check if transport is connected."""
        return self.client is not None and self._initialized
