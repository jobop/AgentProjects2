"""
Common Agent 路由模块
将URL路由代码与主业务逻辑分离
"""

import os
import json
import asyncio
import httpx
from datetime import datetime
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse, FileResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import logging

logger = logging.getLogger(__name__)


class CommonAgentRoutes:
    """Common Agent 路由管理器"""
    
    def __init__(self, app: FastAPI, agent_instance):
        """
        初始化路由管理器
        
        Args:
            app: FastAPI应用实例
            agent_instance: Common Agent实例，用于访问业务逻辑
        """
        self.app = app
        self.agent = agent_instance
        self.setup_cors()
        self.setup_routes()
    
    def setup_cors(self):
        """设置CORS中间件"""
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    
    def setup_routes(self):
        """设置所有路由"""
        self.setup_web_ui_routes()
        self.setup_api_routes()
        self.setup_admin_routes()
    
    def setup_web_ui_routes(self):
        """设置Web界面路由"""
        
        @self.app.get("/")
        async def web_ui():
            """提供Web界面"""
            # 查找web_ui.html文件
            ui_file = os.path.join(os.path.dirname(__file__), "../../web_ui.html")
            ui_file = os.path.abspath(ui_file)
            
            if os.path.exists(ui_file):
                return FileResponse(ui_file, media_type="text/html")
            else:
                # 如果文件不存在，返回简单的HTML
                return JSONResponse({
                    "message": "多Agent系统Web界面",
                    "endpoints": {
                        "status": "/status",
                        "task": "/task",
                        "health": "/health"
                    },
                    "note": "请确保web_ui.html文件存在于项目根目录"
                })
    
    def setup_api_routes(self):
        """设置API路由"""
        
        @self.app.get("/health")
        async def health_check():
            """健康检查"""
            return JSONResponse({
                "status": "healthy",
                "agent": "LLM-Driven Common Agent",
                "timestamp": datetime.now().isoformat(),
                "llm_ready": self.agent.llm_client is not None,
                "discovered_agents": len(self.agent.agent_discovery.discovered_agents)
            })
        
        @self.app.get("/status")
        async def get_status():
            """获取系统状态"""
            discovered_agents = {}
            for agent_id, agent_info in self.agent.agent_discovery.discovered_agents.items():
                # 检查agent是否在线
                try:
                    async with httpx.AsyncClient() as client:
                        response = await client.get(f"{agent_info['endpoint']}/health", timeout=5.0)
                        discovered_agents[agent_id] = {
                            "status": "online" if response.status_code == 200 else "error",
                            "endpoint": agent_info["endpoint"],
                            "protocol": agent_info.get("protocol", "unknown"),
                            "capabilities": self.agent.agent_discovery.get_agent_capabilities(agent_id)
                        }
                except:
                    discovered_agents[agent_id] = {
                        "status": "offline",
                        "endpoint": agent_info["endpoint"],
                        "protocol": agent_info.get("protocol", "unknown")
                    }
            
            return JSONResponse({
                "common_agent": "running",
                "llm_client": "ready" if self.agent.llm_client else "not_ready",
                "discovered_agents": discovered_agents,
                "active_tasks": len(self.agent.active_tasks),
                "mcp_servers": len(self.agent.mcp_loader.list_available_servers())
            })
        
        @self.app.post("/task")
        async def submit_task(task_data: dict, request: Request):
            """
            提交任务给LLM驱动的Common Agent
            
            支持JSON响应（默认）和SSE流式响应（Accept: text/event-stream）
            """
            
            # 检查是否请求流式响应
            accept_header = request.headers.get("accept", "")
            is_streaming = "text/event-stream" in accept_header
            
            task_id = f"task_{self.agent.task_counter}"
            self.agent.task_counter += 1
            
            description = task_data.get("description", "")
            if not description:
                if is_streaming:
                    async def error_stream():
                        yield f"data: {json.dumps({'error': 'Task description is required'})}\n\n"
                    return StreamingResponse(error_stream(), media_type="text/event-stream")
                else:
                    raise HTTPException(status_code=400, detail="Task description is required")
            
            logger.info(f"🎯 收到新任务 {task_id}: {description}")
            
            # 存储任务
            self.agent.active_tasks[task_id] = {
                "id": task_id,
                "data": task_data,
                "status": "processing", 
                "created_at": datetime.now().isoformat(),
                "steps": []
            }
            
            if is_streaming:
                # SSE流式响应
                async def task_stream():
                    """SSE流式任务处理"""
                    try:
                        # 发送任务开始事件
                        yield f"data: {json.dumps({'event': 'task_started', 'task_id': task_id, 'description': description})}\n\n"
                        
                        # 通过LLM流式处理任务
                        async for event in self.agent.process_task_with_llm_stream(task_id, task_data):
                            yield f"data: {json.dumps(event)}\n\n"
                        
                        # 发送任务完成事件
                        task = self.agent.active_tasks[task_id]
                        total_steps = len(task.get("steps", []))
                        successful_steps = len([s for s in task.get("steps", []) if "error" not in s.get("result", {})])
                        failed_steps = total_steps - successful_steps
                        
                        # 计算总执行时间
                        created_at = datetime.fromisoformat(task.get("created_at", datetime.now().isoformat()))
                        completed_at = datetime.fromisoformat(task.get("completed_at", datetime.now().isoformat()))
                        total_duration = (completed_at - created_at).total_seconds() * 1000
                        
                        # 收集执行统计
                        execution_stats = {
                            "total_steps": total_steps,
                            "successful_steps": successful_steps,
                            "failed_steps": failed_steps,
                            "total_duration": total_duration,
                            "agents_used": [],
                            "tools_used": []
                        }
                        
                        # 分析使用的agents和工具
                        for step in task.get("steps", []):
                            if step.get("action") == "agent_call":
                                execution_stats["agents_used"].append(step.get("target", ""))
                            elif step.get("action") == "tool_use":
                                execution_stats["tools_used"].append(step.get("target", ""))
                        
                        # 去重
                        execution_stats["agents_used"] = list(set(execution_stats["agents_used"]))
                        execution_stats["tools_used"] = list(set(execution_stats["tools_used"]))
                        
                        task_completed_data = {
                            'event': 'task_completed', 
                            'task_id': task_id, 
                            'total_steps': total_steps, 
                            'successful_steps': successful_steps, 
                            'failed_steps': failed_steps,
                            'duration': total_duration,
                            'execution_stats': execution_stats,
                            'final_result': task.get("result", {})
                        }
                        yield f"data: {json.dumps(task_completed_data)}\n\n"
                        
                    except Exception as e:
                        logger.error(f"❌ 任务处理错误: {e}")
                        yield f"data: {json.dumps({'event': 'error', 'error': str(e)})}\n\n"
                
                return StreamingResponse(
                    task_stream(),
                    media_type="text/event-stream",
                    headers={
                        "Cache-Control": "no-cache",
                        "Connection": "keep-alive",
                        "Access-Control-Allow-Origin": "*",
                    }
                )
            else:
                # 普通JSON响应 
                try:
                    result = await self.agent.process_task_with_llm(task_id, task_data)
                    
                    return JSONResponse({
                        "task_id": task_id,
                        "status": "completed",
                        "result": result
                    })
                    
                except Exception as e:
                    logger.error(f"❌ 任务处理错误: {e}")
                    raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/task/{task_id}")
        async def get_task_status(task_id: str):
            """获取任务状态"""
            if task_id not in self.agent.active_tasks:
                raise HTTPException(status_code=404, detail="Task not found")
            return JSONResponse(self.agent.active_tasks[task_id])
    
    def setup_admin_routes(self):
        """设置管理员路由"""
        
        @self.app.post("/admin/rediscover")
        async def rediscover_agents():
            """重新发现agents"""
            try:
                logger.info("🔄 开始重新发现agents...")
                await self.agent.agent_discovery.discover_agents(self.agent.discovery_endpoints)
                discovered_count = len(self.agent.agent_discovery.discovered_agents)
                logger.info(f"✅ 重新发现完成，找到 {discovered_count} 个agents")
                return JSONResponse({
                    "success": True,
                    "message": f"重新发现完成，找到 {discovered_count} 个agents",
                    "discovered_agents": list(self.agent.agent_discovery.discovered_agents.keys())
                })
            except Exception as e:
                logger.error(f"❌ 重新发现失败: {e}")
                return JSONResponse({
                    "success": False,
                    "error": str(e)
                }, status_code=500)
        
        @self.app.get("/admin/agents")
        async def get_agents_info(agent_id: Optional[str] = None):
            """获取Agent信息 - 支持查询单个Agent或所有Agent"""
            if agent_id:
                # 获取单个Agent详细信息
                if agent_id not in self.agent.agent_discovery.discovered_agents:
                    return JSONResponse({
                        "error": f"Agent {agent_id} not found"
                    }, status_code=404)
                
                agent_info = self.agent.agent_discovery.discovered_agents[agent_id]
                
                # 检查agent是否在线
                try:
                    async with httpx.AsyncClient() as client:
                        response = await client.get(f"{agent_info['endpoint']}/health", timeout=5.0)
                        status = "online" if response.status_code == 200 else "error"
                except:
                    status = "offline"
                
                # 获取详细信息
                try:
                    async with httpx.AsyncClient() as client:
                        # 尝试获取A2A agent信息
                        a2a_response = await client.get(f"{agent_info['endpoint']}/a2a/agent.json", timeout=5.0)
                        if a2a_response.status_code == 200:
                            a2a_info = a2a_response.json()
                            detailed_info = {
                                "name": a2a_info.get("name", agent_id),
                                "description": a2a_info.get("description", ""),
                                "version": a2a_info.get("version", ""),
                                "url": a2a_info.get("url", agent_info["endpoint"]),
                                "capabilities": a2a_info.get("skills", []),
                                "capabilities_info": a2a_info.get("capabilities", {})
                            }
                        else:
                            detailed_info = {
                                "name": agent_id,
                                "description": "Agent information not available",
                                "capabilities": self.agent.agent_discovery.get_agent_capabilities(agent_id)
                            }
                except:
                    detailed_info = {
                        "name": agent_id,
                        "description": "Agent information not available",
                        "capabilities": self.agent.agent_discovery.get_agent_capabilities(agent_id)
                    }
                
                return JSONResponse({
                    "agent": {
                        "id": agent_id,
                        "status": status,
                        "endpoint": agent_info["endpoint"],
                        "protocol": agent_info.get("protocol", "unknown"),
                        "capabilities": detailed_info.get("capabilities", []),
                        "capabilities_info": detailed_info.get("capabilities_info", {}),
                        "name": detailed_info.get("name", agent_id),
                        "description": detailed_info.get("description", ""),
                        "version": detailed_info.get("version", ""),
                        "url": detailed_info.get("url", agent_info["endpoint"])
                    }
                })
            else:
                # 获取所有Agent信息
                agents_info = {}
                for agent_id, agent_info in self.agent.agent_discovery.discovered_agents.items():
                    # 检查agent是否在线
                    try:
                        async with httpx.AsyncClient() as client:
                            response = await client.get(f"{agent_info['endpoint']}/health", timeout=5.0)
                            status = "online" if response.status_code == 200 else "error"
                    except:
                        status = "offline"
                    
                    agents_info[agent_id] = {
                        "status": status,
                        "endpoint": agent_info["endpoint"],
                        "protocol": agent_info.get("protocol", "unknown"),
                        "capabilities": self.agent.agent_discovery.get_agent_capabilities(agent_id),
                        "info": self.agent.agent_discovery.get_agent_info(agent_id)
                    }
                
                return JSONResponse({
                    "agents": agents_info,
                    "total_count": len(agents_info)
                })
        
        @self.app.get("/admin/mcp-servers")
        async def get_mcp_servers():
            """获取MCP服务器信息"""
            servers = self.agent.mcp_loader.list_available_servers()
            return JSONResponse({
                "servers": servers,
                "total_count": len(servers)
            }) 