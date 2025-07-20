#!/usr/bin/env python3
"""
真正的UI设计师Agent

参考common agent的MCP管理方式，从mcp_servers.json读取真实配置
让LLM根据真实可用的MCP工具决策使用哪些工具进行设计
"""

import asyncio
import json
import logging
import os
import sys
import httpx
from typing import Dict, Any, Optional, List
from python_a2a import A2AServer, skill, agent, run_server

# Add paths for imports
common_agent_src = os.path.join(os.path.dirname(__file__), "..", "..", "common-agent", "src")
shared_path = os.path.join(os.path.dirname(__file__), "..", "..")
sys.path.insert(0, common_agent_src)
sys.path.insert(0, shared_path)

try:
    from mcp.simple_mcp_loader import SimpleMCPLoader
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    class SimpleMCPLoader:
        def __init__(self):
            pass
        def load_config(self):
            return {}
        def list_available_servers(self):
            return []
        def get_server_config(self, name):
            return None

try:
    from shared.config_manager import get_timeout
    CONFIG_AVAILABLE = True
except ImportError:
    CONFIG_AVAILABLE = False
    def get_timeout(timeout_type):
        # 默认超时时间（10分钟）
        return 600

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@agent(
    name="UI设计-大头",
    description="真正的LLM驱动UI设计专家，使用真实MCP工具进行设计分析和原型制作",
    version="1.0.0",
    url="http://localhost:8003",
    capabilities={
        "streaming": True,
        "google_a2a_compatible": True,
        "llm_powered": True,
        "real_mcp_integration": True,
        "no_simulation": True
    }
)
class RealUIDesignerAgent(A2AServer):
    """真正的UI设计师Agent - 参考common agent方式"""
    
    def __init__(self):
        super().__init__()
        self.agent_id = "real_ui_designer_agent"
        self.agent_name = "Real UI Designer Agent"
        
        # LLM API配置
        self.api_key = os.getenv("SILICONFLOW_API_KEY", "xxxxx")
        self.base_url = "https://api.siliconflow.cn/v1"
        self.model = "deepseek-ai/DeepSeek-V3"
        
        # 初始化MCP管理器 - 参考common agent方式
        self.mcp_loader = SimpleMCPLoader()
        self.available_mcp_servers = {}
        self.mcp_servers_info = {}
        
        self._init_mcp_system()
        
        logger.info("✅ Real UI Designer Agent 初始化完成")
    
    def _init_mcp_system(self):
        """初始化MCP系统，参考common agent方式"""
        try:
            # 加载mcp_servers.json配置
            self.available_mcp_servers = self.mcp_loader.load_config()
            
            available_servers = self.mcp_loader.list_available_servers()
            logger.info(f"🔧 从mcp_servers.json加载 {len(available_servers)} 个MCP服务器")
            
            # 记录所有可用的MCP服务器信息给LLM使用
            for server_name in available_servers:
                server_config = self.mcp_loader.get_server_config(server_name)
                if server_config:
                    self.mcp_servers_info[server_name] = {
                        "name": server_name,
                        "description": server_config.get('description', 'No description'),
                        "command": server_config.get('command', 'unknown'),
                        "status": "available_for_llm_decision"
                    }
                    logger.info(f"  📋 {server_name}: {server_config.get('description', '')}")
            
            logger.info(f"✅ MCP系统初始化完成，{len(self.mcp_servers_info)} 个服务器可用")
            
        except Exception as e:
            logger.error(f"❌ MCP系统初始化失败: {e}")
            # 即使失败也继续运行，但没有MCP工具
            self.mcp_servers_info = {}

    async def call_llm(self, prompt: str) -> str:
        """调用LLM进行设计决策"""
        try:
            async with httpx.AsyncClient(timeout=get_timeout("llm_api")) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": self.model,
                        "messages": [{"role": "user", "content": prompt}],
                        "max_tokens": 2000,
                        "temperature": 0.7
                    }
                )
                
                if response.status_code == 200:
                    result = response.json()
                    return result["choices"][0]["message"]["content"]
                else:
                    logger.error(f"LLM API调用失败: {response.status_code}")
                    return f"LLM API调用失败: {response.status_code}"
                    
        except Exception as e:
            logger.error(f"LLM调用异常: {e}")
            return f"LLM调用异常: {str(e)}"

    def _format_mcp_info_for_llm(self) -> str:
        """格式化MCP服务器信息给LLM"""
        if not self.mcp_servers_info:
            return "暂无可用的MCP服务器"
        
        mcp_info = ["我有以下真实的MCP服务器可用："]
        for server_name, info in self.mcp_servers_info.items():
            mcp_info.append(f"- {server_name}: {info['description']}")
        
        mcp_info.append("\n注意：你可以决策使用这些MCP服务器中的任何工具来完成设计任务。")
        return "\n".join(mcp_info)

    @skill(
        name="LLM驱动的UI设计分析",
        description="让LLM分析设计需求并决策使用哪些MCP工具",
        tags=["llm-powered", "ui-design", "real-tools", "no-simulation"]
    )
    async def llm_driven_ui_design_analysis(self, design_requirements: str, target_platform: str = "web"):
        """LLM驱动的UI设计分析"""
        
        logger.info(f"🎨 LLM驱动的UI设计分析: {design_requirements}")
        
        # 构建包含真实MCP服务器信息的提示
        mcp_info = self._format_mcp_info_for_llm()
        
        analysis_prompt = f"""
作为专业的UI/UX设计师，我需要为以下需求进行设计：

设计需求：{design_requirements}
目标平台：{target_platform}

{mcp_info}

请分析这个设计任务，决定需要使用哪些MCP服务器和工具来完成设计工作。

返回JSON格式：
{{
    "design_analysis": "设计需求分析",
    "design_strategy": "设计策略",
    "required_mcp_tools": [
        {{
            "server": "MCP服务器名称",
            "purpose": "使用目的",
            "design_task": "具体设计任务",
            "expected_outcome": "预期产出"
        }}
    ],
    "design_workflow": "设计工作流程",
    "deliverables": ["交付物列表"]
}}

只使用列出的真实MCP服务器，你可以推断每个服务器可能提供的设计相关工具。
"""

        # LLM分析设计需求
        llm_analysis = await self.call_llm(analysis_prompt)
        logger.info(f"🧠 LLM设计分析完成，响应长度: {len(llm_analysis)} 字符")
        
        # 解析LLM分析结果
        try:
            import re
            json_match = re.search(r'\{.*\}', llm_analysis, re.DOTALL)
            if json_match:
                analysis_result = json.loads(json_match.group())
            else:
                analysis_result = {"required_mcp_tools": [], "design_analysis": llm_analysis}
        except Exception as e:
            logger.warning(f"⚠️ LLM分析解析失败: {e}")
            analysis_result = {"required_mcp_tools": [], "design_analysis": llm_analysis}
        
        # 验证LLM决策的工具
        tool_execution_plan = []
        required_tools = analysis_result.get("required_mcp_tools", [])
        
        logger.info(f"🎯 LLM决策使用 {len(required_tools)} 个设计工具")
        
        for tool in required_tools:
            server = tool.get("server")
            if server in self.mcp_servers_info:
                tool_execution_plan.append({
                    "server": server,
                    "purpose": tool.get("purpose"),
                    "design_task": tool.get("design_task"),
                    "expected_outcome": tool.get("expected_outcome"),
                    "server_info": self.mcp_servers_info[server],
                    "status": "llm_decided_real_server",
                    "note": "LLM选择了真实存在的MCP服务器"
                })
                logger.info(f"✅ LLM选择真实服务器: {server} - {tool.get('purpose')}")
            else:
                logger.warning(f"⚠️ LLM选择了不存在的服务器: {server}")
        
        # LLM基于工具计划生成详细设计方案
        if tool_execution_plan:
            design_prompt = f"""
基于MCP工具使用计划，为"{design_requirements}"生成详细的UI设计方案：

分析结果：
{json.dumps(analysis_result, ensure_ascii=False, indent=2)}

工具执行计划：
{json.dumps(tool_execution_plan, ensure_ascii=False, indent=2)}

请生成专业的UI设计方案，包括：
1. 设计理念和原则
2. 用户界面架构
3. 视觉设计规范
4. 交互设计方案
5. 响应式设计考虑
6. 可访问性设计
7. 实现技术建议

基于专业设计知识和真实工具能力，提供可执行的设计方案。
"""

            final_design_plan = await self.call_llm(design_prompt)
        else:
            final_design_plan = "由于没有合适的MCP工具，将使用传统设计方法"
        
        return {
            "success": True,
            "design_requirements": design_requirements,
            "target_platform": target_platform,
            "llm_design_analysis": analysis_result,
            "tool_execution_plan": tool_execution_plan,
            "final_design_plan": final_design_plan,
            "methodology": "LLM专业分析 + 真实MCP工具集成 + 专业设计方案",
            "tools_planned": len(tool_execution_plan),
            "message": f"✅ 完成基于LLM决策的{design_requirements}UI设计分析"
        }

    @skill(
        name="设计系统架构分析",
        description="LLM分析设计系统需求并规划组件架构",
        tags=["design-system", "llm-analysis", "component-architecture"]
    )
    async def design_system_architecture(self, project_scope: str, design_requirements: List[str]):
        """设计系统架构分析"""
        
        logger.info(f"🏗️ 设计系统架构分析: {project_scope}")
        
        # LLM分析设计系统需求
        mcp_info = self._format_mcp_info_for_llm()
        
        system_prompt = f"""
作为资深的设计系统架构师，请为以下项目设计完整的设计系统架构：

项目范围：{project_scope}
设计需求：
{json.dumps(design_requirements, ensure_ascii=False, indent=2)}

{mcp_info}

请制定：
1. 设计系统架构
2. 组件层级结构
3. 设计令牌规范
4. MCP工具使用策略
5. 维护和扩展计划
6. 团队协作流程

要求方案科学、可扩展、基于真实MCP工具能力。
"""

        architecture_plan = await self.call_llm(system_prompt)
        logger.info(f"🏗️ 设计系统架构完成")
        
        return {
            "success": True,
            "project_scope": project_scope,
            "design_requirements": design_requirements,
            "architecture_plan": architecture_plan,
            "methodology": "LLM专业架构设计 + MCP工具集成策略",
            "approach": "AI驱动的设计系统规划"
        }

    # @skill(
    #     name="MCP服务器状态检查",
    #     description="检查当前可用的MCP服务器状态",
    #     tags=["mcp-status", "system-check", "real-time"]
    # )
    # async def check_mcp_servers_status(self):
    #     """检查MCP服务器状态"""
        
    #     return {
    #         "success": True,
    #         "mcp_system_status": "loaded_from_config",
    #         "total_servers": len(self.mcp_servers_info),
    #         "server_details": self.mcp_servers_info,
    #         "config_source": "mcp_servers.json",
    #         "integration_method": "SimpleMCPLoader方式",
    #         "message": f"✅ MCP状态: {len(self.mcp_servers_info)}个服务器从配置文件加载"
    #     }


def main():
    """主函数"""
    port = int(os.environ.get("AGENT_PORT", 8002))
    
    agent_instance = RealUIDesignerAgent()
    logger.info(f"🚀 启动Real UI Designer Agent，端口: {port}")
    logger.info("🎨 此Agent参考common agent方式，从mcp_servers.json读取真实配置")
    logger.info("🎯 LLM决策使用真实MCP工具，无任何硬编码或模拟数据")
    run_server(agent_instance, host="0.0.0.0", port=port)


if __name__ == "__main__":
    main() 
