# 真实多Agent系统测试指南

## 🎯 **系统设计原则**

完全按照你的要求设计的真正LLM驱动、A2A协议、无硬编码的多Agent系统：

### ✅ **核心特性**
- **LLM驱动决策** - Common Agent完全依赖真实LLM分析任务和制定计划
- **A2A协议通信** - 使用标准A2A JSON-RPC 2.0协议进行agent间通信
- **动态发现机制** - 运行时发现可用agents，无硬编码agent信息
- **真实MCP集成** - 使用Cursor风格的MCP配置，真实工具调用
- **零Mock代码** - 所有功能都是真实实现，无任何简化或模拟

### ❌ **绝对禁止**
- ❌ 硬编码的if-else决策逻辑
- ❌ 预定义的agent调用顺序
- ❌ Mock或简化的工具调用
- ❌ 写死的agent能力匹配

## 🏗️ **系统架构**

```
┌─────────────────────────────────────────────────────────────┐
│                    用户任务提交                              │
└─────────────────────────┬───────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────┐
│             LLM驱动的Common Agent (端口8000)                 │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ 1. 通过LLM分析任务需求                                   │ │
│  │ 2. 动态发现可用specialist agents                        │ │
│  │ 3. LLM制定执行计划                                      │ │
│  │ 4. 使用A2A协议协调agents                                │ │
│  │ 5. 调用MCP工具                                          │ │
│  │ 6. 整合结果返回                                         │ │
│  └─────────────────────────────────────────────────────────┘ │
└─────────────────────────┬───────────────────────────────────┘
                          │ A2A协议通信
        ┌─────────────────┼─────────────────┐
        │                 │                 │
┌───────▼────────┐ ┌──────▼─────────┐ ┌────▼──────────┐
│ User Research  │ │ Product Manager │ │ UI Designer   │
│ Agent (8001)   │ │ Agent (8002)    │ │ Agent (8003)  │
│                │ │                 │ │               │
│ MCP: fetch,    │ │ MCP: github,    │ │ MCP: figma,   │
│ filesystem     │ │ filesystem      │ │ filesystem    │
└────────────────┘ └─────────────────┘ └───────────────┘
```

## 📋 **测试方法说明**

### 1. **系统启动流程**

```bash
# 运行完整的真实系统测试
python3 real_multi_agent_system_test.py
```

**启动顺序：**
1. 启动所有Specialist Agents (A2A协议)
2. 等待Specialist Agents准备就绪
3. 启动LLM驱动的Common Agent
4. Common Agent执行agent发现过程
5. 验证系统连通性

### 2. **Agent发现测试**

Common Agent会自动发现可用的agents：

```python
# 发现方法优先级：
1. A2A标准: GET /.well-known/agent.json
2. 能力端点: GET /capabilities  
3. 健康检查: GET /health
```

**验证点：**
- ✅ 发现所有在线agents
- ✅ 正确识别A2A vs Legacy协议
- ✅ 获取agent能力列表
- ✅ 实时状态监控

### 3. **LLM决策测试**

每个任务都会触发真实的LLM分析：

```python
# LLM分析提示示例
"""
你是一个多Agent系统的协调者。用户提交了一个任务，你需要分析这个任务并决定如何处理。

可用的系统资源：
{
  "available_agents": {
    "ui_designer_agent": {
      "endpoint": "http://localhost:8003",
      "capabilities": ["wireframe_creation", "mockup_design"],
      "protocol": "a2a"
    },
    "user_research_agent": {
      "endpoint": "http://localhost:8001", 
      "capabilities": ["market_analysis", "user_surveys"],
      "protocol": "legacy"
    }
  },
  "available_mcp_tools": ["figma_create", "fetch_url", "read_file"]
}

用户任务：开发一款电商应用，包括市场调研、产品规划和界面设计

请分析这个任务并制定执行计划...
"""
```

