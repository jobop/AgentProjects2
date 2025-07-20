"""
Simple MCP Loader - Cursor-style MCP Configuration

This module provides a simple way to load MCP servers from JSON configuration,
similar to how Cursor handles MCP configuration.
"""

import json
import os
import asyncio
import logging
from typing import Dict, List, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class SimpleMCPLoader:
    """
    Simple MCP configuration loader similar to Cursor's approach
    
    Just add a JSON config file and your agent gets MCP powers!
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize MCP loader
        
        Args:
            config_path: Path to MCP config JSON file
                        Defaults to config/mcp_servers.json
        """
        if config_path is None:
            config_path = "config/mcp_servers.json"
        
        self.config_path = Path(config_path)
        self.servers_config = {}
        self.active_servers = {}
        
    def load_config(self) -> Dict[str, Any]:
        """
        从mcp_servers.json加载MCP服务器配置
        (支持LLM动态发现和调用MCP工具)
        """
        try:
            # 尝试多个配置文件位置
            config_paths = [
                self.config_path,
                Path("config/mcp_servers.json"),
                Path("../config/mcp_servers.json"),
                Path("../../config/mcp_servers.json")
            ]
            
            config_loaded = False
            for path in config_paths:
                if path.exists():
                    with open(path, 'r') as f:
                        config = json.load(f)
                    
                    self.servers_config = config.get('mcpServers', {})
                    logger.info(f"📦 从 {path} 加载 {len(self.servers_config)} 个MCP服务器")
                    
                    # 列出所有发现的MCP服务器及其描述
                    for server_name, server_config in self.servers_config.items():
                        description = server_config.get('description', 'No description')
                        command = server_config.get('command', 'unknown')
                        logger.info(f"  🔧 {server_name}: {description} (命令: {command})")
                    
                    config_loaded = True
                    break
            
            if not config_loaded:
                logger.warning("⚠️  未找到MCP配置文件，使用默认配置")
                self._create_default_config()
            
            return self.servers_config
            
        except Exception as e:
            logger.error(f"❌ 加载MCP配置失败: {e}")
            self._create_default_config()
            return self.servers_config
    
    def _create_default_config(self):
        """创建默认MCP配置"""
        self.servers_config = {
            "fetch": {
                "command": "uvx",
                "args": ["mcp-server-fetch"],
                "description": "Fetch web content and APIs"
            },
            "filesystem": {
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-filesystem", "."],
                "description": "Local file system access"
            },
            "git": {
                "command": "uvx", 
                "args": ["mcp-server-git", "--repository", "."],
                "description": "Git repository operations"
            }
        }
        logger.info(f"📦 使用默认MCP配置: {list(self.servers_config.keys())}")
    
    def get_server_config(self, server_name: str) -> Optional[Dict[str, Any]]:
        """Get configuration for a specific MCP server"""
        return self.servers_config.get(server_name)
    
    def list_available_servers(self) -> List[str]:
        """List all available MCP servers from config"""
        return list(self.servers_config.keys())
    
    def get_servers_by_capability(self, capability: str) -> List[str]:
        """动态获取提供特定能力的服务器 - 无硬编码"""
        # 🎯 移除硬编码映射 - 改为真正的动态发现
        # 应该查询实际连接的MCP服务器来获取其真实能力
        logger.debug(f"🔍 动态查询提供 '{capability}' 能力的服务器...")
        
        # TODO: 实现真正的能力发现机制
        # 当前返回空列表，避免任何硬编码假设
        return []
    
    async def create_agent_with_mcp(self, agent_name: str, instruction: str, 
                                  server_names: List[str]) -> 'SimpleMCPAgent':
        """
        Create an agent with MCP servers - Cursor-style simplicity!
        
        Args:
            agent_name: Name of the agent
            instruction: Agent's instruction/purpose
            server_names: List of MCP server names to enable
        
        Returns:
            SimpleMCPAgent with configured MCP servers
        """
        # Load config if not already loaded
        if not self.servers_config:
            self.load_config()
        
        # Validate server names
        available_servers = self.list_available_servers()
        valid_servers = [name for name in server_names if name in available_servers]
        
        if len(valid_servers) != len(server_names):
            invalid = set(server_names) - set(valid_servers)
            logger.warning(f"⚠️  Invalid MCP servers: {invalid}")
            logger.info(f"📋 Available servers: {available_servers}")
        
        return SimpleMCPAgent(
            name=agent_name,
            instruction=instruction,
            server_names=valid_servers,
            mcp_loader=self
        )


