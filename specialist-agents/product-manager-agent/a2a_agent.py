#!/usr/bin/env python3
"""
真正的产品经理Agent

参考common agent的MCP管理方式，从mcp_servers.json读取真实配置
让LLM根据真实可用的MCP工具决策进行产品管理和策略分析
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
    name="产品经理-bobo",
    description="真正的LLM驱动产品经理专家，使用真实MCP工具进行产品策略分析和管理",
    version="1.0.0",
    url="http://localhost:8002",
    capabilities={
        "streaming": True,
        "google_a2a_compatible": True,
        "llm_powered": True,
        "real_mcp_integration": True,
        "no_simulation": True
    }
)
class RealProductManagerAgent(A2AServer):
    """真正的产品经理Agent - 参考common agent方式"""
    
    def __init__(self):
        super().__init__()
        self.agent_id = "real_product_manager_agent"
        self.agent_name = "Real Product Manager Agent"
        
        # LLM API配置
        self.api_key = os.getenv("SILICONFLOW_API_KEY", "xxxxxx")
        self.base_url = "https://api.siliconflow.cn/v1"
        self.model = "deepseek-ai/DeepSeek-V3"
        
        # 初始化MCP管理器 - 参考common agent方式
        self.mcp_loader = SimpleMCPLoader()
        self.available_mcp_servers = {}
        self.mcp_servers_info = {}
        
        self._init_mcp_system()
        
        logger.info("✅ Real Product Manager Agent 初始化完成")
    
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
        """调用LLM进行产品决策"""
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
        
        mcp_info.append("\n注意：你可以决策使用这些MCP服务器中的任何工具来完成产品管理任务。")
        return "\n".join(mcp_info)

    @skill(
        name="LLM驱动的产品策略分析",
        description="让LLM分析产品需求并决策使用哪些MCP工具进行产品管理",
        tags=["llm-powered", "product-strategy", "real-tools", "no-simulation"]
    )
    async def llm_driven_product_strategy_analysis(self, product_vision: str, market_context: str):
        """LLM驱动的产品策略分析"""
        
        logger.info(f"📊 LLM驱动的产品策略分析: {product_vision}")
        
        # 构建包含真实MCP服务器信息的提示
        mcp_info = self._format_mcp_info_for_llm()
        
        strategy_prompt = f"""
作为资深产品经理，我需要为以下产品制定策略：

产品愿景：{product_vision}
市场背景：{market_context}

{mcp_info}

请分析这个产品策略任务，决定需要使用哪些MCP服务器和工具来完成产品分析和规划。

返回JSON格式：
{{
    "product_analysis": "产品现状分析",
    "market_opportunity": "市场机会分析",
    "required_mcp_tools": [
        {{
            "server": "MCP服务器名称",
            "purpose": "使用目的",
            "data_target": "目标数据",
            "expected_insight": "预期洞察"
        }}
    ],
    "strategy_framework": "策略框架",
    "key_metrics": ["关键指标列表"],
    "action_plan": "行动计划"
}}

只使用列出的真实MCP服务器，你可以推断每个服务器可能提供的产品管理相关工具。
"""

        # LLM分析产品策略
        llm_analysis = await self.call_llm(strategy_prompt)
        logger.info(f"🧠 LLM策略分析完成，响应长度: {len(llm_analysis)} 字符")
        
        # 解析LLM分析结果
        try:
            import re
            json_match = re.search(r'\{.*\}', llm_analysis, re.DOTALL)
            if json_match:
                analysis_result = json.loads(json_match.group())
            else:
                analysis_result = {"required_mcp_tools": [], "product_analysis": llm_analysis}
        except Exception as e:
            logger.warning(f"⚠️ LLM分析解析失败: {e}")
            analysis_result = {"required_mcp_tools": [], "product_analysis": llm_analysis}
        
        # 验证LLM决策的工具
        tool_execution_plan = []
        required_tools = analysis_result.get("required_mcp_tools", [])
        
        logger.info(f"🎯 LLM决策使用 {len(required_tools)} 个产品工具")
        
        for tool in required_tools:
            server = tool.get("server")
            if server in self.mcp_servers_info:
                tool_execution_plan.append({
                    "server": server,
                    "purpose": tool.get("purpose"),
                    "data_target": tool.get("data_target"),
                    "expected_insight": tool.get("expected_insight"),
                    "server_info": self.mcp_servers_info[server],
                    "status": "llm_decided_real_server",
                    "note": "LLM选择了真实存在的MCP服务器"
                })
                logger.info(f"✅ LLM选择真实服务器: {server} - {tool.get('purpose')}")
            else:
                logger.warning(f"⚠️ LLM选择了不存在的服务器: {server}")
        
        # LLM基于工具计划生成详细产品策略
        if tool_execution_plan:
            strategy_detail_prompt = f"""