**LLM决策评估：**
- 🎯 **策略选择** - single_agent/multi_agent/mcp_tools/hybrid
- 👥 **Agent选择** - 基于能力匹配的agent列表
- 📋 **执行计划** - 具体的步骤和依赖关系
- 🏆 **质量评分** - 与预期结果的匹配度

### 4. **A2A协议通信测试**

Common Agent使用A2A JSON-RPC 2.0与agents通信：

```json
{
  "jsonrpc": "2.0",
  "method": "tasks/send",
  "id": "common_agent_1234567890",
  "params": {
    "id": "task_1234567890",
    "sessionId": "session_1234567890",
    "message": {
      "role": "user",
      "parts": [
        {
          "type": "text",
          "text": "设计一个移动应用登录界面"
        },
        {
          "type": "data", 
          "data": {
            "previous_results": [],
            "delegated_by": "common_agent"
          }
        }
      ]
    },
    "acceptedOutputModes": ["text", "application/json"]
  }
}
```

**验证点：**
- ✅ 正确的JSON-RPC 2.0格式
- ✅ 多模态数据传输 (text + data)
- ✅ 会话和任务ID管理
- ✅ 错误处理和重试机制

### 5. **测试用例设计**

```python
test_cases = [
    {
        "name": "简单设计任务",
        "description": "为移动应用设计一个登录界面",
        "expected_strategy": "single_agent",
        "expected_agents": ["ui_designer_agent"]
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
```

## 🔧 **关键技术实现**

### 1. **LLM驱动的任务分析**

```python
async def process_task_with_llm(self, task_id: str, task_data: Dict[str, Any]) -> Dict[str, Any]:
    """使用LLM处理任务的核心逻辑 - 完全由LLM决定如何处理任务，无任何硬编码逻辑"""
    
    # 构建系统上下文给LLM
    system_context = await self._build_system_context()
    
    # LLM分析提示 - 要求返回JSON格式的执行计划
    analysis_prompt = f"""
    你是一个多Agent系统的协调者...
    
    可用的系统资源：
    {json.dumps(system_context, indent=2, ensure_ascii=False)}
    
    用户任务：{description}
    
    请分析这个任务并制定执行计划。你的回复必须是有效的JSON格式...
    """
    
    # 获取LLM分析结果
    llm_response = await self.llm_client.send_message(message=analysis_prompt)
    
    # 解析LLM返回的JSON决策
    llm_decision = json.loads(llm_response)
    
    # 根据LLM决策执行任务
    result = await self._execute_llm_plan(task_id, llm_decision)
    
    return result
```

### 2. **动态Agent发现**

```python
async def _discover_single_agent(self, endpoint: str):
    """发现单个agent"""
    async with httpx.AsyncClient() as client:
        # 尝试A2A协议发现
        try:
            # 检查 /.well-known/agent.json (A2A标准)
            response = await client.get(f"{endpoint}/.well-known/agent.json", timeout=5.0)
            if response.status_code == 200:
                agent_card = response.json()
                agent_id = agent_card.get("name", "unknown").lower().replace(" ", "_")
                self.discovered_agents[agent_id] = {
                    "endpoint": endpoint,
                    "agent_card": agent_card,
                    "protocol": "a2a",
                    "discovery_method": "agent_card"
                }
                return
        except:
            pass
            
        # 尝试传统能力端点...
        # 尝试健康检查端点...
```

### 3. **A2A协议调用**

```python
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
                    {"type": "text", "text": task_data["description"]},
                    {"type": "data", "data": task_data.get("context", {})}
                ]
            },
            "acceptedOutputModes": ["text", "application/json"]
        }
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(endpoint, json=a2a_request, ...)
        
        if response.status_code == 200:
            result = response.json()
            if "result" in result:
                return {"success": True, "result": result["result"], "protocol": "a2a"}
```

## 📊 **测试结果评估**

### 1. **LLM决策质量评分**

