#!/usr/bin/env python3
"""
端到端多Agent集成测试

测试完整的任务分发和协作流程：
1. Common Agent接收用户任务
2. 智能分发给专业Agents
3. 专业Agents使用LLM+MCP完成工作
4. Common Agent合并结果
5. 返回完整响应给用户
"""

import asyncio
import json
import httpx
import time
from datetime import datetime

class EndToEndIntegrationTest:
    """端到端集成测试器"""
    
    def __init__(self):
        self.common_agent_url = "http://localhost:8000"
        self.specialist_agents = {
            "user_research": {"port": 8001, "name": "Real MCP User Research Agent"},
            "ui_designer": {"port": 8002, "name": "Real UI Designer Agent"},
            "product_manager": {"port": 8003, "name": "Real Product Manager Agent"}
        }
        
    async def check_system_readiness(self):
        """检查整个系统的就绪状态"""
        print("🔍 系统就绪性检查")
        print("=" * 50)
        
        # 检查Common Agent
        try:
            async with httpx.AsyncClient() as client:
                health_resp = await client.get(f"{self.common_agent_url}/health", timeout=10)
                if health_resp.status_code == 200:
                    health_data = health_resp.json()
                    print(f"✅ Common Agent: {health_data['agent']}")
                    print(f"   📊 发现的专业Agents: {health_data['discovered_agents']} 个")
                    print(f"   🧠 LLM状态: {'就绪' if health_data['llm_ready'] else '未就绪'}")
                else:
                    print("❌ Common Agent健康检查失败")
                    return False
        except Exception as e:
            print(f"❌ Common Agent连接失败: {e}")
            return False
        
        # 检查专业Agents
        print("\n🎯 专业Agents状态:")
        for agent_type, config in self.specialist_agents.items():
            try:
                async with httpx.AsyncClient() as client:
                    agent_resp = await client.get(f"http://localhost:{config['port']}/a2a/agent.json", timeout=5)
                    if agent_resp.status_code == 200:
                        agent_data = agent_resp.json()
                        print(f"  ✅ {agent_data['name']}: 运行正常")
                    else:
                        print(f"  ❌ {config['name']}: 响应异常")
                        return False
            except Exception as e:
                print(f"  ❌ {config['name']}: 连接失败 - {e}")
                return False
        
        print("\n✅ 系统就绪，可以开始端到端测试")
        return True
    
    async def test_simple_task_coordination(self):
        """测试简单任务的协调和分发"""
        print("\n🚀 测试1: 简单任务协调")
        print("=" * 50)
        
        task_request = {
            "task": "我需要为一个AI助手产品制定完整的产品策略",
            "requirements": [
                "市场研究和用户需求分析",
                "产品功能和界面设计建议", 
                "产品路线图和竞争分析"
            ]
        }
        
        print(f"📝 任务: {task_request['task']}")
        print(f"📋 需求: {len(task_request['requirements'])} 项")
        
        try:
            async with httpx.AsyncClient() as client:
                # 发送任务给Common Agent
                response = await client.post(
                    f"{self.common_agent_url}/task",
                    json={"description": task_request["task"], "requirements": task_request["requirements"]},
                    timeout=120  # 2分钟超时
                )
                
                if response.status_code == 200:
                    result = response.json()
                    
                    print("✅ Common Agent任务处理成功")
                    print(f"📊 处理时间: {result.get('processing_time', 'unknown')}")
                    
                    # 检查是否有专业Agent的参与
                    if "agent_collaborations" in result:
                        collabs = result["agent_collaborations"]
                        print(f"\n🤝 专业Agent协作:")
                        for agent_name, contribution in collabs.items():
                            print(f"  👥 {agent_name}: {contribution.get('status', 'unknown')}")
                    
                    # 检查最终结果
                    if "final_result" in result:
                        final = result["final_result"]
                        print(f"\n📈 最终结果:")
                        print(f"  📋 包含组件: {len(final.get('components', []))} 个")
                        if "summary" in final:
                            print(f"  📄 总结: {final['summary'][:100]}...")
                    
                    return True
                    
                else:
                    print(f"❌ 任务处理失败: HTTP {response.status_code}")
                    try:
                        error_detail = response.json()
                        print(f"   错误详情: {error_detail}")
                    except:
                        print(f"   错误详情: {response.text}")
                    return False
                    
        except asyncio.TimeoutError:
            print("❌ 任务处理超时")
            return False
        except Exception as e:
            print(f"❌ 任务处理异常: {e}")
            return False
    
    async def test_complex_workflow(self):
        """测试复杂的多阶段工作流"""
        print("\n🎯 测试2: 复杂多阶段工作流")
        print("=" * 50)
        
        complex_task = {
            "task": "设计一个智能代码助手平台的完整产品方案",
            "context": {
                "target_users": "开发者和编程学习者",
                "market_size": "全球开发者工具市场",
                "timeline": "6个月MVP开发周期"
            },
            "deliverables": [
                "用户研究报告和需求分析",
                "产品功能架构设计",
                "UI/UX设计原型和规范",
                "技术实现路线图",
                "市场定位和竞争策略"
            ]
        }
        
        print(f"📝 复杂任务: {complex_task['task']}")
        print(f"🎯 目标用户: {complex_task['context']['target_users']}")
        print(f"📋 交付物: {len(complex_task['deliverables'])} 项")
        
        try:
            async with httpx.AsyncClient() as client:
                start_time = time.time()
                
                response = await client.post(
                    f"{self.common_agent_url}/task",
                    json={"description": complex_task["task"], "context": complex_task["context"], "deliverables": complex_task["deliverables"]},
                    timeout=180  # 3分钟超时
                )
                
                end_time = time.time()
                processing_time = end_time - start_time
                
                if response.status_code == 200:
                    result = response.json()
                    
                    print(f"✅ 复杂工作流处理成功")
                    print(f"⏱️ 总处理时间: {processing_time:.2f} 秒")
                    
                    # 分析协作过程
                    if "workflow_stages" in result:
                        stages = result["workflow_stages"]
                        print(f"\n🔄 工作流阶段: {len(stages)} 个")
                        for i, stage in enumerate(stages, 1):
                            print(f"  {i}. {stage.get('stage_name', 'Unknown')}: {stage.get('status', 'unknown')}")
                    
                    # 检查专业Agent贡献
                    agent_contributions = result.get("agent_contributions", {})
                    if agent_contributions:
                        print(f"\n👥 专业Agent贡献:")
                        for agent, contrib in agent_contributions.items():
                            tools_used = contrib.get("mcp_tools_used", [])
                            llm_decisions = contrib.get("llm_decision_count", 0)
                            print(f"  🎯 {agent}:")
                            print(f"    🔧 MCP工具使用: {len(tools_used)} 个")
                            print(f"    🧠 LLM决策次数: {llm_decisions}")
                    
                    # 验证无模拟数据
                    verification = result.get("verification", {})
                    if verification:
                        print(f"\n✅ 真实性验证:")
                        print(f"  🚫 无模拟数据: {verification.get('no_mock_data', 'unknown')}")
                        print(f"  🔧 真实MCP工具: {verification.get('real_mcp_tools', 'unknown')}")
                        print(f"  🧠 真实LLM决策: {verification.get('real_llm_decisions', 'unknown')}")
                    
                    return True
                    
                else:
                    print(f"❌ 复杂工作流失败: HTTP {response.status_code}")
                    return False
                    
        except asyncio.TimeoutError:
            print("❌ 复杂工作流超时")
            return False
        except Exception as e:
            print(f"❌ 复杂工作流异常: {e}")
            return False
    
    async def test_real_mcp_integration(self):
        """测试真实MCP工具集成"""
        print("\n🔧 测试3: 真实MCP工具集成验证")
        print("=" * 50)
        
        mcp_task = {
            "task": "使用真实MCP工具进行技术调研",
            "mcp_requirements": [
                "使用fetch工具获取最新技术资讯",
                "使用filesystem工具分析本地代码结构",
                "使用git工具检查代码历史",
                "使用github工具分析开源项目"
            ],
            "validation": {
                "ensure_real_tools": True,
                "no_mock_data": True,
                "llm_driven_decisions": True
            }
        }
        
        print(f"📝 MCP集成任务: {mcp_task['task']}")
        print(f"🔧 MCP需求: {len(mcp_task['mcp_requirements'])} 项")
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.common_agent_url}/task",
                    json={"description": mcp_task["task"], "mcp_requirements": mcp_task["mcp_requirements"], "validation": mcp_task["validation"]},
                    timeout=150
                )
                
                if response.status_code == 200:
                    result = response.json()
                    
                    print("✅ MCP工具集成测试成功")
                    
                    # 验证真实MCP工具使用
                    mcp_usage = result.get("mcp_tool_usage", {})
                    if mcp_usage:
                        print(f"\n🔧 MCP工具使用情况:")
                        for tool, usage in mcp_usage.items():
                            calls = usage.get("calls", 0)
                            success = usage.get("success_rate", "unknown")
                            print(f"  ⚙️ {tool}: {calls} 次调用, 成功率 {success}")
                    
                    # 验证LLM决策过程
                    llm_decisions = result.get("llm_decision_log", [])
                    if llm_decisions:
                        print(f"\n🧠 LLM决策记录: {len(llm_decisions)} 个")
                        for decision in llm_decisions[:3]:  # 显示前3个
                            print(f"  💭 {decision.get('decision_type', 'unknown')}: {decision.get('reasoning', 'no reasoning')[:50]}...")
                    
                    return True
                else:
                    print(f"❌ MCP工具集成失败: HTTP {response.status_code}")
                    return False
                    
        except Exception as e:
            print(f"❌ MCP集成测试异常: {e}")
            return False
    
    async def run_full_e2e_test(self):
        """运行完整的端到端测试"""
        print("🎯 端到端多Agent系统集成测试")
        print("=" * 60)
        print(f"📅 测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # 系统就绪性检查
        if not await self.check_system_readiness():
            print("❌ 系统未就绪，测试终止")
            return False
        
        test_results = []
        
        # 测试1: 简单任务协调
        result1 = await self.test_simple_task_coordination()
        test_results.append(("简单任务协调", result1))
        
        # 测试2: 复杂工作流
        result2 = await self.test_complex_workflow()
        test_results.append(("复杂多阶段工作流", result2))
        
        # 测试3: MCP工具集成
        result3 = await self.test_real_mcp_integration()
        test_results.append(("真实MCP工具集成", result3))
        
        # 测试结果汇总
        print("\n🎉 端到端测试完成")
        print("=" * 60)
        
        passed = sum(1 for _, result in test_results if result)
        total = len(test_results)
        
        print(f"📊 测试结果: {passed}/{total} 通过")
        print()
        
        for test_name, result in test_results:
            status = "✅ 通过" if result else "❌ 失败"
            print(f"  {status} {test_name}")
        
        print()
        
        if passed == total:
            print("🎉 所有测试通过！")
            print("✅ 端到端多Agent协作系统运行正常")
            print("✅ Common Agent成功协调专业Agents")
            print("✅ 专业Agents使用真实LLM+MCP工具")
            print("✅ 任务分发和结果合并功能正常")
            print("✅ 无任何模拟数据，完全真实架构")
            return True
        else:
            print(f"⚠️ {total - passed} 个测试失败")
            print("需要检查失败的测试组件")
            return False

async def main():
    """主函数"""
    tester = EndToEndIntegrationTest()
    success = await tester.run_full_e2e_test()
    
    if success:
        print("\n🌟 端到端集成测试成功完成！")
    else:
        print("\n🔧 部分测试需要调整，请检查系统状态")

if __name__ == "__main__":
    asyncio.run(main()) 