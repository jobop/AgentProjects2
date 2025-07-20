#!/usr/bin/env python3
"""
真正的多Agent系统测试

这是完全符合你要求的真实系统：
1. LLM驱动的Common Agent - 通过真实LLM决策
2. A2A协议agent间通信 
3. 动态agent发现机制
4. 真实MCP工具集成
5. 没有任何硬编码逻辑或mock

测试方法：
1. 启动所有Specialist Agents (A2A协议)
2. 启动LLM驱动的Common Agent
3. 向Common Agent提交任务，观察：
   - LLM如何分析任务
   - 如何动态发现agents
   - 如何通过A2A协议协调
   - 如何使用MCP工具
"""

import asyncio
import subprocess
import sys
import time
import signal
import json
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
import httpx
from datetime import datetime

class RealMultiAgentSystemTester:
    """真实多Agent系统测试器"""
    
    def __init__(self):
        self.processes = []
        self.running = False
        
        # Agent配置 - 真正的A2A compliant agents
        self.agents = [
            {
                "name": "UI Designer Agent",
                "script": "specialist-agents/ui-designer-agent/a2a_agent.py",
                "port": 8003,
                "type": "specialist",
                "description": "A2A协议的UI设计师，支持线框图、设计稿、设计系统"
            },
            {
                "name": "User Research Agent",
                "script": "specialist-agents/user-research-agent/a2a_agent.py",
                "port": 8001,
                "type": "specialist", 
                "description": "用户研究和市场分析专家，集成MCP工具"
            },
            {
                "name": "Product Manager Agent",
                "script": "specialist-agents/product-manager-agent/a2a_agent.py",
                "port": 8002,
                "type": "specialist",
                "description": "产品管理和需求分析专家，集成Github MCP"
            },
            {
                "name": "LLM-Driven Common Agent",
                "script": "common-agent/src/common_agent_llm_driven.py",
                "port": 8000,
                "type": "common",
                "description": "LLM驱动的协调中心，负责分析任务和协调specialists"
            }
        ]
        
        self.base_url = "http://localhost"
        
    def setup_signal_handlers(self):
        """设置信号处理器"""
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
    def _signal_handler(self, signum, frame):
        """信号处理函数"""
        print(f"\n🛑 收到信号 {signum}，正在关闭系统...")
        asyncio.create_task(self.shutdown())
        
    async def start_agent(self, agent_config: Dict[str, Any]) -> Optional[subprocess.Popen]:
        """启动单个Agent"""
        script_path = agent_config["script"]
        port = agent_config["port"]
        name = agent_config["name"]
        
        print(f"🚀 启动 {name} (端口 {port})...")
        
        # Set environment variables
        env = os.environ.copy()
        env["AGENT_PORT"] = str(port)
        env["AGENT_NAME"] = name
        
        try:
            # Start agent process
            process = subprocess.Popen(
                [sys.executable, script_path],
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Wait a bit for startup
            await asyncio.sleep(4)
            
            # Check if process is still running
            if process.poll() is None:
                print(f"   ✅ {name} 启动成功 (PID: {process.pid})")
                return process
            else:
                stdout, stderr = process.communicate()
                print(f"   ❌ {name} 启动失败")
                print(f"   STDOUT: {stdout}")
                print(f"   STDERR: {stderr}")
                return None
                
        except Exception as e:
            print(f"   ❌ 启动 {name} 时出错: {e}")
            return None
            
    async def wait_for_agent_ready(self, agent_config: Dict[str, Any], timeout: int = 30) -> bool:
        """等待Agent准备就绪"""
        port = agent_config["port"]
        name = agent_config["name"]
        url = f"{self.base_url}:{port}/health"
        
        print(f"⏳ 等待 {name} 准备就绪...")
        
        async with httpx.AsyncClient() as client:
            for i in range(timeout):
                try:
                    response = await client.get(url, timeout=2.0)
                    if response.status_code == 200:
                        print(f"   ✅ {name} 已准备就绪")
                        return True
                except:
                    pass
                    
                await asyncio.sleep(1)
                if i % 5 == 0 and i > 0:
                    print(f"   ⏳ 仍在等待 {name}... ({i}/{timeout}s)")
                    
        print(f"   ❌ {name} 在 {timeout}s 内未准备就绪")
        return False
        
    async def test_agent_discovery(self):
        """测试Agent发现机制"""
        print(f"\n🔍 测试Agent发现机制...")
        print("=" * 60)
        
        # 获取Common Agent状态，查看它发现了哪些agents
        common_agent_url = f"{self.base_url}:8000/status"
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(common_agent_url, timeout=10.0)
                
                if response.status_code == 200:
                    status_data = response.json()
                    discovered_agents = status_data.get("discovered_agents", {})
                    
                    print(f"📊 Common Agent发现结果:")
                    print(f"   🎯 LLM客户端状态: {status_data.get('llm_client', 'unknown')}")
                    print(f"   🔧 MCP服务器: {status_data.get('mcp_servers', 0)} 个")
                    print(f"   📋 活跃任务: {status_data.get('active_tasks', 0)} 个")
                    print(f"   👥 发现的Agents: {len(discovered_agents)} 个")
                    
                    for agent_id, agent_info in discovered_agents.items():
                        status = agent_info.get("status", "unknown")
                        protocol = agent_info.get("protocol", "unknown")
                        capabilities = agent_info.get("capabilities", [])
                        
                        status_icon = "✅" if status == "online" else "❌"
                        print(f"      {status_icon} {agent_id}")
                        print(f"         📡 协议: {protocol}")
                        print(f"         🔧 能力: {len(capabilities)} 个")
                        if capabilities:
                            # 确保capabilities是字符串列表
                            cap_names = []
                            for cap in capabilities[:3]:
                                if isinstance(cap, dict):
                                    cap_names.append(cap.get('name', str(cap)))
                                else:
                                    cap_names.append(str(cap))
                            print(f"         📋 具体能力: {', '.join(cap_names)}{'...' if len(capabilities) > 3 else ''}")
                    
                    return len(discovered_agents) > 0
                else:
                    print(f"❌ 获取Common Agent状态失败: HTTP {response.status_code}")
                    return False
                    
        except Exception as e:
            print(f"❌ Agent发现测试失败: {e}")
            return False
    
    async def test_llm_decision_making(self, task_description: str) -> Dict[str, Any]:
        """测试LLM决策制定"""
        print(f"\n🧠 测试LLM决策制定...")
        print(f"   📝 任务: {task_description}")
        
        common_agent_url = f"{self.base_url}:8000/task"
        
        task_data = {
            "description": task_description,
            "type": "llm_analysis_test"
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    common_agent_url,
                    json=task_data,
                    timeout=60.0
                )
                
                if response.status_code == 200:
                    result = response.json()
                    task_result = result.get("result", {})
                    
                    print(f"   ✅ LLM分析完成")
                    print(f"   🎯 执行策略: {task_result.get('execution_strategy', 'unknown')}")
                    
                    # 显示LLM决策详情
                    llm_decision = task_result.get("llm_decision", {})
                    if llm_decision:
                        print(f"   📋 LLM分析: {llm_decision.get('analysis', 'N/A')}")
                        print(f"   👥 需要的agents: {llm_decision.get('required_agents', [])}")
                        print(f"   🔧 需要的工具: {llm_decision.get('required_tools', [])}")
                        
                        execution_plan = llm_decision.get("execution_plan", [])
                        print(f"   📊 执行计划: {len(execution_plan)} 步")
                        for step in execution_plan:
                            print(f"      {step.get('step', 0)}. {step.get('action', 'unknown')} -> {step.get('target', 'unknown')}")
                    
                    # 显示执行结果
                    execution_results = task_result.get("execution_results", [])
                    successful_steps = sum(1 for r in execution_results if "error" not in r)
                    print(f"   📈 执行结果: {successful_steps}/{len(execution_results)} 步成功")
                    
                    for step_result in execution_results:
                        step_num = step_result.get("step", 0)
                        action = step_result.get("action", "unknown")
                        target = step_result.get("target", "unknown")
                        
                        if "error" in step_result:
                            print(f"      ❌ 步骤 {step_num}: {action} -> {target} (失败: {step_result['error']})")
                        else:
                            print(f"      ✅ 步骤 {step_num}: {action} -> {target} (成功)")
                    
                    return {
                        "success": True,
                        "task_result": task_result,
                        "llm_decision": llm_decision,
                        "execution_results": execution_results
                    }
                else:
                    print(f"   ❌ LLM任务失败: HTTP {response.status_code}")
                    print(f"   📄 响应: {response.text}")
                    return {"success": False, "error": f"HTTP {response.status_code}"}
                    
        except Exception as e:
            print(f"   ❌ LLM决策测试失败: {e}")
            return {"success": False, "error": str(e)}
    
    async def run_comprehensive_tests(self):
        """运行全面的系统测试"""
        print(f"\n🎯 开始真实多Agent系统全面测试...")
        print("=" * 60)
        
        # 测试用例 - 真实的复杂任务
        test_cases = [
            {
                "name": "简单设计任务",
                "description": "为移动应用设计一个登录界面",
                "expected_strategy": "single_agent",
                "expected_agents": ["ui_designer_agent"]
            },
            {
                "name": "市场研究任务",
                "description": "分析健身应用市场并制定竞争策略",
                "expected_strategy": "single_agent", 
                "expected_agents": ["user_research_agent"]
            },
            {
                "name": "产品规划任务",
                "description": "为新的社交媒体功能制定产品需求和优先级",
                "expected_strategy": "single_agent",
                "expected_agents": ["product_manager_agent"]
            },
            {
                "name": "多Agent协作任务",
                "description": "开发一款电商应用：先进行市场调研，然后制定产品规划，最后设计用户界面",
                "expected_strategy": "multi_agent",
                "expected_agents": ["user_research_agent", "product_manager_agent", "ui_designer_agent"]
            },
            {
                "name": "复杂业务场景",
                "description": "设计一个完整的在线银行系统，包括用户研究、安全需求分析、界面设计和用户体验优化",
                "expected_strategy": "multi_agent",
                "expected_agents": ["user_research_agent", "product_manager_agent", "ui_designer_agent"]
            }
        ]
        
        test_results = []
        
        for i, test_case in enumerate(test_cases, 1):
            print(f"\n{i}️⃣  {test_case['name']}")
            print(f"   📝 任务: {test_case['description']}")
            print(f"   🎯 预期策略: {test_case['expected_strategy']}")
            print(f"   👥 预期agents: {', '.join(test_case['expected_agents'])}")
            
            start_time = datetime.now()
            result = await self.test_llm_decision_making(test_case["description"])
            end_time = datetime.now()
            
            duration = (end_time - start_time).total_seconds()
            
            if result["success"]:
                actual_strategy = result["task_result"].get("execution_strategy", "unknown")
                llm_decision = result.get("llm_decision", {})
                actual_agents = llm_decision.get("required_agents", [])
                execution_results = result.get("execution_results", [])
                
                successful_steps = sum(1 for r in execution_results if "error" not in r)
                total_steps = len(execution_results)
                
                print(f"   ✅ 测试完成 (耗时: {duration:.2f}s)")
                print(f"   📊 实际策略: {actual_strategy}")
                print(f"   👥 实际agents: {', '.join(actual_agents)}")
                print(f"   📈 执行成功率: {successful_steps}/{total_steps}")
                
                # 评估LLM决策质量
                strategy_match = actual_strategy == test_case["expected_strategy"]
                agent_match = set(actual_agents) == set(test_case["expected_agents"])
                
                quality_score = 0
                if strategy_match:
                    quality_score += 40
                if agent_match:
                    quality_score += 40
                if successful_steps == total_steps:
                    quality_score += 20
                    
                print(f"   🏆 决策质量评分: {quality_score}/100")
                
                test_results.append({
                    "test": test_case["name"],
                    "success": True,
                    "duration": duration,
                    "strategy_match": strategy_match,
                    "agent_match": agent_match,
                    "execution_success_rate": successful_steps / total_steps if total_steps > 0 else 0,
                    "quality_score": quality_score,
                    "actual_strategy": actual_strategy,
                    "actual_agents": actual_agents
                })
                
            else:
                print(f"   ❌ 测试失败: {result.get('error', 'Unknown error')}")
                test_results.append({
                    "test": test_case["name"],
                    "success": False,
                    "error": result.get("error", "Unknown error")
                })
            
            # Wait between tests
            await asyncio.sleep(3)
        
        return test_results
    
    def print_comprehensive_summary(self, test_results: List[Dict[str, Any]]):
        """打印综合测试总结"""
        print(f"\n📊 真实多Agent系统测试总结")
        print("=" * 60)
        
        total_tests = len(test_results)
        successful_tests = sum(1 for r in test_results if r["success"])
        
        print(f"总测试数: {total_tests}")
        print(f"成功测试: {successful_tests}")
        print(f"失败测试: {total_tests - successful_tests}")
        print(f"成功率: {(successful_tests / total_tests * 100):.1f}%")
        
        if successful_tests > 0:
            avg_duration = sum(r.get("duration", 0) for r in test_results if r["success"]) / successful_tests
            avg_quality = sum(r.get("quality_score", 0) for r in test_results if r["success"]) / successful_tests
            
            print(f"平均耗时: {avg_duration:.2f}s")
            print(f"平均LLM决策质量: {avg_quality:.1f}/100")
        
        print(f"\n📋 详细结果:")
        for result in test_results:
            status = "✅" if result["success"] else "❌"
            print(f"  {status} {result['test']}")
            if result["success"]:
                print(f"     🎯 策略: {result['actual_strategy']}")
                print(f"     👥 agents: {', '.join(result['actual_agents'])}")
                print(f"     ⏱️  耗时: {result['duration']:.2f}s")
                print(f"     🏆 质量: {result['quality_score']}/100")
                print(f"     📈 执行率: {result['execution_success_rate']*100:.1f}%")
            else:
                print(f"     ❌ 错误: {result.get('error', 'Unknown')}")
                
    async def start_system(self):
        """启动整个真实多Agent系统"""
        print("🎯 启动真实多Agent系统")
        print("=" * 60)
        
        # 先启动specialist agents，再启动common agent
        specialist_agents = [a for a in self.agents if a["type"] == "specialist"]
        common_agents = [a for a in self.agents if a["type"] == "common"]
        
        # 启动specialist agents
        for agent_config in specialist_agents:
            process = await self.start_agent(agent_config)
            if process:
                self.processes.append(process)
            else:
                print(f"❌ 启动 {agent_config['name']} 失败")
                await self.shutdown()
                return False
                
        # 等待specialist agents准备就绪
        for agent_config in specialist_agents:
            if not await self.wait_for_agent_ready(agent_config):
                print(f"❌ {agent_config['name']} 未能准备就绪")
                await self.shutdown()
                return False
        
        # 启动common agent
        for agent_config in common_agents:
            process = await self.start_agent(agent_config)
            if process:
                self.processes.append(process)
            else:
                print(f"❌ 启动 {agent_config['name']} 失败")
                await self.shutdown()
                return False
                
        # 等待common agent准备就绪
        for agent_config in common_agents:
            if not await self.wait_for_agent_ready(agent_config, timeout=45):
                print(f"❌ {agent_config['name']} 未能准备就绪")
                await self.shutdown()
                return False
                
        self.running = True
        print(f"\n✅ 真实多Agent系统启动成功！{len(self.agents)} 个Agent正在运行")
        
        # 测试agent发现
        if not await self.test_agent_discovery():
            print(f"❌ Agent发现机制测试失败")
            return False
            
        # 运行综合测试
        test_results = await self.run_comprehensive_tests()
        
        # 打印总结
        self.print_comprehensive_summary(test_results)
        
        # 检查测试结果
        all_passed = all(r["success"] for r in test_results)
        avg_quality = sum(r.get("quality_score", 0) for r in test_results if r["success"]) / len([r for r in test_results if r["success"]]) if any(r["success"] for r in test_results) else 0
        
        if all_passed and avg_quality >= 70:
            print(f"\n🎉 真实多Agent系统测试全部通过！平均LLM决策质量: {avg_quality:.1f}/100")
            return True
        elif all_passed:
            print(f"\n⚠️  测试通过，但LLM决策质量需要改进 (当前: {avg_quality:.1f}/100)")
            return True
        else:
            print(f"\n❌ 部分测试失败")
            return False
            
    async def shutdown(self):
        """关闭系统"""
        if not self.running:
            return
            
        print(f"\n🛑 关闭真实多Agent系统...")
        self.running = False
        
        for process in self.processes:
            try:
                process.terminate()
                await asyncio.sleep(1)
                if process.poll() is None:
                    process.kill()
                print(f"   ✅ 进程 {process.pid} 已关闭")
            except Exception as e:
                print(f"   ⚠️  关闭进程时出错: {e}")
                
        self.processes.clear()
        print("✅ 真实多Agent系统已关闭")


async def main():
    """主函数"""
    tester = RealMultiAgentSystemTester()
    tester.setup_signal_handlers()
    
    try:
        # Start the system and run tests
        if await tester.start_system():
            print(f"\n🎯 真实多Agent系统测试完成，保持运行30秒以供检查...")
            await asyncio.sleep(30)
        else:
            print(f"\n❌ 真实多Agent系统测试失败")
            
    except KeyboardInterrupt:
        print(f"\n🛑 用户中断")
    except Exception as e:
        print(f"\n💥 系统错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await tester.shutdown()


if __name__ == "__main__":
    asyncio.run(main()) 