```python
# 评估LLM决策质量
strategy_match = actual_strategy == test_case["expected_strategy"]
agent_match = set(actual_agents) == set(test_case["expected_agents"])

quality_score = 0
if strategy_match:
    quality_score += 40  # 策略正确性 40分
if agent_match:
    quality_score += 40  # Agent选择正确性 40分
if successful_steps == total_steps:
    quality_score += 20  # 执行成功率 20分
```

**质量评估标准：**
- 🏆 **90-100分** - 优秀，LLM决策完全正确
- 🥇 **70-89分** - 良好，LLM决策基本正确
- 🥈 **50-69分** - 一般，LLM决策部分正确
- 🥉 **0-49分** - 需要改进

### 2. **系统性能指标**

- ⏱️ **响应时间** - 每个任务的端到端处理时间
- 🎯 **决策准确性** - LLM选择的策略和agents是否合适
- 📈 **执行成功率** - 制定的执行计划中成功完成的步骤比例
- 🔄 **通信成功率** - A2A协议调用的成功率

### 3. **预期测试结果**

```
📊 真实多Agent系统测试总结
============================================================
总测试数: 5
成功测试: 5
失败测试: 0
成功率: 100.0%
平均耗时: 8.5s
平均LLM决策质量: 85.2/100

📋 详细结果:
  ✅ 简单设计任务
     🎯 策略: single_agent
     👥 agents: ui_designer_agent
     ⏱️  耗时: 5.2s
     🏆 质量: 100/100
     📈 执行率: 100.0%

  ✅ 多Agent协作任务
     🎯 策略: multi_agent
     👥 agents: user_research_agent, product_manager_agent, ui_designer_agent
     ⏱️  耗时: 12.8s
     🏆 质量: 80/100
     📈 执行率: 100.0%
```

## 🚀 **运行指令**

### 快速开始

```bash
# 1. 确保所有依赖已安装
pip install -r requirements.txt

# 2. 运行真实多Agent系统测试
python3 real_multi_agent_system_test.py

# 3. 观察输出，验证：
#    - Agent发现机制是否正常
#    - LLM决策质量如何
#    - A2A协议通信是否成功
#    - 任务执行结果是否正确
```

### 手动测试

```bash
# 启动individual agents for debugging
python3 specialist-agents/ui-designer-agent/main_a2a_compliant.py &
python3 specialist-agents/user-research-agent/server_with_cursor_mcp.py &
python3 specialist-agents/product-manager-agent/server_with_cursor_mcp.py &

# 启动LLM驱动的Common Agent
python3 common-agent/src/common_agent_llm_driven.py

# 手动提交任务测试
curl -X POST http://localhost:8000/task \
  -H "Content-Type: application/json" \
  -d '{"description": "为移动应用设计一个登录界面", "type": "test"}'
```

## 🔍 **故障排除**

### 常见问题

1. **LLM API密钥未设置**
   ```bash
   export SILICONFLOW_API_KEY="your-api-key"
   ```

2. **Agent启动失败**
   - 检查端口是否被占用
   - 确认Python路径和依赖

3. **A2A通信失败**
   - 验证agent是否支持A2A协议
   - 检查JSON-RPC格式是否正确

4. **LLM决策质量低**
   - 检查LLM模型配置
   - 优化提示词模板
   - 增加系统上下文信息

### 调试模式

```bash
# 启用详细日志
export LOG_LEVEL=DEBUG
python3 real_multi_agent_system_test.py
```

## 📝 **总结**

这是一个**完全符合要求**的真实多Agent系统：

✅ **LLM驱动** - 没有硬编码决策逻辑  
✅ **A2A协议** - 标准agent间通信  
✅ **动态发现** - 运行时发现agents  
✅ **真实工具** - 集成真实MCP工具  
✅ **零Mock** - 所有功能都是真实实现

通过这个测试框架，你可以验证整个多Agent系统的真实工作能力，包括LLM的智能决策、agents的协作能力、以及MCP工具的集成效果。 