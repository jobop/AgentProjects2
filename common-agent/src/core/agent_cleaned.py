"""
Common Agent - Cleaned Implementation

Orchestrates the multi-agent system with full A2A and MCP compliance.
This version uses only the new compliant implementations.
"""

import asyncio
import json
import logging
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
import sys
import os

# Add shared modules to path  
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "..", "shared"))

from common_types.base import SystemConfig
from llm.client import LLMClient
from llm.provider_enhanced import EnhancedSiliconFlowProvider
from core.context_manager import ContextManager
from core.decision_engine import DecisionEngine
from core.logger import WorkflowLogger
from mcp import (
    MCPManager, MCPClient,
    MCP_COMPLIANT_AVAILABLE
)


class CommonAgent:
    """
    Common Agent with full A2A and MCP compliance
    
    This agent orchestrates the multi-agent system using:
    - MCP-compliant tool and resource management
    - A2A-compliant agent communication (when needed)
    - Enhanced LLM integration
    """
    
    def __init__(self, config: SystemConfig):
        self.config = config
        self.agent_id = "common_agent"
        self.agent_name = "Common Agent"
        
        # Initialize logging
        self.workflow_logger = WorkflowLogger()
        
        # Initialize LLM client with enhanced provider
        llm_provider = EnhancedSiliconFlowProvider(
            api_key=config.llm.api_key,
            model=config.llm.model,
            base_url=config.llm.base_url,
            timeout=config.llm.timeout
        )
        self.llm_client = LLMClient(config.llm, llm_provider)
        
        # Initialize MCP manager (only compliant implementation)
        if MCP_COMPLIANT_AVAILABLE:
            self.mcp_manager = MCPManager()
            self.mcp_client = MCPClient(self.mcp_manager)
            self.workflow_logger.log_system_status("Using MCP-compliant implementation")
        else:
            self.workflow_logger.log_system_status("Warning: MCP SDK not available - install 'mcp' package")
            self.mcp_manager = None
            self.mcp_client = None
        
        # Initialize other components
        self.context_manager = ContextManager()
        self.decision_engine = DecisionEngine(self.llm_client)
        
    async def initialize(self):
        """Initialize the agent and all its components"""
        try:
            self.workflow_logger.log_system_status(f"Initializing {self.agent_name}")
            
            # Initialize MCP servers if available
            if self.mcp_manager:
                await self.mcp_manager.start_servers()
                self.workflow_logger.log_system_status("MCP servers started")
            
            # TODO: Initialize A2A server when needed
            # This will be implemented when A2A agent communication is required
            
            self.workflow_logger.log_system_status(f"{self.agent_name} initialized successfully")
            return True
            
        except Exception as e:
            self.workflow_logger.log_error(f"Failed to initialize {self.agent_name}: {e}")
            return False
    
    async def process_request(self, user_input: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Process a user request using the multi-agent system
        
        Args:
            user_input: The user's request
            context: Optional context information
            
        Returns:
            Response dictionary with results
        """
        try:
            # Add context to context manager
            if context:
                await self.context_manager.add_context("user_context", context)
            
            # Make decision on how to handle the request
            decision = await self.decision_engine.analyze_request(user_input)
            
            response = {
                "success": True,
                "request": user_input,
                "decision": decision,
                "timestamp": datetime.now().isoformat(),
                "agent": self.agent_name
            }
            
            # Handle different types of requests
            if decision.get("requires_tools", False):
                # Use MCP tools if available
                if self.mcp_client:
                    tool_results = await self._execute_tools(decision.get("tools", []))
                    response["tool_results"] = tool_results
                else:
                    response["warning"] = "Tools requested but MCP not available"
            
            if decision.get("requires_delegation", False):
                # TODO: Implement A2A agent delegation
                response["delegation"] = "A2A delegation not yet implemented"
            
            # Generate final response using LLM
            llm_response = await self.llm_client.generate_response(
                prompt=f"User request: {user_input}\nContext: {json.dumps(response)}\nProvide a helpful response.",
                context=await self.context_manager.get_context()
            )
            
            response["llm_response"] = llm_response
            return response
            
        except Exception as e:
            self.workflow_logger.log_error(f"Error processing request: {e}")
            return {
                "success": False,
                "error": str(e),
                "request": user_input,
                "timestamp": datetime.now().isoformat(),
                "agent": self.agent_name
            }
    
    async def _execute_tools(self, tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Execute MCP tools"""
        results = []
        
        if not self.mcp_client:
            return [{"error": "MCP client not available"}]
        
        for tool in tools:
            try:
                tool_name = tool.get("name")
                tool_params = tool.get("parameters", {})
                
                result = await self.mcp_client.execute_tool(
                    server_name="default",  # TODO: Make configurable
                    tool_name=tool_name,
                    parameters=tool_params
                )
                
                results.append({
                    "tool": tool_name,
                    "success": True,
                    "result": result
                })
                
            except Exception as e:
                results.append({
                    "tool": tool.get("name", "unknown"),
                    "success": False,
                    "error": str(e)
                })
        
        return results
    
    async def shutdown(self):
        """Gracefully shutdown the agent"""
        try:
            self.workflow_logger.log_system_status(f"Shutting down {self.agent_name}")
            
            # Shutdown MCP servers
            if self.mcp_manager:
                await self.mcp_manager.stop_servers()
            
            # TODO: Shutdown A2A server when implemented
            
            self.workflow_logger.log_system_status(f"{self.agent_name} shutdown completed")
            
        except Exception as e:
            self.workflow_logger.log_error(f"Error during shutdown: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current agent status"""
        return {
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "mcp_available": MCP_COMPLIANT_AVAILABLE,
            "mcp_manager_active": self.mcp_manager is not None,
            "llm_client_active": self.llm_client is not None,
            "timestamp": datetime.now().isoformat()
        }
    
    # TODO: Add A2A agent communication methods when needed
    # async def communicate_with_agent(self, agent_url: str, message: str) -> Dict[str, Any]:
    #     """Communicate with another agent using A2A protocol"""
    #     pass
    
    # async def register_with_agent(self, agent_url: str) -> bool:
    #     """Register with another agent for collaboration"""
    #     pass 