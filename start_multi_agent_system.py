#!/usr/bin/env python3
"""
启动真实多Agent系统
保持所有agents运行，供手动测试使用
"""

import asyncio
import subprocess
import time
import signal
import sys
import httpx
from typing import List, Dict

class MultiAgentSystemManager:
    """多Agent系统管理器"""
    
    def __init__(self):
        self.base_url = "http://localhost"
        self.processes: List[subprocess.Popen] = []
        self.agents = [
            {
                "name": "UI Designer Agent",
                "script": "specialist-agents/ui-designer-agent/a2a_agent.py",
                "port": 8003,
                "type": "specialist",
                "description": "A2A协议的UI设计师"
            },
            {
                "name": "User Research Agent", 
                "script": "specialist-agents/user-research-agent/a2a_agent.py",
                "port": 8001,
                "type": "specialist",
                "description": "A2A协议的用户研究专家"
            },
            {
                "name": "Product Manager Agent",
                "script": "specialist-agents/product-manager-agent/a2a_agent.py", 
                "port": 8002,
                "type": "specialist",
                "description": "A2A协议的产品经理"
            },
            {
                "name": "LLM-Driven Common Agent",
                "script": "common-agent/src/common_agent_llm_driven.py",
                "port": 8000,
                "type": "orchestrator",
                "description": "LLM驱动的协调者"
            }
        ]
        
    def cleanup_ports(self):
        """清理端口占用"""
        print("🧹 清理端口占用...")
        subprocess.run("lsof -ti:8000,8001,8002,8003 | xargs kill -9 2>/dev/null || true", shell=True)
        subprocess.run("pkill -f 'python3.*agent' 2>/dev/null || true", shell=True)
        time.sleep(2)
        
    async def start_agent(self, agent_config: Dict) -> bool:
        """启动单个agent"""
        print(f"🚀 启动 {agent_config['name']} (端口 {agent_config['port']})...")
        
        try:
            # 启动进程
            process = subprocess.Popen(
                ["python3", agent_config["script"]],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env={"AGENT_PORT": str(agent_config["port"])}
            )
            
            self.processes.append(process)
            print(f"   ✅ {agent_config['name']} 启动成功 (PID: {process.pid})")
            return True
            
        except Exception as e:
            print(f"   ❌ {agent_config['name']} 启动失败: {e}")
            return False
    
    async def wait_for_agent_ready(self, agent_config: Dict, max_wait: int = 30) -> bool:
        """等待agent准备就绪"""
        print(f"⏳ 等待 {agent_config['name']} 准备就绪...")
        
        if agent_config['port'] == 8000:  # Common agent
            url = f"{self.base_url}:{agent_config['port']}/status"
        else:  # All specialist agents are A2A
            url = f"{self.base_url}:{agent_config['port']}/a2a"
            
        for attempt in range(max_wait):
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(url, timeout=2.0)
                    if response.status_code == 200:
                        print(f"   ✅ {agent_config['name']} 已准备就绪")
                        return True
            except:
                pass
                
            if attempt % 5 == 4:  # 每5秒报告一次
                print(f"   ⏳ 仍在等待 {agent_config['name']}... ({attempt+1}/{max_wait}s)")
            await asyncio.sleep(1)
            
        print(f"   ❌ {agent_config['name']} 在 {max_wait}s 内未准备就绪")
        return False
    
    async def start_all_agents(self) -> bool:
        """启动所有agents"""
        print("🎯 启动真实多Agent系统")
        print("=" * 60)
        
        # 清理环境
        self.cleanup_ports()
        
        # 分离Common Agent和专业Agent
        common_agent = None
        specialist_agents = []
        
        for agent_config in self.agents:
            if agent_config['type'] == 'orchestrator':
                common_agent = agent_config
            else:
                specialist_agents.append(agent_config)
        
        # 确保找到Common Agent
        if common_agent is None:
            print("❌ 未找到Common Agent配置")
            return False
        
        # 首先启动Common Agent
        print("🚀 优先启动Common Agent...")
        if not await self.start_agent(common_agent):
            print("❌ Common Agent启动失败")
            return False
        
        # 等待Common Agent准备就绪
        print("⏳ 等待Common Agent准备就绪...")
        if not await self.wait_for_agent_ready(common_agent, max_wait=30):
            print("❌ Common Agent在30秒内未准备就绪")
            return False
        
        print("✅ Common Agent已准备就绪，可以开始接收任务")
        
        # 然后启动专业Agent（不阻塞Common Agent）
        print("\n🚀 启动专业Agent...")
        specialist_success_count = 0
        for agent_config in specialist_agents:
            if await self.start_agent(agent_config):
                specialist_success_count += 1
            await asyncio.sleep(1)  # 间隔启动
        
        print(f"📊 专业Agent启动结果: {specialist_success_count}/{len(specialist_agents)} 个启动成功")
        
        # 不等待专业Agent就绪，让Common Agent可以立即工作
        print("💡 Common Agent已可独立工作，专业Agent将在后台继续启动...")
        
        return True
    
    async def show_system_status(self):
        """显示系统状态"""
        print(f"\n✅ 多Agent系统启动成功！Common Agent已就绪\n")
        
        # 检查Common Agent状态
        print("🔍 检查Common Agent状态...")
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.base_url}:8000/status", timeout=5.0)
                if response.status_code == 200:
                    status_data = response.json()
                    discovered_agents = status_data.get("discovered_agents", {})
                    
                    print("📊 系统状态信息:")
                    print("=" * 60)
                    print(f"🎯 LLM客户端状态: {status_data.get('llm_client', 'unknown')}")
                    print(f"🔧 MCP服务器: {status_data.get('mcp_servers', 0)} 个")
                    print(f"👥 发现的Agents: {len(discovered_agents)} 个")
                    
                    if len(discovered_agents) > 0:
                        print("\n📋 已发现的Agent:")
                        for agent_id, agent_info in discovered_agents.items():
                            status = agent_info.get("status", "unknown")
                            protocol = agent_info.get("protocol", "unknown")
                            capabilities = agent_info.get("capabilities", [])
                            
                            status_icon = "✅" if status == "online" else "❌"
                            print(f"   {status_icon} {agent_id}")
                            print(f"      📡 协议: {protocol}")
                            print(f"      🔧 能力: {len(capabilities)} 个")
                    else:
                        print("\n💡 专业Agent正在后台启动中，Common Agent可以独立工作")
                        print("   🔄 Agent发现将在后台持续进行...")
                else:
                    print("❌ 无法获取Common Agent状态")
        except Exception as e:
            print(f"⚠️  无法连接Common Agent: {e}")
        
        # 后台持续监控Agent发现
        print("\n🔄 启动后台Agent发现监控...")
        asyncio.create_task(self.monitor_agent_discovery())
    
    async def monitor_agent_discovery(self):
        """后台监控Agent发现过程"""
        last_agent_count = 0
        check_interval = 10  # 每10秒检查一次
        
        while True:
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(f"{self.base_url}:8000/status", timeout=5.0)
                    if response.status_code == 200:
                        status_data = response.json()
                        discovered_agents = status_data.get("discovered_agents", {})
                        current_agent_count = len(discovered_agents)
                        
                        if current_agent_count > last_agent_count:
                            print(f"🎉 发现新Agent! 当前总数: {current_agent_count}")
                            last_agent_count = current_agent_count
                        
                        # 如果发现所有预期的Agent，可以停止监控
                        if current_agent_count >= 3:
                            print("✅ 所有专业Agent已发现完成")
                            break
                            
            except Exception:
                pass  # 静默处理连接错误
                
            await asyncio.sleep(check_interval)
    
    def show_usage_info(self):
        """显示使用说明"""
        print("\n📋 测试接口信息:")
        print("=" * 60)
        print("🎯 Common Agent (主要接口):")
        print("   📡 地址: http://localhost:8000")
        print("   📊 状态: GET http://localhost:8000/status")
        print("   📝 提交任务: POST http://localhost:8000/task")
        print("      请求体: {\"description\": \"你的任务描述\"}")
        print("")
        print("👥 Specialist Agents:")
        print("   🎨 UI Designer: http://localhost:8003 (A2A协议)")
        print("   👤 User Research: http://localhost:8001 (A2A协议)")
        print("   📈 Product Manager: http://localhost:8002 (A2A协议)")
        print("")
        print("🧪 SSE流式测试示例:")
        print("   # 使用curl测试SSE流式响应")
        print("   curl -X POST http://localhost:8000/task \\")
        print("        -H \"Content-Type: application/json\" \\")
        print("        -H \"Accept: text/event-stream\" \\")
        print("        -d '{\"description\": \"为移动应用设计一个登录界面\"}' \\")
        print("        --no-buffer")
        print("")
        print("   # 使用JavaScript EventSource")
        print("   const eventSource = new EventSource('http://localhost:8000/task');")
        print("   eventSource.onmessage = (event) => console.log(JSON.parse(event.data));")
        print("")
        print("💡 SSE流式功能:")
        print("   1. 实时LLM分析进度 📊")
        print("   2. 逐步执行计划反馈 🔄") 
        print("   3. Agent调用实时状态 👥")
        print("   4. 完整任务执行流程 ✅")
        print("   5. 支持A2A协议流式传输 🌊")
        
    def setup_signal_handlers(self):
        """设置信号处理器"""
        def signal_handler(signum, frame):
            print(f"\n🛑 接收到信号 {signum}，正在关闭系统...")
            self.shutdown()
            sys.exit(0)
            
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    def shutdown(self):
        """关闭所有agents"""
        print("\n🛑 关闭多Agent系统...")
        for process in self.processes:
            try:
                process.terminate()
                process.wait(timeout=5)
                print(f"   ✅ 进程 {process.pid} 已关闭")
            except:
                try:
                    process.kill()
                    print(f"   ⚡ 强制关闭进程 {process.pid}")
                except:
                    pass
        print("✅ 多Agent系统已关闭")
    
    async def run(self):
        """运行系统"""
        self.setup_signal_handlers()
        
        # 启动所有agents
        if not await self.start_all_agents():
            print("❌ 系统启动失败")
            self.shutdown()
            return
        
        # 显示状态和使用说明
        await self.show_system_status()
        self.show_usage_info()
        
        print("\n🎯 系统已启动并保持运行，按 Ctrl+C 停止")
        print("=" * 60)
        
        # 保持运行
        try:
            while True:
                await asyncio.sleep(10)
                # 可以在这里添加健康检查逻辑
        except KeyboardInterrupt:
            pass
        finally:
            self.shutdown()


async def main():
    """主函数"""
    manager = MultiAgentSystemManager()
    await manager.run()


if __name__ == "__main__":
    asyncio.run(main()) 