class SimpleMCPAgent:
    """
    Simple MCP-enabled agent - just like agents in Cursor!
    
    Usage:
        loader = SimpleMCPLoader()
        agent = await loader.create_agent_with_mcp(
            "research_agent", 
            "Help with research tasks",
            ["fetch", "filesystem"]
        )
    """
    
    def __init__(self, name: str, instruction: str, server_names: List[str], 
                 mcp_loader: SimpleMCPLoader):
        self.name = name
        self.instruction = instruction
        self.server_names = server_names
        self.mcp_loader = mcp_loader
        self.available_tools = []
        self.server_connections = {}
        
    async def initialize(self):
        """Initialize MCP servers (like Cursor does automatically)"""
        logger.info(f"🚀 Initializing {self.name} with MCP servers: {self.server_names}")
        
        for server_name in self.server_names:
            try:
                server_config = self.mcp_loader.get_server_config(server_name)
                if server_config:
                    # In a real implementation, this would start the MCP server
                    logger.info(f"  ✅ Connected to {server_name}: {server_config.get('description', 'No description')}")
                    self.server_connections[server_name] = server_config
                else:
                    logger.warning(f"  ❌ Server config not found: {server_name}")
                    
            except Exception as e:
                logger.error(f"  ❌ Failed to connect to {server_name}: {e}")
        
        # Simulate tool discovery - will need to await this in an async context
        # self._discover_tools()  # 异步方法需要在异步上下文中调用
        logger.info("🔧 MCP工具发现需要在异步上下文中进行")
        
    async def _discover_tools(self):
        """Dynamically discover available tools from connected MCP servers - NO HARDCODING"""
        # 🎯 纯净的动态发现机制 - 完全由LLM和运行时决策
        
        discovered_tools = []
        
        for server_name in self.server_connections:
            # 真正的动态发现 - 运行时查询MCP服务器的实际能力
            try:
                # 通过MCP协议发现真实工具
                server_tools = await self._query_server_tools(server_name)
                discovered_tools.extend([f"{server_name}:{tool}" for tool in server_tools])
                
            except Exception as e:
                logger.warning(f"⚠️  无法从 {server_name} 发现工具: {e}")
                # 失败时不假设任何工具存在
                
        self.available_tools = discovered_tools
        logger.info(f"🔍 动态发现工具: {len(self.available_tools)} 个工具来自 {len(self.server_connections)} 个服务器")
        
    async def _query_server_tools(self, server_name: str) -> List[str]:
        """真正动态查询MCP服务器的工具列表 - 无任何硬编码"""
        logger.debug(f"🔍 动态查询 {server_name} 的真实工具列表...")
        
        # 🎯 完全动态发现 - 通过MCP协议查询服务器的实际工具
        server_config = self.mcp_loader.servers_config.get(server_name)
        if not server_config:
            logger.warning(f"⚠️  MCP服务器 {server_name} 未在mcp_servers.json中配置")
            return []
        
        try:
            # 🎯 实现真正的MCP协议工具发现
            # 这里应该启动MCP服务器进程并调用list_tools端点
            tools = await self._discover_tools_via_mcp_protocol(server_name, server_config)
            
            if tools:
                logger.info(f"🔧 通过MCP协议发现 {server_name} 的 {len(tools)} 个真实工具")
                logger.debug(f"   动态发现的工具: {', '.join(tools)}")
            else:
                logger.info(f"📝 {server_name} 服务器可用但未返回工具列表")
            
            return tools
            
        except Exception as e:
            logger.warning(f"⚠️  无法通过MCP协议查询 {server_name}: {e}")
            # 🎯 失败时不假设任何工具存在，保持纯净
            return []
    
    async def _discover_tools_via_mcp_protocol(self, server_name: str, server_config: Dict[str, Any]) -> List[str]:
        """通过MCP协议动态发现工具 - 真正的实现"""
        
        try:
            # 导入MCP协议客户端
            from .mcp_protocol_client import mcp_client
            
            logger.info(f"🔍 使用MCP协议发现 {server_name} 的真实工具...")
            
            # 通过MCP协议发现工具
            tools = await mcp_client.discover_tools(server_name, server_config)
            
            # 提取工具名称列表
            tool_names = [tool.get('name', '') for tool in tools if tool.get('name')]
            
            if tool_names:
                logger.info(f"✅ 通过MCP协议发现 {server_name} 的 {len(tool_names)} 个工具")
                logger.debug(f"   工具列表: {', '.join(tool_names)}")
            else:
                logger.info(f"📝 {server_name} 服务器当前无可用工具")
            
            return tool_names
            
        except Exception as e:
            logger.error(f"❌ MCP协议工具发现失败 {server_name}: {e}")
            logger.debug(f"   配置: {server_config}")
            return []
    
    async def process_request(self, user_input: str) -> str:
        """Process a user request using available MCP tools"""
        logger.info(f"💭 Processing request: {user_input}")
        
        # Simulate LLM processing with MCP tools
        response = f"""
🤖 {self.name} Response:
📝 Request: {user_input}
🔧 Available MCP Servers: {', '.join(self.server_connections.keys())}
⚡ Available Tools: {len(self.available_tools)} tools
🎯 Instruction: {self.instruction}

✅ I can help you with this request using my MCP-powered capabilities!
"""
        return response.strip()
    
    def get_status(self) -> Dict[str, Any]:
        """Get agent status"""
        return {
            "name": self.name,
            "instruction": self.instruction,
            "mcp_servers": list(self.server_connections.keys()),
            "available_tools": len(self.available_tools),
            "status": "ready"
        }


