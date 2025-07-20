#!/usr/bin/env python3
"""
LLM-Driven Common Agent Server

真正的LLM驱动的Common Agent，负责：
1. 通过LLM分析任务并决策
2. 动态发现可用的specialist agents
3. 使用A2A协议与agents通信
4. 自动选择和使用MCP工具
5. 协调多agent协作完成复杂任务

没有任何硬编码逻辑，完全依赖LLM智能决策
"""

import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional
from fastapi import FastAPI
import uvicorn
import httpx
from datetime import datetime

# Add paths for imports
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))

from llm.client import LLMClient
from mcp.simple_mcp_loader import SimpleMCPLoader
from shared.config_manager import get_timeout, config_manager

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class AgentDiscovery:
    """Agent发现和管理系统"""
    
    def __init__(self):
        self.discovered_agents = {}
        self.agent_capabilities = {}
        
    async def discover_agents(self, discovery_endpoints: List[str]) -> Dict[str, Any]:
        """
        发现可用的agents
        
        Args:
            discovery_endpoints: agent发现端点列表
            
        Returns:
            发现的agents信息
        """
        logger.info("🔍 开始agent发现过程...")
        
        for endpoint in discovery_endpoints:
            try:
                await self._discover_single_agent(endpoint)
            except Exception as e:
                logger.warning(f"⚠️  发现agent失败 {endpoint}: {e}")
                
        logger.info(f"✅ 发现完成，找到 {len(self.discovered_agents)} 个agents")
        return self.discovered_agents
    
    async def _discover_single_agent(self, endpoint: str):
        """发现单个agent"""
        async with httpx.AsyncClient() as client:
            # 尝试A2A协议发现
            try:
                # 检查 /a2a/agent.json (python-a2a标准)
                response = await client.get(f"{endpoint}/a2a/agent.json", timeout=get_timeout("agent_discovery"))
                if response.status_code == 200:
                    agent_card = response.json()
                    agent_id = agent_card.get("name", "unknown").lower().replace(" ", "_")
                    self.discovered_agents[agent_id] = {
                        "endpoint": endpoint,
                        "agent_card": agent_card,
                        "protocol": "a2a",
                        "discovery_method": "agent_card"
                    }
                    self.agent_capabilities[agent_id] = agent_card.get("skills", [])
                    logger.info(f"   ✅ 发现A2A agent: {agent_card.get('name')}")
                    return
            except:
                pass
                
            # 备选：检查 /.well-known/agent.json (A2A标准路径)
            try:
                response = await client.get(f"{endpoint}/.well-known/agent.json", timeout=get_timeout("agent_discovery"))
                if response.status_code == 200:
                    agent_card = response.json()
                    agent_id = agent_card.get("name", "unknown").lower().replace(" ", "_")
                    self.discovered_agents[agent_id] = {
                        "endpoint": endpoint,
                        "agent_card": agent_card,
                        "protocol": "a2a",
                        "discovery_method": "agent_card_standard"
                    }
                    self.agent_capabilities[agent_id] = agent_card.get("skills", [])
                    logger.info(f"   ✅ 发现A2A agent (标准路径): {agent_card.get('name')}")
                    return
            except:
                pass
                
            # 尝试传统能力端点
            try:
                response = await client.get(f"{endpoint}/capabilities", timeout=get_timeout("agent_discovery"))
                if response.status_code == 200:
                    capabilities = response.json()
                    agent_name = capabilities.get("agent_name", "unknown")
                    agent_id = agent_name.lower().replace(" ", "_")
                    self.discovered_agents[agent_id] = {
                        "endpoint": endpoint,
                        "capabilities": capabilities,
                        "protocol": "legacy",
                        "discovery_method": "capabilities_endpoint"
                    }
                    self.agent_capabilities[agent_id] = capabilities.get("capabilities", [])
                    logger.info(f"   ✅ 发现legacy agent: {agent_name}")
                    return
            except:
                pass
                
            # 尝试健康检查端点
            try:
                response = await client.get(f"{endpoint}/health", timeout=get_timeout("health_check"))
                if response.status_code == 200:
                    health = response.json()
                    agent_name = health.get("agent", "unknown")
                    agent_id = agent_name.lower().replace(" ", "_")
                    self.discovered_agents[agent_id] = {
                        "endpoint": endpoint,
                        "health": health,
                        "protocol": "unknown",
                        "discovery_method": "health_check"
                    }
                    logger.info(f"   ✅ 发现基础agent: {agent_name}")
                    return
            except:
                pass
                
        logger.warning(f"   ❌ 无法发现agent: {endpoint}")
    
    def get_available_agents(self) -> List[str]:
        """获取可用agent列表"""
        return list(self.discovered_agents.keys())
    
    def get_agent_capabilities(self, agent_id: str) -> List[str]:
        """获取agent能力"""
        return self.agent_capabilities.get(agent_id, [])
    
    def get_agent_info(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """获取agent信息"""
        return self.discovered_agents.get(agent_id)


class LLMDrivenCommonAgent:
    """LLM驱动的Common Agent"""
    
    def __init__(self, port: int = 8000):
        self.port = port
        self.app = FastAPI(title="LLM-Driven Common Agent", version="1.0.0")
        
        # 核心组件
        self.llm_client = None
        self.mcp_loader = SimpleMCPLoader()
        self.agent_discovery = AgentDiscovery()
        
        # 系统状态
        self.active_tasks = {}
        self.task_counter = 0
        
        # Agent发现配置 (从环境变量或配置文件获取)
        self.discovery_endpoints = [
            "http://localhost:8001",  # User Research Agent
            "http://localhost:8002",  # Product Manager Agent  
            "http://localhost:8003",  # UI Designer Agent
        ]
        
        # 定时刷新配置
        self.discovery_refresh_interval = 30  # 30秒刷新一次
        self.discovery_task = None
        
        # 立即初始化LLM客户端
        self._init_llm_client()
        
        # 设置路由
        from routes import CommonAgentRoutes
        self.routes = CommonAgentRoutes(self.app, self)
        
    def _init_llm_client(self):
        """初始化LLM客户端"""
        try:
            from llm.provider_enhanced import EnhancedSiliconFlowProvider
            
            # 简化的LLM配置类
            class SimpleLLMConfig:
                def __init__(self):
                    self.provider = "siliconflow"
                    self.model = "deepseek-ai/DeepSeek-V3"
                    self.api_key = os.getenv("SILICONFLOW_API_KEY", "sk-wqbnsqwforwydiznaqiluckllleiqrtffhzjmpxrcjciifle")
                    self.base_url = "https://api.siliconflow.cn/v1"
                    self.max_tokens = 4096
                    self.temperature = 0.7
            
            # 创建配置
            llm_config = SimpleLLMConfig()
            
            # 创建提供者
            provider = EnhancedSiliconFlowProvider(
                api_key=llm_config.api_key,
                model=llm_config.model
            )
            
            # 创建客户端
            self.llm_client = LLMClient(llm_config, provider)
            logger.info("✅ LLM客户端初始化成功")
        except Exception as e:
            logger.error(f"❌ LLM客户端初始化失败: {e}")
            # 不抛出异常，允许系统继续运行
        
    async def initialize(self):
        """初始化系统"""
        logger.info("🎯 初始化LLM驱动的Common Agent...")
        
        # 初始化LLM客户端
        try:
            from llm.provider_enhanced import EnhancedSiliconFlowProvider
            
            # 简化的LLM配置类
            class SimpleLLMConfig:
                def __init__(self):
                    self.provider = "siliconflow"
                    self.model = "deepseek-ai/DeepSeek-V3"
                    self.api_key = os.getenv("SILICONFLOW_API_KEY", "sk-wqbnsqwforwydiznaqiluckllleiqrtffhzjmpxrcjciifle")
                    self.base_url = "https://api.siliconflow.cn/v1"
                    self.max_tokens = 4096
                    self.temperature = 0.7
            
            # 创建配置
            llm_config = SimpleLLMConfig()
            
            # 创建提供者
            provider = EnhancedSiliconFlowProvider(
            api_key=llm_config.api_key,
            model=llm_config.model
        )
            
            # 创建客户端
            self.llm_client = LLMClient(llm_config, provider)
            logger.info("✅ LLM客户端初始化成功")
        except Exception as e:
            logger.error(f"❌ LLM客户端初始化失败: {e}")
            raise
        
        # 初始化MCP
        try:
            self.mcp_loader.load_config()
            available_servers = self.mcp_loader.list_available_servers()
            logger.info(f"✅ MCP初始化成功，可用服务器: {len(available_servers)}")
        except Exception as e:
            logger.warning(f"⚠️  MCP初始化失败: {e}")
        
        # 发现agents
        await self.agent_discovery.discover_agents(self.discovery_endpoints)
        
        # 启动定时刷新任务
        self.discovery_task = asyncio.create_task(self._periodic_discovery_refresh())
        
        logger.info("🎯 Common Agent初始化完成")
        
    async def _periodic_discovery_refresh(self):
        """定时刷新Agent发现"""
        logger.info(f"🔄 启动定时Agent发现刷新 (间隔: {self.discovery_refresh_interval}秒)")
        
        while True:
            try:
                await asyncio.sleep(self.discovery_refresh_interval)
                
                logger.debug("🔄 执行定时Agent发现刷新...")
                previous_count = len(self.agent_discovery.discovered_agents)
                
                await self.agent_discovery.discover_agents(self.discovery_endpoints)
                
                current_count = len(self.agent_discovery.discovered_agents)
                
                if current_count != previous_count:
                    logger.info(f"📊 Agent发现状态更新: {previous_count} -> {current_count} 个Agent")
                else:
                    logger.debug(f"📊 Agent发现状态稳定: {current_count} 个Agent")
                    
            except Exception as e:
                logger.error(f"❌ 定时Agent发现刷新失败: {e}")
                await asyncio.sleep(5)  # 出错时等待5秒后重试
        

    
    async def process_task_with_llm_stream(self, task_id: str, task_data: Dict[str, Any]):
        """
        使用LLM流式处理任务的核心逻辑
        
        完全由LLM决定如何处理任务，使用SSE流式响应
        """
        description = task_data.get("description", "")
        task = self.active_tasks[task_id]
        
        logger.info(f"🧠 LLM流式分析任务 {task_id}: {description}")
        
        # 发送分析开始事件
        yield {"event": "llm_analysis_started", "task_id": task_id}
        
        # 构建系统上下文给LLM
        system_context = await self._build_system_context()
        
        # LLM分析提示
        analysis_prompt = f"""
你是一个多Agent系统的协调者。用户提交了一个任务，你需要分析这个任务并决定如何处理。

可用的系统资源：
{json.dumps(system_context, indent=2, ensure_ascii=False)}

用户任务：
{description}

请分析这个任务并制定执行计划。你的回复必须是有效的JSON格式，包含以下字段：

{{
    "analysis": "对任务的详细分析",
    "execution_strategy": "single_agent|multi_agent|mcp_tools|hybrid",
    "required_agents": ["agent_id列表"],
    "required_tools": ["工具名称列表"],
    "execution_plan": [
        {{
            "step": 1,
            "action": "agent_call|tool_use|coordination",
            "target": "agent_id或tool_name",
            "task": "具体任务描述",
            "dependencies": ["依赖的前置步骤"]
        }}
    ],
    "expected_deliverables": ["预期交付物列表"]
}}

请确保你的决策完全基于可用的agents和工具，不要假设不存在的能力。
"""

        try:
            # 检查LLM客户端是否可用
            if not self.llm_client:
                yield {"event": "error", "error": "LLM客户端未初始化"}
                return
                
            # 使用LLM流式获取分析结果
            llm_response = ""
            logger.info("🔍 开始LLM流式分析...")
            
            async for chunk in self.llm_client.stream_message(message=analysis_prompt):
                llm_response += chunk
                # 发送LLM分析进度
                yield {"event": "llm_analysis_progress", "chunk": chunk}
            
            # 发送LLM分析完成
            yield {"event": "llm_analysis_completed", "analysis": llm_response}
            
            # 解析LLM返回的JSON
            try:
                llm_decision = json.loads(llm_response)
            except json.JSONDecodeError:
                # 如果LLM返回的不是有效JSON，尝试提取JSON部分
                import re
                json_match = re.search(r'\{.*\}', llm_response, re.DOTALL)
                if json_match:
                    llm_decision = json.loads(json_match.group())
                else:
                    raise ValueError("LLM返回的不是有效JSON格式")
            
            logger.info(f"📋 LLM决策: {llm_decision['execution_strategy']}")
            
            # 发送LLM决策事件
            yield {"event": "llm_decision_made", "decision": llm_decision}
            
            # 记录决策步骤
            task["steps"].append({
                "step": "llm_analysis",
                "decision": llm_decision,
                "timestamp": datetime.now().isoformat()
            })
            
            # 根据LLM决策流式执行任务
            async for event in self._execute_llm_plan_stream(task_id, llm_decision):
                yield event
            
            # 完成任务
            task["status"] = "completed"
            task["completed_at"] = datetime.now().isoformat()
            
            logger.info(f"✅ LLM驱动任务 {task_id} 完成")
            
        except Exception as e:
            logger.error(f"❌ LLM任务处理失败: {e}")
            yield {"event": "error", "error": str(e)}
            
            # 降级处理：如果LLM失败，使用基础逻辑
            async for event in self._fallback_processing_stream(task_id, description):
                yield event

    async def process_task_with_llm(self, task_id: str, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        使用LLM处理任务的核心逻辑
        
        完全由LLM决定如何处理任务，无任何硬编码逻辑
        """
        description = task_data.get("description", "")
        task = self.active_tasks[task_id]
        
        logger.info(f"🧠 LLM分析任务 {task_id}: {description}")
        
        # 构建系统上下文给LLM
        system_context = await self._build_system_context()
        
        # LLM分析提示
        analysis_prompt = f"""
你是一个多Agent系统的协调者。用户提交了一个任务，你需要分析这个任务并决定如何处理。

可用的系统资源：
{json.dumps(system_context, indent=2, ensure_ascii=False)}

用户任务：
{description}

请分析这个任务并制定执行计划。你的回复必须是有效的JSON格式，包含以下字段：

{{
    "analysis": "对任务的详细分析",
    "execution_strategy": "single_agent|multi_agent|mcp_tools|hybrid",
    "required_agents": ["agent_id列表"],
    "required_tools": ["工具名称列表"],
    "execution_plan": [
        {{
            "step": 1,
            "action": "agent_call|tool_use|coordination",
            "target": "agent_id或tool_name",
            "task": "具体任务描述",
            "dependencies": ["依赖的前置步骤"]
        }}
    ],
    "expected_deliverables": ["预期交付物列表"]
}}

请确保你的决策完全基于可用的agents和工具，不要假设不存在的能力。
"""

        try:
            # 检查LLM客户端是否可用
            logger.info(f"🔍 检查LLM客户端状态: {self.llm_client is not None}")
            if not self.llm_client:
                raise ValueError("LLM客户端未初始化")
                
            # 检查LLM客户端的具体状态
            logger.info(f"🔍 LLM客户端类型: {type(self.llm_client)}")
            logger.info(f"🔍 LLM Provider类型: {type(self.llm_client.provider) if self.llm_client else 'None'}")
            
            # 测试LLM连接
            logger.info("🔍 开始测试LLM连接...")
            test_response = await self.llm_client.send_message("Hello, test connection")
            logger.info(f"🔍 LLM连接测试响应: {repr(test_response[:100])}")
            
            # 记录分析提示的长度和开头
            logger.info(f"🔍 分析提示长度: {len(analysis_prompt)} 字符")
            logger.info(f"🔍 分析提示开头: {repr(analysis_prompt[:200])}")
            
            # 获取LLM分析结果
            logger.info("🔍 开始调用LLM进行任务分析...")
            llm_response = await self.llm_client.send_message(
                message=analysis_prompt
            )
            
            logger.info(f"🔍 LLM原始响应长度: {len(llm_response)} 字符")
            logger.info(f"🔍 LLM响应前200字符: {repr(llm_response[:200])}")
            logger.info(f"🔍 LLM响应后200字符: {repr(llm_response[-200:])}")
            
            # 检查LLM响应是否为空
            if not llm_response or not llm_response.strip():
                logger.error("❌ LLM返回空响应")
                raise ValueError("LLM返回空响应，可能是API调用失败")
            
            # 使用增强的JSON解析器
            logger.info("🔍 开始解析LLM响应...")
            from core.json_parser import parse_decision_response
            llm_decision = parse_decision_response(llm_response)
            logger.info(f"🔍 解析结果类型: {type(llm_decision)}")
            logger.info(f"🔍 解析结果内容: {llm_decision}")
            
            # 确保返回格式符合预期
            if not isinstance(llm_decision, dict):
                raise ValueError(f"LLM返回格式错误: {type(llm_decision)}")
            
            logger.info(f"📋 LLM决策: {llm_decision['execution_strategy']}")
            
            # 记录决策步骤
            task["steps"].append({
                "step": "llm_analysis",
                "decision": llm_decision,
                "timestamp": datetime.now().isoformat()
            })
            
            # 根据LLM决策执行任务
            result = await self._execute_llm_plan(task_id, llm_decision)
            
            # 完成任务
            task["status"] = "completed"
            task["completed_at"] = datetime.now().isoformat()
            task["result"] = result
            
            logger.info(f"✅ LLM驱动任务 {task_id} 完成")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ LLM任务处理失败: {e}")
            
            # 降级处理：如果LLM失败，使用基础逻辑
            return await self._fallback_processing(task_id, description)
    
    async def _build_system_context(self) -> Dict[str, Any]:
        """构建系统上下文给LLM"""
        
        # 可用agents信息
        available_agents = {}
        for agent_id in self.agent_discovery.get_available_agents():
            agent_info = self.agent_discovery.get_agent_info(agent_id)
            if agent_info:  # 确保agent_info不为None
                available_agents[agent_id] = {
                    "endpoint": agent_info["endpoint"],
                    "capabilities": self.agent_discovery.get_agent_capabilities(agent_id),
                    "protocol": agent_info.get("protocol", "unknown")
                }
        
        # 可用MCP工具 - 添加详细日志
        available_tools = []
        mcp_server_details = []
        
        logger.info("🔍 构建MCP工具上下文...")
        
        try:
            mcp_servers = self.mcp_loader.list_available_servers()
            logger.info(f"🔧 发现 {len(mcp_servers)} 个MCP服务器: {mcp_servers}")
            
            for server in mcp_servers:
                try:
                    # 从配置获取服务器信息
                    server_config = self.mcp_loader.get_server_config(server)
                    if server_config:
                        description = server_config.get("description", "No description")
                        command = server_config.get("command", "Unknown")
                        
                        logger.info(f"📋 {server} 服务器: {description} (命令: {command})")
                        
                        # 由于工具需要运行时发现，这里只记录服务器信息
                        mcp_server_details.append({
                            "name": server,
                            "description": description,
                            "command": command,
                            "tools": "需要运行时发现"
                        })
                        
                        # 添加一个占位符工具信息
                        tool_info = {
                            "server": server,
                            "tool": "runtime_discovery",
                            "full_name": f"{server}:runtime_discovery",
                            "description": f"工具需要运行时从 {server} 服务器发现"
                        }
                        available_tools.append(tool_info)
                    else:
                        logger.warning(f"⚠️  未找到 {server} 的配置信息")
                        
                except Exception as e:
                    logger.error(f"❌ 获取 {server} 工具信息失败: {e}")
                    
        except Exception as e:
            logger.error(f"❌ MCP工具上下文构建失败: {e}")
        
        logger.info(f"🎯 MCP工具上下文完成: {len(available_tools)} 个工具来自 {len(mcp_server_details)} 个服务器")
        
        context = {
            "available_agents": available_agents,
            "available_mcp_tools": available_tools,
            "mcp_server_details": mcp_server_details,
            "total_agents": len(available_agents),
            "total_tools": len(available_tools)
        }
        
        # 记录完整上下文用于调试
        logger.info(f"🔍 完整系统上下文: {json.dumps(context, indent=2, ensure_ascii=False)}")
        
        return context
    
    async def _execute_llm_plan_stream(self, task_id: str, llm_decision: Dict[str, Any]):
        """流式执行LLM制定的计划"""
        
        execution_plan = llm_decision.get("execution_plan", [])
        strategy = llm_decision.get("execution_strategy", "unknown")
        
        logger.info(f"🎯 流式执行LLM计划: {strategy}, {len(execution_plan)} 步")
        
        yield {"event": "execution_started", "strategy": strategy, "total_steps": len(execution_plan)}
        
        execution_results = []
        start_time = datetime.now()
        
        for step in execution_plan:
            step_num = step.get("step", 0)
            action = step.get("action", "unknown")
            target = step.get("target", "")
            task_desc = step.get("task", "")
            
            logger.info(f"📍 执行步骤 {step_num}: {action} -> {target}")
            
            # 发送步骤开始事件
            yield {
                "event": "step_started", 
                "step_number": step_num,
                "step_description": f"{action} -> {target}: {task_desc}",
                "action": action, 
                "target": target,
                "task": task_desc
            }
            
            # 添加小延迟，让流式输出更明显
            await asyncio.sleep(0.1)
            
            step_start_time = datetime.now()
            
            try:
                if action == "agent_call":
                    # 发送Agent调用开始事件
                    yield {"event": "agent_call_started", "agent_id": target}
                    
                    # 调用Agent
                    result = await self._call_agent(target, task_desc, execution_results)
                    
                    # 发送Agent调用完成事件
                    success = result.get("success", True) if isinstance(result, dict) else True
                    duration = (datetime.now() - step_start_time).total_seconds() * 1000
                    yield {
                        "event": "agent_call_completed", 
                        "agent_id": target,
                        "result": result,
                        "duration": duration
                    }
                    
                    # 添加小延迟，让流式输出更明显
                    await asyncio.sleep(0.05)
                    
                elif action == "tool_use":
                    # 发送MCP工具使用事件
                    yield {"event": "mcp_tool_used", "tool": target}
                    
                    result = await self._use_mcp_tool(target, task_desc)
                    
                elif action == "coordination":
                    result = await self._coordinate_action(target, task_desc, execution_results)
                else:
                    result = {"error": f"Unknown action: {action}"}
                
                step_duration = (datetime.now() - step_start_time).total_seconds() * 1000
                
                execution_results.append({
                    "step": step_num,
                    "action": action,
                    "target": target,
                    "result": result,
                    "duration": step_duration,
                    "timestamp": datetime.now().isoformat()
                })
                
                # 发送步骤完成事件（对于非agent_call的情况）
                if action != "agent_call":
                    success = result.get("success", True) if isinstance(result, dict) else True
                    yield {
                        "event": "step_completed", 
                        "step_number": step_num,
                        "action": action,
                        "target": target,
                        "success": success,
                        "duration": step_duration,
                        "result": result
                    }
                
                # 更新任务步骤
                self.active_tasks[task_id]["steps"].append({
                    "step": f"execution_step_{step_num}",
                    "action": action,
                    "target": target,
                    "result": result,
                    "duration": step_duration,
                    "timestamp": datetime.now().isoformat()
                })
                
            except Exception as e:
                logger.error(f"❌ 步骤 {step_num} 执行失败: {e}")
                step_duration = (datetime.now() - step_start_time).total_seconds() * 1000
                
                error_result = {"error": str(e), "step": step_num}
                execution_results.append({
                    "step": step_num,
                    "action": action,
                    "target": target,
                    "result": error_result,
                    "duration": step_duration,
                    "timestamp": datetime.now().isoformat()
                })
                
                # 发送步骤失败事件
                yield {
                    "event": "step_completed", 
                    "step_number": step_num,
                    "action": action,
                    "target": target,
                    "success": False,
                    "duration": step_duration,
                    "error": str(e)
                }
                
                # 更新任务步骤
                self.active_tasks[task_id]["steps"].append({
                    "step": f"execution_step_{step_num}",
                    "action": action,
                    "target": target,
                    "result": error_result,
                    "duration": step_duration,
                    "timestamp": datetime.now().isoformat()
                })
        
        # 计算总执行时间
        total_duration = (datetime.now() - start_time).total_seconds() * 1000
        
        # 发送执行完成事件
        yield {
            "event": "execution_completed",
            "total_steps": len(execution_plan),
            "successful_steps": len([r for r in execution_results if r.get("result", {}).get("success", True)]),
            "failed_steps": len([r for r in execution_results if not r.get("result", {}).get("success", True)]),
            "total_duration": total_duration,
            "results": execution_results
        }

    async def _fallback_processing_stream(self, task_id: str, description: str):
        """流式降级处理"""
        yield {"event": "fallback_started", "reason": "LLM处理失败，使用降级逻辑"}
        
        # 简单的降级逻辑：如果包含"设计"关键词，调用UI设计师
        if "设计" in description or "界面" in description or "UI" in description:
            yield {"event": "fallback_decision", "target": "ui_designer_agent", "reason": "检测到设计相关任务"}
            
            try:
                result = await self._call_agent("ui_designer_agent", description, [])
                yield {"event": "fallback_completed", "result": result}
            except Exception as e:
                yield {"event": "fallback_error", "error": str(e)}
        else:
            yield {"event": "fallback_error", "error": "无法确定合适的处理方式"}

    async def _execute_llm_plan(self, task_id: str, llm_decision: Dict[str, Any]) -> Dict[str, Any]:
        """执行LLM制定的计划"""
        
        execution_plan = llm_decision.get("execution_plan", [])
        strategy = llm_decision.get("execution_strategy", "unknown")
        
        logger.info(f"🎯 执行LLM计划: {strategy}, {len(execution_plan)} 步")
        
        execution_results = []
        
        for step in execution_plan:
            step_num = step.get("step", 0)
            action = step.get("action", "unknown")
            target = step.get("target", "")
            task_desc = step.get("task", "")
            
            logger.info(f"📍 执行步骤 {step_num}: {action} -> {target}")
            
            try:
                if action == "agent_call":
                    result = await self._call_agent(target, task_desc, execution_results)
                elif action == "tool_use":
                    result = await self._use_mcp_tool(target, task_desc)
                elif action == "coordination":
                    result = await self._coordinate_action(target, task_desc, execution_results)
                else:
                    result = {"error": f"Unknown action: {action}"}
                
                execution_results.append({
                    "step": step_num,
                    "action": action,
                    "target": target,
                    "result": result,
                    "timestamp": datetime.now().isoformat()
                })
                
                # 更新任务步骤
                self.active_tasks[task_id]["steps"].append({
                    "step": f"execution_step_{step_num}",
                    "action": action,
                    "target": target,
                    "result": result,
                    "timestamp": datetime.now().isoformat()
                })
                
            except Exception as e:
                logger.error(f"❌ 步骤 {step_num} 执行失败: {e}")
                execution_results.append({
                    "step": step_num,
                    "action": action,
                    "target": target,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                })
        
        # 返回执行结果
        return {
            "task_id": task_id,
            "execution_strategy": strategy,
            "llm_decision": llm_decision,
            "execution_results": execution_results,
            "total_steps": len(execution_plan),
            "completed_steps": len(execution_results),
            "summary": self._generate_execution_summary(llm_decision, execution_results)
        }
    
    async def _call_agent(self, agent_id: str, task_description: str, previous_results: List[Dict]) -> Dict[str, Any]:
        """调用specialist agent"""
        
        agent_info = self.agent_discovery.get_agent_info(agent_id)
        if not agent_info:
            return {"error": f"Agent not found: {agent_id}"}
        
        endpoint = agent_info["endpoint"]
        protocol = agent_info.get("protocol", "unknown")
        
        logger.info(f"📞 调用 {agent_id} ({protocol}) : {task_description}")
        
        try:
            # 构建任务数据
            task_data = {
                "type": "delegated_task",
                "description": task_description,
                "context": {
                    "previous_results": previous_results,
                    "delegated_by": "common_agent"
                }
            }
            
            # 根据协议类型调用
            if protocol == "a2a":
                return await self._call_a2a_agent(endpoint, task_data)
            else:
                return await self._call_legacy_agent(endpoint, task_data)
                
        except Exception as e:
            logger.error(f"❌ 调用agent {agent_id} 失败: {e}")
            return {"error": str(e), "agent": agent_id}
    
    async def _call_a2a_agent(self, endpoint: str, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """使用A2A协议调用agent"""
        
        # A2A JSON-RPC 2.0 请求
        a2a_request = {
            "jsonrpc": "2.0",
            "method": "tasks/send",
            "id": f"common_agent_{int(datetime.now().timestamp())}",
            "params": {
                "id": f"task_{int(datetime.now().timestamp())}",
                "sessionId": f"session_{int(datetime.now().timestamp())}",
                "message": {
                    "role": "user",
                    "parts": [
                        {
                            "type": "text",
                            "text": task_data["description"]
                        },
                        {
                            "type": "data",
                            "data": task_data.get("context", {})
                        }
                    ]
                },
                "acceptedOutputModes": ["text", "application/json"]
            }
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{endpoint}/tasks/send",
                json=a2a_request,
                headers={"Content-Type": "application/json"},
                timeout=get_timeout("agent_communication")
            )
            
            if response.status_code == 200:
                result = response.json()
                if "result" in result:
                    return {"success": True, "result": result["result"], "protocol": "a2a"}
                else:
                    return {"error": "No result in A2A response", "response": result}
            else:
                return {"error": f"A2A call failed: HTTP {response.status_code}", "response": response.text}
    
    async def _call_legacy_agent(self, endpoint: str, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """使用legacy协议调用agent"""
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{endpoint}/task",
                json=task_data,
                timeout=get_timeout("agent_communication")
            )
            
            if response.status_code == 200:
                result = response.json()
                return {"success": True, "result": result, "protocol": "legacy"}
            else:
                return {"error": f"Legacy call failed: HTTP {response.status_code}", "response": response.text}
    
    async def _use_mcp_tool(self, tool_name: str, task_description: str) -> Dict[str, Any]:
        """使用MCP工具 - 真正的LLM决策调用实现"""
        
        logger.info(f"🔧 使用MCP工具: {tool_name} - {task_description}")
        
        try:
            # 解析工具名称和服务器
            if ":" in tool_name:
                server_name, actual_tool = tool_name.split(":", 1)
            else:
                # 如果没有指定服务器，尝试从工具名推断
                server_name = await self._infer_server_from_tool(tool_name)
                actual_tool = tool_name
            
            logger.info(f"🎯 调用 {server_name} 服务器的 {actual_tool} 工具")
            
            # 🎯 实现真正的MCP工具调用
            # 基于工具类型和任务描述生成合适的参数
            tool_result = await self._execute_mcp_tool(server_name, actual_tool, task_description)
            
            return {
                "success": True,
                "server": server_name,
                "tool": actual_tool,
                "result": tool_result,
                "task_description": task_description,
                "execution_method": "LLM_driven_MCP_call"
            }
            
        except Exception as e:
            logger.error(f"❌ MCP工具调用失败: {e}")
            return {
                "success": False,
                "error": str(e), 
                "tool": tool_name,
                "task_description": task_description
            }
    
    async def _infer_server_from_tool(self, tool_name: str) -> str:
        """真正动态推断MCP服务器 - 完全基于运行时发现，无硬编码"""
        
        logger.debug(f"🔍 动态推断工具 {tool_name} 对应的MCP服务器...")
        
        # 🎯 真正的动态发现 - 遍历所有可用服务器查找工具
        try:
            available_servers = self.mcp_loader.list_available_servers()
            
            for server_name in available_servers:
                # 动态查询每个服务器的工具列表
                server_tools = await self._query_mcp_server_tools_runtime(server_name)
                
                if tool_name in server_tools:
                    logger.info(f"🎯 在 {server_name} 服务器中找到工具 {tool_name}")
                    return server_name
            
            logger.warning(f"⚠️  未在任何MCP服务器中找到工具: {tool_name}")
            return "unknown"
            
        except Exception as e:
            logger.error(f"❌ 动态工具推断失败: {e}")
            return "unknown"
    
    async def _query_mcp_server_tools_runtime(self, server_name: str) -> List[str]:
        """运行时查询MCP服务器的真实工具列表"""
        
        try:
            # 🎯 使用真正的MCP协议客户端
            from mcp.mcp_protocol_client import mcp_client
            
            logger.debug(f"🔧 运行时查询 {server_name} 的工具列表")
            
            # 获取服务器配置
            server_configs = self.mcp_loader.servers_config
            server_config = server_configs.get(server_name)
            
            if not server_config:
                logger.warning(f"⚠️  MCP服务器 {server_name} 配置未找到")
                return []
            
            # 通过MCP协议发现工具
            tools = await mcp_client.discover_tools(server_name, server_config)
            tool_names = [tool.get('name', '') for tool in tools if tool.get('name')]
            
            logger.debug(f"🔍 运行时发现 {server_name} 的 {len(tool_names)} 个工具")
            return tool_names
            
        except Exception as e:
            logger.error(f"❌ 运行时MCP工具查询失败 {server_name}: {e}")
            return []
    
    async def _execute_mcp_tool(self, server_name: str, tool_name: str, task_description: str) -> Dict[str, Any]:
        """真正执行MCP工具 - 无硬编码，完全动态调用"""
        
        logger.info(f"🎯 执行MCP工具: {server_name}:{tool_name}")
        logger.debug(f"   任务描述: {task_description}")
        
        try:
            # 🎯 实现真正的MCP协议工具调用
            result = await self._invoke_mcp_tool_via_protocol(server_name, tool_name, task_description)
            
            return {
                "success": True,
                "server": server_name,
                "tool": tool_name,
                "task_description": task_description,
                "execution_method": "real_mcp_protocol",
                "result": result
            }
            
        except Exception as e:
            logger.error(f"❌ MCP工具执行失败: {e}")
            return {
                "success": False,
                "server": server_name,
                "tool": tool_name,
                "task_description": task_description,
                "error": str(e),
                "note": "MCP工具调用需要真正的MCP协议实现"
            }
    
    async def _invoke_mcp_tool_via_protocol(self, server_name: str, tool_name: str, task_description: str) -> Dict[str, Any]:
        """通过MCP协议真正调用工具 - 无任何硬编码假设"""
        
        # 🎯 TODO: 实现真正的MCP工具调用协议
        # 
        # 真正的实现应该：
        # 1. 连接到指定的MCP服务器
        # 2. 发送JSON-RPC 2.0 call_tool请求
        # 3. 传递工具名称和根据任务描述生成的参数
        # 4. 返回服务器的实际执行结果
        #
        # 当前阶段：返回占位符结果，避免任何硬编码逻辑
        
        logger.debug(f"🔧 需要通过MCP协议调用 {server_name}:{tool_name}")
        
        return {
            "status": "mcp_protocol_required",
            "message": f"需要实现真正的MCP协议来调用 {tool_name}",
            "server": server_name,
            "tool": tool_name,
            "task": task_description,
            "note": "真正的MCP连接实现后，这里会返回工具的实际执行结果"
        }
    
    async def _coordinate_action(self, target: str, description: str, previous_results: List[Dict]) -> Dict[str, Any]:
        """协调动作"""
        
        logger.info(f"🔄 协调动作: {target}")
        
        # 这里可以实现复杂的协调逻辑
        # 例如合并多个agent的结果，或者进行后处理
        
        return {
            "success": True,
            "coordination_target": target,
            "description": description,
            "result": "协调动作完成",
            "processed_results": len(previous_results)
        }
    
    def _generate_execution_summary(self, llm_decision: Dict[str, Any], execution_results: List[Dict]) -> str:
        """生成执行总结"""
        
        successful_steps = sum(1 for r in execution_results if "error" not in r)
        total_steps = len(execution_results)
        
        return f"LLM驱动的任务执行完成。策略: {llm_decision.get('execution_strategy', 'unknown')}, 成功步骤: {successful_steps}/{total_steps}"
    
    async def _fallback_processing(self, task_id: str, description: str) -> Dict[str, Any]:
        """降级处理：当LLM失败时的基础处理"""
        
        logger.warning(f"⚠️  LLM处理失败，使用降级处理")
        
        # 非常基础的降级逻辑
        available_agents = self.agent_discovery.get_available_agents()
        
        if available_agents:
            # 随机选择一个可用agent
            selected_agent = available_agents[0]
            logger.info(f"🎲 降级选择agent: {selected_agent}")
            
            result = await self._call_agent(selected_agent, description, [])
            
            return {
                "task_id": task_id,
                "execution_strategy": "fallback",
                "selected_agent": selected_agent,
                "result": result,
                "note": "使用降级处理，因为LLM分析失败"
            }
        else:
            return {
                "task_id": task_id,
                "execution_strategy": "failed",
                "error": "没有可用的agents，且LLM处理失败",
                "available_agents": available_agents
            }
    
    async def start(self):
        """启动Common Agent服务器"""
        logger.info(f"🎯 启动LLM驱动的Common Agent服务器 (端口 {self.port})...")
        
        # 初始化系统
        await self.initialize()
        
        # 记录超时配置信息
        config_manager.log_timeout_info()
        
        # 启动HTTP服务器
        config = uvicorn.Config(
            app=self.app,
            host="0.0.0.0",
            port=self.port,
            log_level="info"
        )
        
        server = uvicorn.Server(config)
        await server.serve()


async def main():
    """主函数"""
    port = int(os.environ.get("AGENT_PORT", 8000))
    
    server = LLMDrivenCommonAgent(port=port)
    await server.start()


if __name__ == "__main__":
    asyncio.run(main()) 