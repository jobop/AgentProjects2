"""
MCP Compliant Client

Client implementation that fully complies with MCP specification.
Provides a compatible interface for the CommonAgent while using the 
compliant MCP manager underneath.
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional
from .mcp_compliant_manager import MCPCompliantManager


class MCPCompliantClient:
    """
    MCP Client that provides a simplified interface for the CommonAgent
    while ensuring full compliance with MCP specifications underneath.
    """
    
    def __init__(self, manager: MCPCompliantManager):
        self.manager = manager
        self.logger = logging.getLogger(__name__)
    
    async def execute_tool(
        self,
        server_name: str,
        tool_name: str,
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a tool on an MCP server (using standard MCP Tools interface)"""
        try:
            return await self.manager.call_tool(server_name, tool_name, parameters)
        except Exception as e:
            self.logger.error(f"Error executing tool {tool_name}: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def read_resource(
        self,
        server_name: str,
        resource_uri: str
    ) -> Dict[str, Any]:
        """Read a resource from an MCP server (using standard MCP Resources interface)"""
        try:
            return await self.manager.read_resource(server_name, resource_uri)
        except Exception as e:
            self.logger.error(f"Error reading resource {resource_uri}: {e}")
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
        """Get a prompt from an MCP server (using standard MCP Prompts interface)"""
        try:
            return await self.manager.get_prompt(server_name, prompt_name, arguments)
        except Exception as e:
            self.logger.error(f"Error getting prompt {prompt_name}: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def list_tools(self, server_name: Optional[str] = None) -> Dict[str, List[str]]:
        """List available tools (compatible with existing interface)"""
        try:
            available_tools = self.manager.get_available_tools(server_name)
            
            result = {}
            for server, tools in available_tools.items():
                result[server] = [tool["name"] for tool in tools]
            
            return result
        except Exception as e:
            self.logger.error(f"Error listing tools: {e}")
            return {}
    
    async def list_resources(self, server_name: Optional[str] = None) -> Dict[str, List[str]]:
        """List available resources"""
        try:
            available_resources = self.manager.get_available_resources(server_name)
            
            result = {}
            for server, resources in available_resources.items():
                result[server] = [resource["uri"] for resource in resources]
            
            return result
        except Exception as e:
            self.logger.error(f"Error listing resources: {e}")
            return {}
    
    async def list_prompts(self, server_name: Optional[str] = None) -> Dict[str, List[str]]:
        """List available prompts"""
        try:
            available_prompts = self.manager.get_available_prompts(server_name)
            
            result = {}
            for server, prompts in available_prompts.items():
                result[server] = [prompt["name"] for prompt in prompts]
            
            return result
        except Exception as e:
            self.logger.error(f"Error listing prompts: {e}")
            return {}
    
    async def get_tool_schema(self, server_name: str, tool_name: str) -> Optional[Dict[str, Any]]:
        """Get schema for a specific tool (enhanced version)"""
        try:
            available_tools = self.manager.get_available_tools(server_name)
            
            if server_name not in available_tools:
                return None
            
            for tool in available_tools[server_name]:
                if tool["name"] == tool_name:
                    return tool
            
            return None
        except Exception as e:
            self.logger.error(f"Error getting tool schema: {e}")
            return None
    
    async def get_resource_info(self, server_name: str, resource_uri: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific resource"""
        try:
            available_resources = self.manager.get_available_resources(server_name)
            
            if server_name not in available_resources:
                return None
            
            for resource in available_resources[server_name]:
                if resource["uri"] == resource_uri:
                    return resource
            
            return None
        except Exception as e:
            self.logger.error(f"Error getting resource info: {e}")
            return None
    
    async def get_prompt_info(self, server_name: str, prompt_name: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific prompt"""
        try:
            available_prompts = self.manager.get_available_prompts(server_name)
            
            if server_name not in available_prompts:
                return None
            
            for prompt in available_prompts[server_name]:
                if prompt["name"] == prompt_name:
                    return prompt
            
            return None
        except Exception as e:
            self.logger.error(f"Error getting prompt info: {e}")
            return None
    
    def get_server_capabilities(self, server_name: str) -> Optional[Dict[str, Any]]:
        """Get capabilities for a specific server"""
        return self.manager.get_server_capabilities(server_name)
    
    def get_running_servers(self) -> List[str]:
        """Get list of running server names"""
        return self.manager.get_running_servers()
    
    async def batch_execute(
        self,
        tool_calls: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Execute multiple tools in batch (enhanced with better error handling)"""
        results = []
        
        for call in tool_calls:
            server_name = call.get("server_name")
            tool_name = call.get("tool_name")
            parameters = call.get("parameters", {})
            
            if not server_name or not tool_name:
                results.append({
                    "success": False,
                    "error": "Missing server_name or tool_name in tool call"
                })
                continue
            
            result = await self.execute_tool(server_name, tool_name, parameters)
            results.append(result)
        
        return results
    
    async def batch_read_resources(
        self,
        resource_calls: List[Dict[str, str]]
    ) -> List[Dict[str, Any]]:
        """Read multiple resources in batch"""
        results = []
        
        for call in resource_calls:
            server_name = call.get("server_name")
            resource_uri = call.get("resource_uri")
            
            if not server_name or not resource_uri:
                results.append({
                    "success": False,
                    "error": "Missing server_name or resource_uri in resource call"
                })
                continue
            
            result = await self.read_resource(server_name, resource_uri)
            results.append(result)
        
        return results 