"""
Base configuration types and data structures
"""

from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field


class BaseConfig(BaseModel):
    """Base configuration class"""
    name: str = Field(..., description="Configuration name")
    description: Optional[str] = Field(None, description="Configuration description")
    

class LLMConfig(BaseConfig):
    """LLM configuration"""
    provider: str = Field(..., description="LLM provider name")
    model: str = Field(..., description="Model name")
    api_key: str = Field(..., description="API key")
    base_url: Optional[str] = Field(None, description="Custom base URL")
    max_tokens: int = Field(default=4096, description="Maximum tokens")
    temperature: float = Field(default=0.7, description="Temperature setting")
    timeout: int = Field(default=60, description="Request timeout in seconds")


class MCPServerConfig(BaseConfig):
    """MCP server configuration - Enhanced for full MCP specification compliance"""
    command: List[str] = Field(..., description="Command to start MCP server")
    env: Dict[str, str] = Field(default_factory=dict, description="Environment variables")
    args: List[str] = Field(default_factory=list, description="Additional arguments")
    capabilities: List[str] = Field(default_factory=list, description="Server capabilities")
    
    # Enhanced MCP configuration options
    transport: str = Field(default="stdio", description="Transport method: stdio, sse, http")
    url: Optional[str] = Field(default=None, description="Server URL for SSE/HTTP transport")
    headers: Optional[Dict[str, str]] = Field(default=None, description="HTTP headers for remote servers")
    auth_config: Optional[Dict[str, Any]] = Field(default=None, description="OAuth/authentication configuration")
    timeout: int = Field(default=30, description="Connection timeout in seconds")
    protocol_version: str = Field(default="2025-06-18", description="MCP protocol version")


class AgentConfig(BaseConfig):
    """Agent configuration"""
    agent_type: str = Field(..., description="Agent type")
    endpoint: str = Field(..., description="Agent endpoint URL")
    capabilities: List[str] = Field(default_factory=list, description="Agent capabilities")
    # mcp_servers: List[str] = Field(default_factory=list, description="Available MCP servers")  # DEPRECATED: Use config/mcp_servers.json instead
    max_concurrent_tasks: int = Field(default=5, description="Maximum concurrent tasks")


class SystemConfig(BaseModel):
    """Complete system configuration"""
    llm: LLMConfig = Field(..., description="LLM configuration")
    # mcp_servers: Dict[str, MCPServerConfig] = Field(default_factory=dict, description="MCP servers")  # DEPRECATED: Use config/mcp_servers.json instead
    agents: Dict[str, AgentConfig] = Field(default_factory=dict, description="Specialist agents")
    common_agent: AgentConfig = Field(..., description="Common agent configuration") 