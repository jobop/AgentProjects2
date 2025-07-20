"""
LLM Client

Generic client for communicating with various LLM providers.
"""

from typing import Dict, List, Any, Optional, AsyncGenerator
from abc import ABC, abstractmethod
import json
import sys
import os

# Add shared modules to path  
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "..", "shared"))

from common_types.base import LLMConfig


class LLMProvider(ABC):
    """Abstract base class for LLM providers"""
    
    @abstractmethod
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        **kwargs
    ) -> Dict[str, Any]:
        """Send chat completion request"""
        pass
    
    @abstractmethod
    async def stream_completion(
        self,
        messages: List[Dict[str, str]],
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """Stream chat completion"""
        pass


class LLMClient:
    """Generic LLM client that can work with different providers"""
    
    def __init__(self, config: LLMConfig, provider: LLMProvider):
        self.config = config
        self.provider = provider
        self.conversation_history: List[Dict[str, str]] = []
    
    async def send_message(
        self,
        message: str,
        system_prompt: Optional[str] = None,
        include_history: bool = True,
        **kwargs
    ) -> str:
        """Send a message to the LLM and get response"""
        
        messages = []
        
        # Add system prompt if provided
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        # Add conversation history if requested
        if include_history:
            messages.extend(self.conversation_history)
        
        # Add current user message
        messages.append({"role": "user", "content": message})
        
        # Send to provider
        response = await self.provider.chat_completion(
            messages=messages,
            max_tokens=self.config.max_tokens,
            temperature=self.config.temperature,
            **kwargs
        )
        
        # Extract response text
        assistant_message = response.get("choices", [{}])[0].get("message", {}).get("content", "")
        
        # Update conversation history
        if include_history:
            self.conversation_history.append({"role": "user", "content": message})
            self.conversation_history.append({"role": "assistant", "content": assistant_message})
            
            # Keep history within reasonable limits
            max_history = 20  # Keep last 20 messages
            if len(self.conversation_history) > max_history:
                self.conversation_history = self.conversation_history[-max_history:]
        
        return assistant_message
    
    async def stream_message(
        self,
        message: str,
        system_prompt: Optional[str] = None,
        include_history: bool = True,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """Stream a message to the LLM"""
        
        messages = []
        
        # Add system prompt if provided
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        # Add conversation history if requested
        if include_history:
            messages.extend(self.conversation_history)
        
        # Add current user message
        messages.append({"role": "user", "content": message})
        
        # Stream from provider
        full_response = ""
        async for chunk in self.provider.stream_completion(
            messages=messages,
            max_tokens=self.config.max_tokens,
            temperature=self.config.temperature,
            **kwargs
        ):
            full_response += chunk
            yield chunk
        
        # Update conversation history
        if include_history:
            self.conversation_history.append({"role": "user", "content": message})
            self.conversation_history.append({"role": "assistant", "content": full_response})
    
    def clear_history(self):
        """Clear conversation history"""
        self.conversation_history.clear()
    
    def get_history(self) -> List[Dict[str, str]]:
        """Get conversation history"""
        return self.conversation_history.copy()
    
    def create_decision_prompt(
        self,
        user_request: str,
        available_mcps: List[str],
        available_agents: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Create a decision-making prompt for the LLM"""
        
        prompt = f"""You are a decision-making AI that coordinates multiple specialist agents and MCP tools to fulfill user requests.

User Request: {user_request}

Available MCP Tools:
{json.dumps(available_mcps, indent=2)}

Available Specialist Agents:
{json.dumps(available_agents, indent=2)}

Current Context:
{json.dumps(context or {}, indent=2)}

Based on this information, please decide what actions to take. You can:
1. Call specific MCP tools directly
2. Delegate tasks to specialist agents
3. Ask for more information from the user
4. Combine multiple approaches

Please respond in JSON format with your decision plan:
{{
    "approach": "description of your overall approach",
    "steps": [
        {{
            "type": "mcp|agent|user_input",
            "target": "specific MCP tool or agent name",
            "action": "what to do",
            "parameters": {{...}},
            "reason": "why this step is needed"
        }}
    ],
    "expected_outcome": "what you expect to achieve"
}}"""
        
        return prompt 