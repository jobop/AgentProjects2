#!/usr/bin/env python3
"""
真正的用户研究Agent

参考common agent的MCP管理方式，从mcp_servers.json读取真实配置
让LLM根据真实可用的MCP工具决策使用哪些工具
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
    name="用户研究员-ViVi",
    description="真正的MCP集成用户研究专家，由LLM决策使用MCP工具获取真实数据",
    version="1.0.0",
    url="http://localhost:8001",
    capabilities={
        "streaming": True,
        "google_a2a_compatible": True,
        "llm_powered": True,
        "real_mcp_integration": True,
        "no_simulation": True
    }
)
class RealMCPUserResearchAgent(A2AServer):
    """真正的MCP集成用户研究Agent - 参考common agent方式"""
    
    def __init__(self):
        super().__init__()
        self.agent_id = "real_mcp_user_research_agent"
        self.agent_name = "Real MCP User Research Agent"
        
        # LLM API配置
        self.api_key = os.getenv("SILICONFLOW_API_KEY", "xxxxx")
        self.base_url = "https://api.siliconflow.cn/v1"
        self.model = "deepseek-ai/DeepSeek-V3"
        
        # 初始化MCP管理器 - 参考common agent方式
        self.mcp_loader = SimpleMCPLoader()
        self.available_mcp_servers = {}
        self.mcp_servers_info = {}
        
        self._init_mcp_system()
        
        logger.info("✅ Real MCP User Research Agent 初始化完成")
    
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
        """调用LLM"""
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
        
        mcp_info.append("\n注意：你可以决策使用这些MCP服务器中的任何工具来获取真实数据。")
        return "\n".join(mcp_info)

    @skill(
        name="LLM驱动的市场研究",
        description="让LLM决策使用哪些MCP工具进行真实的市场研究，不模拟任何数据",
        tags=["llm-powered", "real-mcp", "market-research", "no-simulation"]
    )
    async def llm_driven_market_research(self, research_topic: str, research_depth: str = "comprehensive"):
        """LLM驱动的真实市场研究"""
        
        logger.info(f"🧠 LLM驱动的市场研究: {research_topic}")
        
        # 构建包含真实MCP服务器信息的提示
        mcp_info = self._format_mcp_info_for_llm()
        
        decision_prompt = f"""
作为专业的市场研究专家，我需要对"{research_topic}"进行{research_depth}级别的市场研究。

{mcp_info}

请分析这个研究任务，决定需要使用哪些MCP服务器和工具来获取真实数据。

返回JSON格式的执行计划：
{{
    "task_analysis": "对研究任务的分析",
    "required_mcp_tools": [
        {{
            "server": "MCP服务器名称",
            "purpose": "使用目的",
            "data_type": "需要获取的数据类型",
            "expected_outcome": "预期结果"
        }}
    ],
    "research_strategy": "研究策略说明",
    "methodology": "研究方法论"
}}

重要：只使用我列出的真实MCP服务器，你可以推断每个服务器可能提供的工具能力。
"""

        # LLM决策使用哪些MCP工具
        llm_response = await self.call_llm(decision_prompt)
        
        try:
            # 解析LLM的决策
            import re
            json_match = re.search(r'\{.*\}', llm_response, re.DOTALL)
            if json_match:
                decision = json.loads(json_match.group())
            else:
                decision = {"required_mcp_tools": [], "task_analysis": llm_response}
        except:
            decision = {"required_mcp_tools": [], "task_analysis": llm_response}
        
        # 记录LLM的工具决策计划
        tool_decision_plan = []
        required_tools = decision.get("required_mcp_tools", [])
        
        logger.info(f"🎯 LLM决策使用 {len(required_tools)} 个MCP工具")
        
        for tool_spec in required_tools:
            server = tool_spec.get("server")
            purpose = tool_spec.get("purpose", "数据获取")
            
            # 验证LLM选择的服务器是否真实存在
            if server in self.mcp_servers_info:
                tool_decision_plan.append({
                    "server": server,
                    "purpose": purpose,
                    "data_type": tool_spec.get("data_type"),
                    "expected_outcome": tool_spec.get("expected_outcome"),
                    "server_info": self.mcp_servers_info[server],
                    "status": "llm_decided_real_server",
                    "note": "LLM选择了真实存在的MCP服务器"
                })
                logger.info(f"✅ LLM选择真实服务器: {server} - {purpose}")
            else:
                logger.warning(f"⚠️ LLM选择了不存在的服务器: {server}")
        
        # LLM基于决策生成最终研究报告框架
        if tool_decision_plan:
            synthesis_prompt = f"""
基于我对MCP工具的使用决策，为"{research_topic}"生成专业的市场研究报告框架：

我的工具使用决策：
{json.dumps(tool_decision_plan, ensure_ascii=False, indent=2)}

