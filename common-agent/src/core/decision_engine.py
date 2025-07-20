"""
Decision Engine

Advanced decision-making engine for the common agent.
"""

import json
import re
from typing import Dict, List, Any, Optional, Tuple
from enum import Enum


class DecisionType(Enum):
    """Types of decisions the engine can make"""
    AGENT_DELEGATION = "agent_delegation"
    MCP_TOOL_CALL = "mcp_tool_call"
    HYBRID_APPROACH = "hybrid_approach"
    USER_CLARIFICATION = "user_clarification"
    DIRECT_RESPONSE = "direct_response"


class Priority(Enum):
    """Priority levels for tasks"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


class DecisionEngine:
    """Advanced decision-making engine"""
    
    def __init__(self):
        self.decision_patterns = self._load_decision_patterns()
        self.agent_capabilities = self._load_agent_capabilities()
        self.decision_history: List[Dict[str, Any]] = []
    
    def _load_decision_patterns(self) -> Dict[str, Any]:
        """Load decision-making patterns and rules"""
        return {
            "keywords": {
                "user_research": [
                    "market analysis", "user survey", "competitive analysis",
                    "user research", "market research", "competitor", "user persona",
                    "market trends", "user behavior", "customer research"
                ],
                "product_management": [
                    "requirements", "feature prioritization", "roadmap", "backlog",
                    "product strategy", "stakeholder", "business goals", "mvp",
                    "product planning", "feature specification"
                ],
                "ui_design": [
                    "wireframe", "mockup", "design", "ui", "ux", "interface",
                    "prototype", "design system", "visual design", "user interface",
                    "design review", "component"
                ]
                # 🎯 移除硬编码的工具分类 - 工具选择由LLM动态决策
            },
            "complexity_indicators": [
                "multiple", "complex", "comprehensive", "detailed", "complete",
                "full", "entire", "end-to-end", "integrated"
            ],
            "urgency_indicators": [
                "urgent", "asap", "immediately", "quick", "fast", "now",
                "emergency", "critical", "deadline"
            ]
        }
    
    def _load_agent_capabilities(self) -> Dict[str, Dict[str, Any]]:
        """动态加载agent capabilities - 无硬编码"""
        # 🎯 移除硬编码的capabilities映射
        # 现在所有capabilities通过A2A协议动态获取
        # LLM将基于实时发现的agent信息进行决策
        return {
            # 此mapping已弃用 - 使用A2A动态发现的agent信息
            # 参见: Common Agent的discover_agents()方法
        }
    
    def analyze_request(self, user_input: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze user request and determine approach"""
        
        # Normalize input
        normalized_input = user_input.lower().strip()
        
        # Extract key information
        analysis = {
            "original_request": user_input,
            "normalized_input": normalized_input,
            "keywords_found": self._extract_keywords(normalized_input),
            "complexity_level": self._assess_complexity(normalized_input),
            "urgency_level": self._assess_urgency(normalized_input),
            "domain_areas": self._identify_domains(normalized_input),
            "specific_requests": self._extract_specific_requests(normalized_input),
            "context_relevance": self._assess_context_relevance(context)
        }
        
        return analysis
    
    def make_decision(
        self, 
        analysis: Dict[str, Any], 
        available_agents: List[Dict[str, Any]],
        available_tools: Dict[str, List[str]]
    ) -> Dict[str, Any]:
        """Make decision based on analysis"""
        
        # Determine decision type
        decision_type = self._determine_decision_type(analysis, available_agents, available_tools)
        
        # Create execution plan
        plan = self._create_execution_plan(decision_type, analysis, available_agents, available_tools)
        
        # Calculate confidence and priority
        confidence = self._calculate_confidence(analysis, plan)
        priority = self._determine_priority(analysis)
        
        decision = {
            "decision_id": len(self.decision_history) + 1,
            "decision_type": decision_type.value,
            "analysis": analysis,
            "plan": plan,
            "confidence": confidence,
            "priority": priority.value,
            "reasoning": self._generate_reasoning(decision_type, analysis, plan),
            "alternatives": self._suggest_alternatives(analysis, available_agents, available_tools)
        }
        
        # Record decision
        self.decision_history.append(decision)
        
        return decision
    
    def _extract_keywords(self, text: str) -> Dict[str, List[str]]:
        """Extract relevant keywords from text"""
        found_keywords = {}
        
        for category, keywords in self.decision_patterns["keywords"].items():
            found = [kw for kw in keywords if kw in text]
            if found:
                found_keywords[category] = found
        
        return found_keywords
    
    def _assess_complexity(self, text: str) -> str:
        """Assess complexity level of the request"""
        complexity_count = sum(1 for indicator in self.decision_patterns["complexity_indicators"] 
                             if indicator in text)
        
        if complexity_count >= 3:
            return "high"
        elif complexity_count >= 1:
            return "medium"
        else:
            return "low"
    
    def _assess_urgency(self, text: str) -> str:
        """Assess urgency level of the request"""
        urgency_count = sum(1 for indicator in self.decision_patterns["urgency_indicators"]
                          if indicator in text)
        
        if urgency_count >= 2:
            return "high"
        elif urgency_count >= 1:
            return "medium"
        else:
            return "low"
    
    def _identify_domains(self, text: str) -> List[str]:
        """Identify relevant domain areas"""
        domains = []
        keywords_found = self._extract_keywords(text)
        
        for domain, keywords in keywords_found.items():
            if keywords:
                domains.append(domain)
        
        return domains
    
    def _extract_specific_requests(self, text: str) -> List[str]:
        """Extract specific actionable requests"""
        # Simple pattern matching for specific requests
        patterns = [
            r"create (\w+)",
            r"design (\w+)",
            r"analyze (\w+)",
            r"research (\w+)",
            r"build (\w+)",
            r"develop (\w+)"
        ]
        
        requests = []
        for pattern in patterns:
            matches = re.findall(pattern, text)
            requests.extend(matches)
        
        return requests
    
    def _assess_context_relevance(self, context: Dict[str, Any]) -> str:
        """Assess how relevant the current context is"""
        if not context:
            return "none"
        
        relevant_keys = ["last_task_result", "ongoing_project", "user_preferences"]
        relevant_count = sum(1 for key in relevant_keys if key in context)
        
        if relevant_count >= 2:
            return "high"
        elif relevant_count >= 1:
            return "medium"
        else:
            return "low"
    
    def _determine_decision_type(
        self, 
        analysis: Dict[str, Any],
        available_agents: List[Dict[str, Any]],
        available_tools: Dict[str, List[str]]
    ) -> DecisionType:
        """Determine the type of decision to make"""
        
        domains = analysis["domain_areas"]
        complexity = analysis["complexity_level"]
        
        # Check if we need clarification
        if not domains and analysis["specific_requests"]:
            return DecisionType.USER_CLARIFICATION
        
        # Single domain, low complexity - direct agent delegation
        if len(domains) == 1 and complexity == "low":
            return DecisionType.AGENT_DELEGATION
        
        # Multiple domains or high complexity - hybrid approach
        if len(domains) > 1 or complexity == "high":
            return DecisionType.HYBRID_APPROACH
        
        # 🎯 移除硬编码的工具检查 - 让LLM决策工具使用
        
        # Default to agent delegation
        return DecisionType.AGENT_DELEGATION
    
    def _create_execution_plan(
        self,
        decision_type: DecisionType,
        analysis: Dict[str, Any],
        available_agents: List[Dict[str, Any]],
        available_tools: Dict[str, List[str]]
    ) -> Dict[str, Any]:
        """Create detailed execution plan"""
        
        plan = {
            "approach": "",
            "steps": [],
            "expected_outcome": "",
            "estimated_time": "",
            "resources_needed": []
        }
        
        if decision_type == DecisionType.AGENT_DELEGATION:
            plan = self._create_agent_delegation_plan(analysis, available_agents)
        
        elif decision_type == DecisionType.MCP_TOOL_CALL:
            plan = self._create_mcp_tool_plan(analysis, available_tools)
        
        elif decision_type == DecisionType.HYBRID_APPROACH:
            plan = self._create_hybrid_plan(analysis, available_agents, available_tools)
        
        elif decision_type == DecisionType.USER_CLARIFICATION:
            plan = self._create_clarification_plan(analysis)
        
        else:  # DIRECT_RESPONSE
            plan = self._create_direct_response_plan(analysis)
        
        return plan
    
    def _create_agent_delegation_plan(
        self, 
        analysis: Dict[str, Any], 
        available_agents: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Create plan for single agent delegation"""
        
        domain = analysis["domain_areas"][0] if analysis["domain_areas"] else "user_research"
        
        # Find best matching agent
        target_agent = None
        for agent in available_agents:
            if domain.replace("_", "-") in agent["name"].lower():
                target_agent = agent
                break
        
        if not target_agent and available_agents:
            target_agent = available_agents[0]  # Fallback
        
        return {
            "approach": f"Delegate to {domain} specialist agent",
            "steps": [
                {
                    "type": "agent",
                    "target": domain,
                    "action": self._select_agent_capability(domain, analysis),
                    "parameters": self._extract_agent_parameters(analysis),
                    "reason": f"Specialized {domain} expertise required"
                }
            ],
            "expected_outcome": f"Specialized {domain} deliverable",
            "estimated_time": "5-10 minutes",
            "resources_needed": [domain + " agent"]
        }
    
    def _create_mcp_tool_plan(
        self, 
        analysis: Dict[str, Any], 
        available_tools: Dict[str, List[str]]
    ) -> Dict[str, Any]:
        """Create plan for MCP tool usage"""
        
        return {
            "approach": "Use MCP tools for direct task execution",
            "steps": [
                {
                    "type": "mcp",
                    "target": "figma",
                    "action": "get_figma_files",
                    "parameters": {"team_id": "default"},
                    "reason": "Direct access to Figma resources needed"
                }
            ],
            "expected_outcome": "Direct tool results",
            "estimated_time": "2-5 minutes",
            "resources_needed": ["figma MCP server"]
        }
    
    def _create_hybrid_plan(
        self,
        analysis: Dict[str, Any],
        available_agents: List[Dict[str, Any]],
        available_tools: Dict[str, List[str]]
    ) -> Dict[str, Any]:
        """Create plan combining multiple agents and tools"""
        
        domains = analysis["domain_areas"]
        steps = []
        
        # Add steps for each relevant domain
        for i, domain in enumerate(domains):
            steps.append({
                "type": "agent",
                "target": domain,
                "action": self._select_agent_capability(domain, analysis),
                "parameters": self._extract_agent_parameters(analysis),
                "reason": f"Step {i+1}: {domain} expertise needed"
            })
        
        # 🎯 移除硬编码的MCP工具步骤 - 让LLM动态决策工具使用
        
        return {
            "approach": "Multi-step approach using multiple specialists",
            "steps": steps,
            "expected_outcome": "Comprehensive solution addressing all aspects",
            "estimated_time": f"{len(steps)*5}-{len(steps)*10} minutes",
            "resources_needed": domains  # 纯净的域列表，无硬编码工具
        }
    
    def _create_clarification_plan(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Create plan for requesting user clarification"""
        
        return {
            "approach": "Request clarification from user",
            "steps": [
                {
                    "type": "user_input",
                    "target": "user",
                    "action": "clarify_requirements",
                    "parameters": {"questions": self._generate_clarification_questions(analysis)},
                    "reason": "Need more specific information to proceed"
                }
            ],
            "expected_outcome": "Clarified requirements for better assistance",
            "estimated_time": "1-2 minutes",
            "resources_needed": ["user input"]
        }
    
    def _create_direct_response_plan(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Create plan for direct response"""
        
        return {
            "approach": "Provide direct response",
            "steps": [
                {
                    "type": "direct",
                    "target": "system",
                    "action": "generate_response",
                    "parameters": {"analysis": analysis},
                    "reason": "Simple request can be handled directly"
                }
            ],
            "expected_outcome": "Direct helpful response",
            "estimated_time": "1 minute",
            "resources_needed": ["system knowledge"]
        }
    
    def _select_agent_capability(self, domain: str, analysis: Dict[str, Any]) -> str:
        """Select appropriate capability for an agent"""
        
        agent_caps = self.agent_capabilities.get(domain, {}).get("capabilities", [])
        
        if not agent_caps:
            return "general_task"
        
        # Simple matching based on keywords
        keywords_found = analysis.get("keywords_found", {}).get(domain, [])
        
        if "analysis" in " ".join(keywords_found):
            return [cap for cap in agent_caps if "analysis" in cap][0] if any("analysis" in cap for cap in agent_caps) else agent_caps[0]
        
        return agent_caps[0]  # Default to first capability
    
    def _extract_agent_parameters(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Extract parameters for agent calls"""
        
        return {
            "request_type": analysis.get("complexity_level", "medium"),
            "specific_requests": analysis.get("specific_requests", []),
            "urgency": analysis.get("urgency_level", "medium")
        }
    
    def _generate_clarification_questions(self, analysis: Dict[str, Any]) -> List[str]:
        """Generate questions for user clarification"""
        
        questions = []
        
        if not analysis.get("domain_areas"):
            questions.append("What specific area would you like help with? (design, research, product management)")
        
        if analysis.get("complexity_level") == "high":
            questions.append("Could you break down your request into smaller, specific tasks?")
        
        if not analysis.get("specific_requests"):
            questions.append("What specific deliverable or outcome are you looking for?")
        
        return questions or ["Could you provide more details about what you'd like me to help you with?"]
    
    def _calculate_confidence(self, analysis: Dict[str, Any], plan: Dict[str, Any]) -> float:
        """Calculate confidence in the decision"""
        
        confidence = 0.5  # Base confidence
        
        # Increase confidence for clear domain identification
        if analysis.get("domain_areas"):
            confidence += 0.2
        
        # Increase confidence for specific requests
        if analysis.get("specific_requests"):
            confidence += 0.2
        
        # Increase confidence for detailed plan
        if len(plan.get("steps", [])) > 0:
            confidence += 0.1
        
        return min(confidence, 1.0)
    
    def _determine_priority(self, analysis: Dict[str, Any]) -> Priority:
        """Determine task priority"""
        
        urgency = analysis.get("urgency_level", "low")
        complexity = analysis.get("complexity_level", "low")
        
        if urgency == "high":
            return Priority.HIGH
        elif urgency == "medium" or complexity == "high":
            return Priority.MEDIUM
        else:
            return Priority.LOW
    
    def _generate_reasoning(
        self, 
        decision_type: DecisionType, 
        analysis: Dict[str, Any], 
        plan: Dict[str, Any]
    ) -> str:
        """Generate human-readable reasoning for the decision"""
        
        reasoning_parts = []
        
        # Domain analysis
        domains = analysis.get("domain_areas", [])
        if domains:
            reasoning_parts.append(f"Identified {len(domains)} relevant domain(s): {', '.join(domains)}")
        
        # Complexity assessment
        complexity = analysis.get("complexity_level", "low")
        reasoning_parts.append(f"Assessed complexity as {complexity}")
        
        # Decision rationale
        if decision_type == DecisionType.AGENT_DELEGATION:
            reasoning_parts.append("Single specialist agent can handle this request effectively")
        elif decision_type == DecisionType.HYBRID_APPROACH:
            reasoning_parts.append("Multiple specialists needed for comprehensive solution")
        elif decision_type == DecisionType.MCP_TOOL_CALL:
            reasoning_parts.append("Direct tool access provides most efficient solution")
        
        return ". ".join(reasoning_parts) + "."
    
    def _suggest_alternatives(
        self,
        analysis: Dict[str, Any],
        available_agents: List[Dict[str, Any]],
        available_tools: Dict[str, List[str]]
    ) -> List[Dict[str, Any]]:
        """Suggest alternative approaches"""
        
        alternatives = []
        
        # Always suggest a simpler approach
        alternatives.append({
            "approach": "Simplified approach",
            "description": "Break down into smaller, sequential tasks",
            "confidence": 0.7
        })
        
        # Suggest different agent combinations
        if len(analysis.get("domain_areas", [])) > 1:
            alternatives.append({
                "approach": "Sequential specialist consultation",
                "description": "Consult each specialist separately in sequence",
                "confidence": 0.6
            })
        
        return alternatives 