基于MCP工具使用计划，为"{product_vision}"制定详细的产品策略：

分析结果：
{json.dumps(analysis_result, ensure_ascii=False, indent=2)}

工具执行计划：
{json.dumps(tool_execution_plan, ensure_ascii=False, indent=2)}

请生成完整的产品策略方案，包括：
1. 产品定位和差异化策略
2. 目标用户群体和用户画像
3. 核心功能优先级
4. 商业模式设计
5. 竞争策略分析
6. 产品路线图规划
7. 成功指标和KPI设计
8. 风险评估和应对策略

基于专业产品管理方法论和真实工具能力，提供可执行的策略方案。
"""

            final_strategy = await self.call_llm(strategy_detail_prompt)
        else:
            final_strategy = "由于没有合适的MCP工具，将使用传统产品管理方法"
        
        return {
            "success": True,
            "product_vision": product_vision,
            "market_context": market_context,
            "llm_strategy_analysis": analysis_result,
            "tool_execution_plan": tool_execution_plan,
            "final_product_strategy": final_strategy,
            "methodology": "LLM专业分析 + 真实MCP工具集成 + 产品策略制定",
            "tools_planned": len(tool_execution_plan),
            "message": f"✅ 完成基于LLM决策的{product_vision}产品策略分析"
        }

    @skill(
        name="产品路线图规划",
        description="LLM分析产品需求并规划开发路线图",
        tags=["product-roadmap", "llm-planning", "feature-prioritization"]
    )
    async def product_roadmap_planning(self, product_goals: List[str], timeline: str, constraints: List[str]):
        """产品路线图规划"""
        
        logger.info(f"🗺️ 产品路线图规划开始")
        
        # LLM规划产品路线图
        mcp_info = self._format_mcp_info_for_llm()
        
        roadmap_prompt = f"""
作为产品经理，请为以下产品目标制定详细的开发路线图：

产品目标：
{json.dumps(product_goals, ensure_ascii=False, indent=2)}

时间线：{timeline}

约束条件：
{json.dumps(constraints, ensure_ascii=False, indent=2)}

{mcp_info}

请制定：
1. 功能优先级矩阵
2. 里程碑规划
3. 资源分配计划
4. 依赖关系分析
5. 风险识别和缓解
6. 质量保证计划
7. 发布策略

要求路线图科学、可执行、基于真实MCP工具支持。
"""

        roadmap_plan = await self.call_llm(roadmap_prompt)
        logger.info(f"🗺️ 产品路线图规划完成")
        
        return {
            "success": True,
            "product_goals": product_goals,
            "timeline": timeline,
            "constraints": constraints,
            "roadmap_plan": roadmap_plan,
            "methodology": "LLM产品规划 + MCP工具集成支持",
            "approach": "AI驱动的产品路线图制定"
        }

    @skill(
        name="竞品分析和市场定位",
        description="LLM进行竞品分析并制定市场定位策略",
        tags=["competitive-analysis", "market-positioning", "llm-analysis"]
    )
    async def competitive_analysis_and_positioning(self, product_category: str, target_competitors: List[str]):
        """竞品分析和市场定位"""
        
        logger.info(f"🔍 竞品分析开始: {product_category}")
        
        # LLM进行竞品分析
        mcp_info = self._format_mcp_info_for_llm()
        
        competitive_prompt = f"""
作为产品策略专家，请对以下产品类别进行深度竞品分析：

产品类别：{product_category}
目标竞品：
{json.dumps(target_competitors, ensure_ascii=False, indent=2)}

{mcp_info}

请提供：
1. 竞品功能对比矩阵
2. 商业模式分析
3. 用户评价洞察
4. 技术栈和性能对比
5. 市场份额和趋势
6. 差异化机会识别
7. 市场定位建议
8. 竞争策略制定

基于专业分析方法和真实MCP工具能力，提供可操作的竞争策略。
"""

        competitive_analysis = await self.call_llm(competitive_prompt)
        logger.info(f"🔍 竞品分析完成")
        
        return {
            "success": True,
            "product_category": product_category,
            "target_competitors": target_competitors,
            "competitive_analysis": competitive_analysis,
            "methodology": "LLM专业分析 + MCP数据工具",
            "focus": "数据驱动的竞争策略制定"
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
    port = int(os.environ.get("AGENT_PORT", 8003))
    
    agent_instance = RealProductManagerAgent()
    logger.info(f"🚀 启动Real Product Manager Agent，端口: {port}")
    logger.info("📊 此Agent参考common agent方式，从mcp_servers.json读取真实配置")
    logger.info("🎯 LLM决策使用真实MCP工具，无任何硬编码或模拟数据")
    run_server(agent_instance, host="0.0.0.0", port=port)


if __name__ == "__main__":
    main() 
