"""
Enhanced Logging System

Provides detailed logging for the multi-agent system workflow.
"""

import logging
import json
import time
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path


class WorkflowLogger:
    """Enhanced logger for multi-agent workflow tracking"""
    
    def __init__(self, agent_id: str, log_dir: str = "logs"):
        self.agent_id = agent_id
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        
        # Setup structured logging
        self.logger = self._setup_logger()
        self.session_id = None
        self.request_start_time = None
        
    def _setup_logger(self) -> logging.Logger:
        """Setup enhanced logger with file and console output"""
        logger = logging.getLogger(f"{self.agent_id}_workflow")
        logger.setLevel(logging.INFO)
        
        # Remove existing handlers
        logger.handlers.clear()
        
        # File handler
        log_file = self.log_dir / f"{self.agent_id}_workflow.log"
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.INFO)
        
        # Console handler  
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s | %(name)s | %(levelname)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        
        return logger
    
    def start_request(self, user_request: str, session_id: str = None) -> str:
        """Start logging a new request"""
        self.session_id = session_id or f"session_{int(time.time())}"
        self.request_start_time = time.time()
        
        self.logger.info("="*80)
        self.logger.info(f"🚀 REQUEST START | Session: {self.session_id}")
        self.logger.info(f"📝 User Request: {user_request}")
        self.logger.info(f"🤖 Agent: {self.agent_id}")
        self.logger.info("="*80)
        
        return self.session_id
    
    def log_llm_request(self, prompt: str, system_prompt: str = None):
        """Log LLM request details"""
        self.logger.info("🧠 LLM REQUEST")
        self.logger.info(f"📤 System Prompt: {system_prompt[:200] if system_prompt else 'None'}...")
        self.logger.info(f"📤 User Prompt: {prompt[:300]}...")
        
    def log_llm_response(self, response: str, processing_time: float):
        """Log LLM response details"""
        self.logger.info("🧠 LLM RESPONSE")
        self.logger.info(f"📥 Response: {response[:300]}...")
        self.logger.info(f"⏱️ Processing Time: {processing_time:.2f}s")
        
    def log_decision_analysis(self, decision: Dict[str, Any]):
        """Log decision analysis results"""
        self.logger.info("🎯 DECISION ANALYSIS")
        self.logger.info(f"📊 Approach: {decision.get('approach', 'Unknown')}")
        self.logger.info(f"💭 Reasoning: {decision.get('reasoning', 'No reasoning provided')}")
        
        if 'steps' in decision:
            self.logger.info(f"📋 Execution Steps: {len(decision['steps'])} steps planned")
            for i, step in enumerate(decision['steps'][:3]):  # Log first 3 steps
                self.logger.info(f"   {i+1}. {step.get('type', 'unknown')} -> {step.get('action', 'unknown')}")
    
    def log_agent_call(self, target_agent: str, capability: str, parameters: Dict[str, Any]):
        """Log agent-to-agent communication"""
        self.logger.info("🔄 A2A COMMUNICATION")
        self.logger.info(f"🎯 Target Agent: {target_agent}")
        self.logger.info(f"⚡ Capability: {capability}")
        self.logger.info(f"📦 Parameters: {json.dumps(parameters, ensure_ascii=False)[:200]}...")
        
    def log_agent_response(self, target_agent: str, response: Dict[str, Any], success: bool):
        """Log agent response"""
        status = "✅ SUCCESS" if success else "❌ FAILED"
        self.logger.info(f"📨 A2A RESPONSE | {status}")
        self.logger.info(f"🤖 From Agent: {target_agent}")
        
        if success and 'result' in response:
            result = response['result']
            if isinstance(result, dict):
                self.logger.info(f"📊 Result Fields: {list(result.keys())[:5]}")
                # Log key insights
                for key in ['insights', 'recommendations', 'summary', 'analysis']:
                    if key in result:
                        value = str(result[key])[:150]
                        self.logger.info(f"   {key.title()}: {value}...")
        elif not success:
            error = response.get('error', 'Unknown error')
            self.logger.info(f"❌ Error: {error}")
    
    def log_mcp_call(self, tool_name: str, parameters: Dict[str, Any]):
        """Log MCP tool call"""
        self.logger.info("🔧 MCP TOOL CALL")
        self.logger.info(f"🛠️ Tool: {tool_name}")
        self.logger.info(f"📦 Parameters: {json.dumps(parameters, ensure_ascii=False)[:200]}...")
        
    def log_mcp_response(self, tool_name: str, response: Any, success: bool):
        """Log MCP tool response"""
        status = "✅ SUCCESS" if success else "❌ FAILED"
        self.logger.info(f"🔧 MCP RESPONSE | {status}")
        self.logger.info(f"🛠️ Tool: {tool_name}")
        
        if success:
            response_str = str(response)[:200] if response else "Empty response"
            self.logger.info(f"📊 Response: {response_str}...")
        else:
            self.logger.info(f"❌ Error: {response}")
    
    def log_step_execution(self, step_num: int, step_type: str, step_action: str, success: bool):
        """Log step execution"""
        status = "✅" if success else "❌"
        self.logger.info(f"📋 STEP {step_num} | {status} {step_type.upper()}")
        self.logger.info(f"🎬 Action: {step_action}")
        
    def log_final_response(self, response: str):
        """Log final response to user"""
        elapsed_time = time.time() - self.request_start_time if self.request_start_time else 0
        
        self.logger.info("🎯 FINAL RESPONSE")
        self.logger.info(f"📝 Response: {response[:400]}...")
        self.logger.info(f"⏱️ Total Processing Time: {elapsed_time:.2f}s")
        self.logger.info("="*80)
        self.logger.info(f"✅ REQUEST COMPLETE | Session: {self.session_id}")
        self.logger.info("="*80)
    
    def log_error(self, error_type: str, error_message: str, context: Dict[str, Any] = None):
        """Log error with context"""
        self.logger.error(f"❌ ERROR | {error_type}")
        self.logger.error(f"💥 Message: {error_message}")
        if context:
            self.logger.error(f"🔍 Context: {json.dumps(context, ensure_ascii=False)[:300]}")
    
    def log_capability_registration(self, capability: str, description: str):
        """Log capability registration"""
        self.logger.info(f"⚡ CAPABILITY REGISTERED: {capability}")
        self.logger.info(f"📄 Description: {description}")
    
    def log_system_status(self, status: str, details: Dict[str, Any] = None):
        """Log system status changes"""
        self.logger.info(f"🔄 SYSTEM STATUS: {status}")
        if details:
            for key, value in details.items():
                self.logger.info(f"   {key}: {value}")


# Global logger instances
_loggers: Dict[str, WorkflowLogger] = {}

def get_logger(agent_id: str) -> WorkflowLogger:
    """Get or create logger for agent"""
    if agent_id not in _loggers:
        _loggers[agent_id] = WorkflowLogger(agent_id)
    return _loggers[agent_id] 