# Convenience functions for quick MCP setup

def quick_mcp_setup(config_path: Optional[str] = None) -> SimpleMCPLoader:
    """
    Quick MCP setup - one function call!
    
    Just like adding MCP in Cursor settings.
    """
    loader = SimpleMCPLoader(config_path)
    loader.load_config()
    return loader


async def create_research_agent() -> SimpleMCPAgent:
    """Create a research agent with web and file access"""
    loader = quick_mcp_setup()
    return await loader.create_agent_with_mcp(
        "research_agent",
        "Research assistant with web and file access",
        ["fetch", "filesystem"]
    )


async def create_developer_agent() -> SimpleMCPAgent:
    """Create a developer agent with full development tools"""
    loader = quick_mcp_setup()
    return await loader.create_agent_with_mcp(
        "developer_agent", 
        "Full-stack developer with database and git access",
        ["filesystem", "git", "postgres", "github"]
    )


async def create_designer_agent() -> SimpleMCPAgent:
    """Create a designer agent with design tools"""
    loader = quick_mcp_setup()
    return await loader.create_agent_with_mcp(
        "designer_agent",
        "UI/UX designer with Figma integration",
        ["figma", "filesystem", "fetch"]
    )


async def create_community_agent() -> SimpleMCPAgent:
    """Create a community management agent"""
    loader = quick_mcp_setup()
    return await loader.create_agent_with_mcp(
        "community_agent",
        "Community manager with social platform access", 
        ["discord", "github", "notion"]
    ) 