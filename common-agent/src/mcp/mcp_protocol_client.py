"""
MCP Protocol Client

真正的MCP协议客户端实现，支持：
- 通过stdio连接MCP服务器
- 发送JSON-RPC 2.0请求
- 动态发现工具列表（list_tools）
- 调用工具（call_tool）
"""

import asyncio
import json
import logging
import subprocess
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)


class MCPProtocolClient:
    """真正的MCP协议客户端"""
    
    def __init__(self):
        self.active_servers = {}  # server_name -> process
        self.server_tools = {}    # server_name -> [tools]
        self.request_id = 0
        
    def _get_next_request_id(self) -> int:
        """获取下一个请求ID"""
        self.request_id += 1
        return self.request_id
    
    async def start_mcp_server(self, server_name: str, server_config: Dict[str, Any]) -> bool:
        """启动MCP服务器进程"""
        try:
            command = server_config.get('command')
            args = server_config.get('args', [])
            env = server_config.get('env', {})
            
            if not command:
                logger.error(f"❌ MCP服务器 {server_name} 缺少command配置")
                return False
            
            # 构建完整命令
            full_command = [command] + args
            
            logger.info(f"🚀 启动MCP服务器: {server_name}")
            logger.debug(f"   命令: {' '.join(full_command)}")
            
            # 启动进程
            import os
            process_env = {**os.environ, **env} if env else os.environ
            process = await asyncio.create_subprocess_exec(
                *full_command,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=process_env
            )
            
            self.active_servers[server_name] = process
            logger.info(f"✅ MCP服务器 {server_name} 启动成功 (PID: {process.pid})")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ 启动MCP服务器 {server_name} 失败: {e}")
            return False
    
    async def send_jsonrpc_request(self, server_name: str, method: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """发送JSON-RPC 2.0请求到MCP服务器"""
        
        if server_name not in self.active_servers:
            raise ValueError(f"MCP服务器 {server_name} 未启动")
        
        process = self.active_servers[server_name]
        
        # 构建JSON-RPC 2.0请求
        request = {
            "jsonrpc": "2.0",
            "id": self._get_next_request_id(),
            "method": method,
            "params": params or {}
        }
        
        request_json = json.dumps(request) + "\n"
        
        logger.debug(f"📤 发送MCP请求到 {server_name}: {method}")
        
        try:
            # 发送请求
            process.stdin.write(request_json.encode())
            await process.stdin.drain()
            
            # 读取响应
            response_line = await process.stdout.readline()
            response_text = response_line.decode().strip()
            
            if not response_text:
                raise ValueError("收到空响应")
            
            response = json.loads(response_text)
            
            logger.debug(f"📥 收到MCP响应: {response.get('result', response.get('error'))}")
            
            # 检查错误
            if 'error' in response:
                error = response['error']
                raise ValueError(f"MCP错误: {error.get('message', 'Unknown error')}")
            
            return response.get('result', {})
            
        except Exception as e:
            logger.error(f"❌ MCP请求失败 {server_name}.{method}: {e}")
            raise
    
    async def discover_tools(self, server_name: str, server_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """通过MCP协议发现服务器的工具列表"""
        
        logger.info(f"🔍 通过MCP协议发现 {server_name} 的工具...")
        
        try:
            # 1. 启动MCP服务器
            if server_name not in self.active_servers:
                success = await self.start_mcp_server(server_name, server_config)
                if not success:
                    return []
            
            # 2. 发送初始化请求
            await self._initialize_server(server_name)
            
            # 3. 发送list_tools请求
            tools_result = await self.send_jsonrpc_request(server_name, "tools/list")
            
            # 4. 解析工具列表
            tools = tools_result.get('tools', [])
            
            if tools:
                logger.info(f"🔧 发现 {server_name} 的 {len(tools)} 个真实工具")
                for tool in tools[:3]:  # 显示前3个工具
                    tool_name = tool.get('name', 'unnamed')
                    description = tool.get('description', 'No description')
                    logger.debug(f"   - {tool_name}: {description}")
                if len(tools) > 3:
                    logger.debug(f"   ... 还有 {len(tools)-3} 个工具")
            else:
                logger.info(f"📝 {server_name} 服务器无可用工具")
            
            # 缓存工具列表
            self.server_tools[server_name] = tools
            
            return tools
            
        except Exception as e:
            logger.error(f"❌ MCP工具发现失败 {server_name}: {e}")
            return []
    
    async def _initialize_server(self, server_name: str):
        """初始化MCP服务器连接"""
        try:
            # 发送initialize请求
            init_params = {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "roots": {
                        "listChanged": True
                    },
                    "sampling": {}
                },
                "clientInfo": {
                    "name": "LLM-Driven Common Agent",
                    "version": "1.0.0"
                }
            }
            
            result = await self.send_jsonrpc_request(server_name, "initialize", init_params)
            logger.debug(f"🤝 {server_name} MCP服务器初始化成功")
            
            # 发送initialized通知
            await self.send_jsonrpc_notification(server_name, "notifications/initialized")
            
        except Exception as e:
            logger.warning(f"⚠️  {server_name} 初始化失败: {e}")
    
    async def send_jsonrpc_notification(self, server_name: str, method: str, params: Optional[Dict[str, Any]] = None):
        """发送JSON-RPC 2.0通知（无需响应）"""
        
        if server_name not in self.active_servers:
            raise ValueError(f"MCP服务器 {server_name} 未启动")
        
        process = self.active_servers[server_name]
        
        # 构建JSON-RPC 2.0通知（没有id字段）
        notification = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or {}
        }
        
        notification_json = json.dumps(notification) + "\n"
        
        try:
            process.stdin.write(notification_json.encode())
            await process.stdin.drain()
            logger.debug(f"📢 发送MCP通知到 {server_name}: {method}")
            
        except Exception as e:
            logger.error(f"❌ 发送MCP通知失败 {server_name}.{method}: {e}")
    
    async def call_tool(self, server_name: str, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """通过MCP协议调用工具"""
        
        logger.info(f"🔧 通过MCP协议调用工具: {server_name}:{tool_name}")
        
        try:
            if server_name not in self.active_servers:
                raise ValueError(f"MCP服务器 {server_name} 未启动")
            
            # 构建工具调用参数
            call_params = {
                "name": tool_name,
                "arguments": arguments
            }
            
            # 发送call_tool请求
            result = await self.send_jsonrpc_request(server_name, "tools/call", call_params)
            
            logger.info(f"✅ MCP工具调用成功: {tool_name}")
            return result
            
        except Exception as e:
            logger.error(f"❌ MCP工具调用失败 {server_name}:{tool_name}: {e}")
            raise
    
    def get_server_tools(self, server_name: str) -> List[str]:
        """获取服务器的工具名称列表"""
        tools = self.server_tools.get(server_name, [])
        return [tool.get('name', '') for tool in tools if tool.get('name')]
    
    def get_server_tool_info(self, server_name: str, tool_name: str) -> Dict[str, Any]:
        """获取指定工具的详细信息"""
        tools = self.server_tools.get(server_name, [])
        for tool in tools:
            if tool.get('name') == tool_name:
                return tool
        return {}
    
    async def close_server(self, server_name: str):
        """关闭MCP服务器"""
        if server_name in self.active_servers:
            process = self.active_servers[server_name]
            try:
                process.terminate()
                await process.wait()
                logger.info(f"🛑 MCP服务器 {server_name} 已关闭")
            except Exception as e:
                logger.error(f"❌ 关闭MCP服务器失败 {server_name}: {e}")
            finally:
                del self.active_servers[server_name]
                if server_name in self.server_tools:
                    del self.server_tools[server_name]
    
    async def close_all_servers(self):
        """关闭所有MCP服务器"""
        for server_name in list(self.active_servers.keys()):
            await self.close_server(server_name)
        
        logger.info("🛑 所有MCP服务器已关闭")


# 全局MCP客户端实例
mcp_client = MCPProtocolClient() 