"""MCP (Model Context Protocol) client for custom business logic integration."""

import asyncio
import json
import os
from typing import Any, Dict, List, Optional

import structlog

from src.config import get_settings
from src.mcp.base_transport import BaseMCPTransport

logger = structlog.get_logger()
settings = get_settings()


class MCPClient(BaseMCPTransport):
    """
    Client for interacting with MCP (Model Context Protocol) servers via stdio.
    
    MCP allows the AI agent to interact with external tools and business logic
    in a standardized way using JSON-RPC 2.0 over stdin/stdout.
    """

    def __init__(
        self,
        server_command: Optional[List[str]] = None,
        env: Optional[Dict[str, str]] = None
    ):
        """
        Initialize MCP client.
        
        Args:
            server_command: Command to start the MCP server (e.g., ['python', 'scripts/mcp_server.py'])
            env: Environment variables for the server process
        """
        self.server_command = server_command or self._get_default_server_command()
        self.env = env or {}
        self.process: Optional[asyncio.subprocess.Process] = None
        self._request_id = 0
        self._available_tools: Optional[List[Dict[str, Any]]] = None
        self._initialized = False
        logger.info("mcp_client_initialized", command=self.server_command)

    def _get_default_server_command(self) -> List[str]:
        """Get the default MCP server command."""
        # Get the project root directory
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        venv_python = os.path.join(project_root, '.venv', 'bin', 'python')
        server_script = os.path.join(project_root, 'scripts', 'mcp_server.py')
        
        # Use venv python if it exists, otherwise use system python
        python_cmd = venv_python if os.path.exists(venv_python) else 'python3'
        
        return [python_cmd, server_script]

    async def start(self) -> bool:
        """
        Start the MCP server process.
        
        Returns:
            True if started successfully
        """
        if self.process is not None:
            logger.warning("mcp_server_already_running")
            return True

        try:
            logger.info("starting_mcp_server", command=self.server_command)
            
            # Prepare environment variables
            env = os.environ.copy()
            env.update(self.env)
            
            self.process = await asyncio.create_subprocess_exec(
                *self.server_command,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env
            )
            
            # Initialize the server
            await self._initialize_server()
            
            logger.info("mcp_server_started")
            return True
            
        except Exception as e:
            logger.error("failed_to_start_mcp_server", error=str(e))
            return False

    async def _initialize_server(self):
        """Send initialize request to the MCP server."""
        init_response = await self._send_request(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {
                    "name": "simple-ai-agent",
                    "version": "1.0.0"
                }
            }
        )
        
        if init_response and "result" in init_response:
            self._initialized = True
            logger.info("mcp_server_initialized", server_info=init_response["result"].get("serverInfo"))
        else:
            raise Exception("Failed to initialize MCP server")

    async def _send_request(self, method: str, params: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """
        Send a JSON-RPC request to the MCP server.
        
        Args:
            method: JSON-RPC method name
            params: Method parameters
            
        Returns:
            JSON-RPC response or None if failed
        """
        if self.process is None or self.process.stdin is None or self.process.stdout is None:
            logger.error("mcp_server_not_started")
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
            # Send request
            request_json = json.dumps(request) + "\n"
            self.process.stdin.write(request_json.encode())
            await self.process.stdin.drain()
            
            logger.debug("sent_request", method=method, id=self._request_id)
            
            # Read response
            response_line = await self.process.stdout.readline()
            if not response_line:
                logger.error("no_response_from_server", method=method)
                return None
            
            response = json.loads(response_line.decode())
            logger.debug("received_response", method=method, id=response.get("id"))
            
            return response
            
        except Exception as e:
            logger.error("mcp_request_failed", method=method, error=str(e))
            return None

    async def list_tools(self) -> List[Dict[str, Any]]:
        """
        List available tools from the MCP server.
        
        Returns:
            List of tool definitions with name, description, and parameters
        """
        if self._available_tools is not None:
            return self._available_tools

        if not self._initialized:
            if not await self.start():
                return []

        try:
            response = await self._send_request("tools/list")
            
            if response and "result" in response:
                self._available_tools = response["result"].get("tools", [])
                if self._available_tools:
                    logger.info("mcp_tools_listed", count=len(self._available_tools))
                    return self._available_tools
                else:
                    logger.warning("mcp_tools_list_empty")
                    return []
            else:
                logger.warning("mcp_tools_list_empty")
                return []

        except Exception as e:
            logger.error(
                "mcp_list_tools_error",
                error=str(e),
                error_type=type(e).__name__,
            )
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
            arguments: Tool arguments as a dictionary
            
        Returns:
            Tool execution result
        """
        if not self._initialized:
            if not await self.start():
                return {
                    "content": [{
                        "type": "text",
                        "text": "Error: MCP server not initialized"
                    }],
                    "isError": True
                }

        try:
            logger.info("mcp_calling_tool", tool=tool_name, args=arguments)

            response = await self._send_request(
                "tools/call",
                {"name": tool_name, "arguments": arguments or {}}
            )

            if response and "result" in response:
                logger.info("mcp_tool_called_successfully", tool=tool_name)
                return response["result"]
            elif response and "error" in response:
                error = response["error"]
                logger.error(
                    "mcp_tool_error",
                    tool=tool_name,
                    error=error,
                )
                return {
                    "content": [{
                        "type": "text",
                        "text": f"Error: {error.get('message', 'Unknown error')}"
                    }],
                    "isError": True
                }
            else:
                logger.warning("mcp_tool_unexpected_response", tool=tool_name)
                return {
                    "content": [{
                        "type": "text",
                        "text": "Error: Unexpected response from server"
                    }],
                    "isError": True
                }

        except Exception as e:
            logger.error(
                "mcp_call_tool_error",
                tool=tool_name,
                error=str(e),
                error_type=type(e).__name__,
            )
            return {
                "content": [{
                    "type": "text",
                    "text": f"Error calling tool: {str(e)}"
                }],
                "isError": True
            }

    async def get_resources(self) -> List[Dict[str, Any]]:
        """
        Get available resources from the MCP server.
        
        Resources are data sources that the AI can access (files, databases, etc.)
        
        Returns:
            List of available resources
        """
        if not self._initialized:
            if not await self.start():
                return []

        try:
            response = await self._send_request("resources/list")

            if response and "result" in response:
                resources = response["result"].get("resources", [])
                logger.info("mcp_resources_listed", count=len(resources))
                return resources
            else:
                return []

        except Exception as e:
            logger.error(
                "mcp_list_resources_error",
                error=str(e),
                error_type=type(e).__name__,
            )
            return []

    async def read_resource(self, resource_uri: str) -> Optional[str]:
        """
        Read a resource from the MCP server.
        
        Args:
            resource_uri: URI of the resource to read
            
        Returns:
            Resource content or None if failed
        """
        if not self._initialized:
            if not await self.start():
                return None

        try:
            response = await self._send_request(
                "resources/read",
                {"uri": resource_uri}
            )

            if response and "result" in response:
                content = response["result"].get("contents", [])
                if content:
                    return content[0].get("text", "")
                return None
            else:
                return None

        except Exception as e:
            logger.error(
                "mcp_read_resource_error",
                uri=resource_uri,
                error=str(e),
                error_type=type(e).__name__,
            )
            return None

    async def get_tools_for_prompt(self) -> str:
        """
        Get a formatted description of available tools for inclusion in prompts.
        
        Returns:
            Formatted string describing available tools
        """
        tools = await self.list_tools()
        if not tools:
            return "No custom tools available."

        tool_descriptions = []
        for tool in tools:
            name = tool.get("name", "unknown")
            description = tool.get("description", "No description")
            params = tool.get("inputSchema", {}).get("properties", {})
            
            param_list = []
            for param_name, param_info in params.items():
                param_type = param_info.get("type", "any")
                param_desc = param_info.get("description", "")
                param_list.append(f"  - {param_name} ({param_type}): {param_desc}")
            
            params_str = "\n".join(param_list) if param_list else "  No parameters"
            
            tool_descriptions.append(
                f"Tool: {name}\n"
                f"Description: {description}\n"
                f"Parameters:\n{params_str}"
            )

        return "\n\n".join(tool_descriptions)

    # BaseMCPTransport interface implementation
    
    async def stop(self):
        """Stop the MCP server (alias for close)."""
        await self.close()

    async def send_request(
        self,
        method: str,
        params: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Send a JSON-RPC request (public interface).
        
        Args:
            method: JSON-RPC method name
            params: Method parameters
            
        Returns:
            JSON-RPC response or None if failed
        """
        return await self._send_request(method, params)

    async def initialize(self, client_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Initialize the MCP connection.
        
        Args:
            client_info: Client information
            
        Returns:
            Server information and capabilities
        """
        if self.process is None:
            await self.start()
        
        if not self._initialized:
            await self._initialize_server()
        
        # Return server info (stored during initialization)
        return {
            "serverInfo": {
                "name": "kubernetes-mcp-server",
                "version": "1.0.0"
            },
            "capabilities": {
                "tools": {}
            }
        }

    def is_connected(self) -> bool:
        """Check if transport is connected."""
        return self.process is not None and self._initialized

    async def close(self) -> None:
        """Close the MCP server process."""
        if self.process is not None:
            try:
                if self.process.stdin:
                    self.process.stdin.close()
                
                # Wait for process to terminate (with timeout)
                try:
                    await asyncio.wait_for(self.process.wait(), timeout=5.0)
                except asyncio.TimeoutError:
                    logger.warning("mcp_server_timeout_killing")
                    self.process.kill()
                    await self.process.wait()
                
                logger.info("mcp_server_closed")
            except Exception as e:
                logger.error("error_closing_mcp_server", error=str(e))
            finally:
                self.process = None
                self._initialized = False


class MCPToolExecutor:
    """
    Helper class to execute MCP tools based on AI model decisions.
    
    This class helps parse AI responses and execute appropriate MCP tools.
    """

    def __init__(self, mcp_client: MCPClient):
        self.mcp_client = mcp_client

    async def execute_from_text(self, text: str) -> Optional[str]:
        """
        Parse AI response for tool calls and execute them.
        
        Looks for patterns like:
        TOOL_CALL: tool_name(arg1="value1", arg2="value2")
        
        Args:
            text: AI model response text
            
        Returns:
            Tool execution result or None
        """
        # Simple pattern matching for tool calls
        # In production, you'd use a more robust parser
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
            
            # Execute tool
            logger.info("executing_tool_from_ai_response", tool=tool_name)
            result = await self.mcp_client.call_tool(tool_name, arguments)
            
            if result:
                results.append(f"Tool {tool_name} result: {json.dumps(result)}")
        
        return "\n".join(results) if results else None