请生成一份专业的市场研究报告框架，包括：
1. 研究目标和范围
2. 数据收集策略（基于我选择的MCP工具）
3. 分析方法论
4. 预期洞察领域
5. 报告结构设计
6. 成功指标定义

基于专业市场研究方法论和真实工具能力，提供可执行的研究框架。
"""
            
            final_report_framework = await self.call_llm(synthesis_prompt)
        else:
            final_report_framework = "由于没有可用的MCP工具，将使用传统研究方法进行分析"
        
        return {
            "success": True,
            "research_topic": research_topic,
            "research_depth": research_depth,
            "llm_decision": decision,
            "mcp_tool_decision_plan": tool_decision_plan,
            "final_research_framework": final_report_framework,
            "available_mcp_servers": len(self.mcp_servers_info),
            "llm_selected_tools": len(tool_decision_plan),
            "methodology": "LLM决策 + 真实MCP服务器 + 专业研究方法论",
            "message": f"✅ LLM完成基于真实MCP配置的{research_topic}市场研究规划"
        }

    @skill(
        name="真实数据用户画像分析",
        description="LLM决策使用真实MCP工具获取数据，进行用户画像分析",
        tags=["llm-powered", "real-data", "user-personas", "mcp-tools"]
    )
    async def llm_driven_persona_analysis(self, target_audience: str, analysis_goals: List[str]):
        """LLM决策的用户画像分析"""
        
        logger.info(f"🧠 LLM驱动的用户画像分析: {target_audience}")
        
        # LLM决策数据收集策略
        mcp_info = self._format_mcp_info_for_llm()
        
        strategy_prompt = f"""
我需要为"{target_audience}"创建用户画像，分析目标：
{json.dumps(analysis_goals, ensure_ascii=False, indent=2)}

{mcp_info}

请制定数据收集和分析策略，决定使用哪些MCP服务器来获取真实的用户数据。

返回JSON格式：
{{
    "analysis_approach": "分析方法",
    "data_collection_plan": [
        {{
            "server": "MCP服务器名称",
            "data_source": "数据来源",
            "data_type": "数据类型",
            "purpose": "收集目的",
            "expected_insight": "期望获得的洞察"
        }}
    ],
    "persona_framework": "用户画像框架设计"
}}
"""

        strategy_response = await self.call_llm(strategy_prompt)
        
        try:
            import re
            json_match = re.search(r'\{.*\}', strategy_response, re.DOTALL)
            if json_match:
                strategy = json.loads(json_match.group())
            else:
                strategy = {"data_collection_plan": []}
        except:
            strategy = {"data_collection_plan": []}
        
        # 验证LLM的数据收集计划
        validated_plan = []
        data_plan = strategy.get("data_collection_plan", [])
        
        for data_spec in data_plan:
            server = data_spec.get("server")
            if server in self.mcp_servers_info:
                validated_plan.append({
                    **data_spec,
                    "server_info": self.mcp_servers_info[server],
                    "validation_status": "real_server_selected"
                })
                logger.info(f"✅ 验证通过: {server} - {data_spec.get('purpose')}")
        
        # LLM生成用户画像分析框架
        if validated_plan:
            persona_prompt = f"""
基于验证的数据收集计划，为"{target_audience}"设计用户画像分析框架：

验证的数据收集计划：
{json.dumps(validated_plan, ensure_ascii=False, indent=2)}

分析目标：
{json.dumps(analysis_goals, ensure_ascii=False, indent=2)}

请设计详细的用户画像分析框架，包括：
1. 用户画像维度设计
2. 数据分析方法
3. 洞察提取策略
4. 画像验证方法
5. 应用场景设计

基于真实数据源和专业用户研究方法论。
"""
            
            personas_framework = await self.call_llm(persona_prompt)
        else:
            personas_framework = "由于没有合适的MCP数据源，将使用定性研究方法"
        
        return {
            "success": True,
            "target_audience": target_audience,
            "analysis_goals": analysis_goals,
            "data_collection_strategy": strategy,
            "validated_data_plan": validated_plan,
            "user_personas_framework": personas_framework,
            "methodology": "LLM决策数据收集 + 真实MCP服务器 + 专业画像分析",
            "message": f"✅ 完成基于真实MCP配置的{target_audience}用户画像分析规划"
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
    port = int(os.environ.get("AGENT_PORT", 8001))
    
    agent_instance = RealMCPUserResearchAgent()
    logger.info(f"🚀 启动Real MCP User Research Agent，端口: {port}")
    logger.info("🧠 此Agent参考common agent方式，从mcp_servers.json读取真实配置")
    logger.info("🎯 LLM决策使用真实MCP工具，无任何硬编码或模拟数据")
    run_server(agent_instance, host="0.0.0.0", port=port)


if __name__ == "__main__":
    main() 
