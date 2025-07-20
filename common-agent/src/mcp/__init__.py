"""
MCP Management Package

Handles MCP (Model Context Protocol) server management and tool execution.
Provides both legacy and compliant implementations.
"""

# MCP-compliant implementations using official SDK
try:
    from .mcp_compliant_manager import MCPCompliantManager
    from .mcp_compliant_client import MCPCompliantClient
    MCP_COMPLIANT_AVAILABLE = True
    
    # Use compliant implementations as defaults
    MCPManager = MCPCompliantManager
    MCPClient = MCPCompliantClient
except ImportError:
    # Fallback if official MCP SDK is not available
    MCPCompliantManager = None
    MCPCompliantClient = None
    MCPManager = None
    MCPClient = None
    MCP_COMPLIANT_AVAILABLE = False

__all__ = [
    "MCPManager",
    "MCPClient", 
    "MCPCompliantManager",
    "MCPCompliantClient",
    "MCP_COMPLIANT_AVAILABLE"
] 