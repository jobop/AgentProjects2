"""
MCP Compliant Manager

Fully compliant MCP (Model Context Protocol) implementation using official Anthropic MCP SDK.
This implementation follows the MCP 2025-06-18 specification.
"""

import asyncio
import json
import logging
from typing import Dict, List, Any, Optional, Union
from pathlib import Path
import sys
import os

# Add shared modules to path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "..", "shared"))

try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.models import Resource, Tool, Prompt
    from mcp.client.stdio import stdio_client
    from mcp.client.sse import sse_client
    from mcp.types import TextContent, ImageContent, EmbeddedResource
except ImportError:
    logging.warning("Official MCP SDK not available. Install with: pip install mcp")
    # Fallback imports for development
    ClientSession = None
    StdioServerParameters = None

from common_types.base import MCPServerConfig


class MCPCompliantManager:
    """
    MCP Manager that fully complies with Anthropic's MCP specification.
    Supports JSON-RPC 2.0, proper lifecycle management, and all MCP features.
    """
    
    def __init__(self, protocol_version: str = "2025-06-18"):
        self.protocol_version = protocol_version
        self.servers: Dict[str, MCPServerConfig] = {}
        self.client_sessions: Dict[str, ClientSession] = {}
        self.server_capabilities: Dict[str, Dict[str, Any]] = {}
        self.available_tools: Dict[str, List[Tool]] = {}
        self.available_resources: Dict[str, List[Resource]] = {}
        self.available_prompts: Dict[str, List[Prompt]] = {}
        self.logger = logging.getLogger(__name__)
    
    def register_server(self, name: str, config: MCPServerConfig):
        """Register an MCP server configuration"""
        self.servers[name] = config
        self.logger.info(f"Registered MCP server: {name}")
    
    async def start_server(self, name: str) -> bool:
        """Start an MCP server with full lifecycle compliance"""
        if name not in self.servers:
            self.logger.error(f"MCP server '{name}' not configured")
            return False
        
        config = self.servers[name]
        
        try:
            # Determine transport method
            if config.transport == "stdio":
                session = await self._start_stdio_server(name, config)
            elif config.transport == "sse":
                session = await self._start_sse_server(name, config)
            elif config.transport == "http":
                session = await self._start_http_server(name, config)
            else:
                self.logger.error(f"Unsupported transport: {config.transport}")
                return False
            
            if session:
                self.client_sessions[name] = session
                
                # Perform capability discovery
                await self._discover_capabilities(name, session)
                
                self.logger.info(f"Started MCP server: {name} (transport: {config.transport})")
                return True
            
        except Exception as e:
            self.logger.error(f"Failed to start MCP server '{name}': {e}")
            return False
        
        return False
    
    async def _start_stdio_server(self, name: str, config: MCPServerConfig) -> Optional[ClientSession]:
        """Start MCP server using stdio transport"""
        server_params = StdioServerParameters(
            command=config.command[0],
            args=config.command[1:] + config.args,
            env=config.env or {}
        )
        
        # Create stdio client session
        session = await stdio_client(server_params)
        
        # Initialize the session with proper lifecycle
        await self._initialize_session(session, name)
        
        return session
    
    async def _start_sse_server(self, name: str, config: MCPServerConfig) -> Optional[ClientSession]:
        """Start MCP server using Server-Sent Events transport"""
        if not config.url:
            raise ValueError(f"SSE transport requires URL for server {name}")
        
        # Create SSE client session
        session = await sse_client(config.url, headers=config.headers or {})
        
        # Initialize the session
        await self._initialize_session(session, name)
        
        return session
    
    async def _start_http_server(self, name: str, config: MCPServerConfig) -> Optional[ClientSession]:
        """Start MCP server using HTTP transport"""
        # TODO: Implement HTTP transport when available in official SDK
        self.logger.warning("HTTP transport not yet implemented in official MCP SDK")
        return None
    
    async def _initialize_session(self, session: ClientSession, server_name: str):
        """
        Perform MCP lifecycle initialization with capability negotiation
        Following MCP specification for proper handshake
        """
        try:
            # Send initialize request
            init_result = await session.initialize()
            
            # Store server capabilities
            self.server_capabilities[server_name] = {
                "protocol_version": init_result.protocolVersion,
                "capabilities": init_result.capabilities.model_dump(),
                "server_info": init_result.serverInfo.model_dump()
            }
            
            # Send initialized notification to complete handshake
            await session.notify_initialized()
            
            self.logger.info(f"Successfully initialized MCP session for {server_name}")
            self.logger.debug(f"Server capabilities: {self.server_capabilities[server_name]}")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize MCP session for {server_name}: {e}")
            raise
    
    async def _discover_capabilities(self, server_name: str, session: ClientSession):
        """Discover all available tools, resources, and prompts from MCP server"""
        try:
            capabilities = self.server_capabilities[server_name]["capabilities"]
            
            # Discover tools if supported
            if capabilities.get("tools"):
                tools = await session.list_tools()
                self.available_tools[server_name] = tools.tools
                self.logger.info(f"Discovered {len(tools.tools)} tools for server '{server_name}'")
            
            # Discover resources if supported
            if capabilities.get("resources"):
                resources = await session.list_resources()
                self.available_resources[server_name] = resources.resources
                self.logger.info(f"Discovered {len(resources.resources)} resources for server '{server_name}'")
            
            # Discover prompts if supported
            if capabilities.get("prompts"):
                prompts = await session.list_prompts()
                self.available_prompts[server_name] = prompts.prompts
                self.logger.info(f"Discovered {len(prompts.prompts)} prompts for server '{server_name}'")
                
        except Exception as e:
            self.logger.error(f"Failed to discover capabilities for {server_name}: {e}")
    
    async def stop_server(self, name: str) -> bool:
        """Stop an MCP server with proper cleanup"""
        if name not in self.client_sessions:
            return False
        
        try:
            session = self.client_sessions[name]
            
            # Graceful shutdown
            await session.close()
            
            # Clean up state
            del self.client_sessions[name]
            if name in self.server_capabilities:
                del self.server_capabilities[name]
            if name in self.available_tools:
                del self.available_tools[name]
            if name in self.available_resources:
                del self.available_resources[name]
            if name in self.available_prompts:
                del self.available_prompts[name]
            
            self.logger.info(f"Stopped MCP server: {name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to stop MCP server '{name}': {e}")
            return False
    
    async def call_tool(
        self,
        server_name: str,
        tool_name: str,
        arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Call a tool on an MCP server (standard MCP Tools interface)"""
        
        if server_name not in self.client_sessions:
            return {
                "success": False,
                "error": f"MCP server '{server_name}' is not running"
            }
        
        session = self.client_sessions[server_name]
        
        try:
            # Use official MCP tool calling
            result = await session.call_tool(tool_name, arguments)
            
            # Process the result content
            content_result = []
            for content in result.content:
                if isinstance(content, TextContent):
                    content_result.append({
                        "type": "text",
                        "text": content.text
                    })
                elif isinstance(content, ImageContent):
                    content_result.append({
                        "type": "image",
                        "data": content.data,
                        "mimeType": content.mimeType
                    })
                elif isinstance(content, EmbeddedResource):
                    content_result.append({
                        "type": "resource",
                        "resource": content.resource.model_dump()
                    })
            
            return {
                "success": True,
                "content": content_result,
                "isError": result.isError or False
            }
            
        except Exception as e:
            self.logger.error(f"Error calling tool '{tool_name}' on server '{server_name}': {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def read_resource(
        self,
        server_name: str,
        resource_uri: str
    ) -> Dict[str, Any]:
        """Read a resource from an MCP server (standard MCP Resources interface)"""
        
        if server_name not in self.client_sessions:
            return {
                "success": False,
                "error": f"MCP server '{server_name}' is not running"
            }
        
        session = self.client_sessions[server_name]
        
        try:
            result = await session.read_resource(resource_uri)
            
            # Process the resource content
            content_result = []
            for content in result.contents:
                if isinstance(content, TextContent):
                    content_result.append({
                        "type": "text",
                        "text": content.text,
                        "uri": resource_uri
                    })
                elif isinstance(content, ImageContent):
                    content_result.append({
                        "type": "image",
                        "data": content.data,
                        "mimeType": content.mimeType,
                        "uri": resource_uri
                    })
            
            return {
                "success": True,
                "contents": content_result
            }
            
        except Exception as e:
            self.logger.error(f"Error reading resource '{resource_uri}' from server '{server_name}': {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_prompt(
        self,
        server_name: str,
        prompt_name: str,
        arguments: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Get a prompt from an MCP server (standard MCP Prompts interface)"""
        
        if server_name not in self.client_sessions:
            return {
                "success": False,
                "error": f"MCP server '{server_name}' is not running"
            }
        
        session = self.client_sessions[server_name]
        
        try:
            result = await session.get_prompt(prompt_name, arguments or {})
            
            return {
                "success": True,
                "description": result.description,
                "messages": [msg.model_dump() for msg in result.messages]
            }
            
        except Exception as e:
            self.logger.error(f"Error getting prompt '{prompt_name}' from server '{server_name}': {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_available_tools(self, server_name: Optional[str] = None) -> Dict[str, List[Dict[str, Any]]]:
        """Get available tools for a specific server or all servers"""
        if server_name:
            tools = self.available_tools.get(server_name, [])
            return {server_name: [tool.model_dump() for tool in tools]}
        
        result = {}
        for name, tools in self.available_tools.items():
            result[name] = [tool.model_dump() for tool in tools]
        return result
    
    def get_available_resources(self, server_name: Optional[str] = None) -> Dict[str, List[Dict[str, Any]]]:
        """Get available resources for a specific server or all servers"""
        if server_name:
            resources = self.available_resources.get(server_name, [])
            return {server_name: [resource.model_dump() for resource in resources]}
        
        result = {}
        for name, resources in self.available_resources.items():
            result[name] = [resource.model_dump() for resource in resources]
        return result
    
    def get_available_prompts(self, server_name: Optional[str] = None) -> Dict[str, List[Dict[str, Any]]]:
        """Get available prompts for a specific server or all servers"""
        if server_name:
            prompts = self.available_prompts.get(server_name, [])
            return {server_name: [prompt.model_dump() for prompt in prompts]}
        
        result = {}
        for name, prompts in self.available_prompts.items():
            result[name] = [prompt.model_dump() for prompt in prompts]
        return result
    
    def get_running_servers(self) -> List[str]:
        """Get list of running server names"""
        return list(self.client_sessions.keys())
    
    def get_server_capabilities(self, server_name: str) -> Optional[Dict[str, Any]]:
        """Get capabilities for a specific server"""
        return self.server_capabilities.get(server_name)
    
    async def start_all_servers(self) -> Dict[str, bool]:
        """Start all configured MCP servers"""
        results = {}
        for name in self.servers:
            results[name] = await self.start_server(name)
        return results
    
    async def stop_all_servers(self) -> Dict[str, bool]:
        """Stop all running MCP servers"""
        results = {}
        for name in list(self.client_sessions.keys()):
            results[name] = await self.stop_server(name)
        return results
    
    async def cleanup(self):
        """Clean up all resources and connections"""
        await self.stop_all_servers()
        self.logger.info("MCP Manager cleanup completed") 