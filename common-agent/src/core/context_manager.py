"""
Context Manager

Manages conversation context and task state for the common agent.
"""

import json
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from pathlib import Path
import aiofiles


class ContextManager:
    """Manages conversation context and task history"""
    
    def __init__(self, max_history: int = 100, save_path: Optional[str] = None):
        self.max_history = max_history
        self.save_path = Path(save_path) if save_path else Path("conversations")
        self.current_context: Dict[str, Any] = {}
        self.conversation_history: List[Dict[str, Any]] = []
        self.task_history: List[Dict[str, Any]] = []
        self.session_id = self._generate_session_id()
        
        # Ensure save directory exists
        self.save_path.mkdir(exist_ok=True)
    
    def _generate_session_id(self) -> str:
        """Generate a unique session ID"""
        from uuid import uuid4
        return f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{str(uuid4())[:8]}"
    
    def update_context(self, key: str, value: Any):
        """Update context with new information"""
        self.current_context[key] = {
            "value": value,
            "timestamp": datetime.now().isoformat(),
            "type": type(value).__name__
        }
        
        # Keep context size manageable
        if len(self.current_context) > self.max_history:
            # Remove oldest entries
            oldest_keys = sorted(
                self.current_context.keys(),
                key=lambda k: self.current_context[k]["timestamp"]
            )[:len(self.current_context) - self.max_history]
            
            for key in oldest_keys:
                del self.current_context[key]
    
    def get_context(self, key: Optional[str] = None) -> Any:
        """Get context value or entire context"""
        if key is None:
            return {k: v["value"] for k, v in self.current_context.items()}
        
        return self.current_context.get(key, {}).get("value")
    
    def add_conversation_turn(
        self,
        user_input: str,
        agent_response: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Add a conversation turn to history"""
        turn = {
            "timestamp": datetime.now().isoformat(),
            "user_input": user_input,
            "agent_response": agent_response,
            "metadata": metadata or {},
            "turn_id": len(self.conversation_history) + 1
        }
        
        self.conversation_history.append(turn)
        
        # Maintain history limit
        if len(self.conversation_history) > self.max_history:
            self.conversation_history = self.conversation_history[-self.max_history:]
    
    def add_task_execution(
        self,
        task_description: str,
        plan: Dict[str, Any],
        results: List[Dict[str, Any]],
        success: bool
    ):
        """Add task execution to history"""
        task = {
            "timestamp": datetime.now().isoformat(),
            "task_id": len(self.task_history) + 1,
            "description": task_description,
            "plan": plan,
            "results": results,
            "success": success,
            "execution_time": self._calculate_execution_time(results)
        }
        
        self.task_history.append(task)
        
        # Update context with task result
        self.update_context(f"last_task_result", {
            "success": success,
            "description": task_description,
            "summary": self._summarize_task_results(results)
        })
    
    def _calculate_execution_time(self, results: List[Dict[str, Any]]) -> Optional[float]:
        """Calculate task execution time from results"""
        try:
            if not results:
                return None
            
            # This is a simplified calculation
            # In a real implementation, you'd track actual timing
            return len(results) * 2.5  # Approximate seconds per step
            
        except Exception:
            return None
    
    def _summarize_task_results(self, results: List[Dict[str, Any]]) -> str:
        """Create a summary of task results"""
        if not results:
            return "No results"
        
        successful_steps = sum(1 for r in results if r.get("result", {}).get("success", True))
        total_steps = len(results)
        
        return f"Completed {successful_steps}/{total_steps} steps successfully"
    
    def get_recent_context(self, minutes: int = 30) -> Dict[str, Any]:
        """Get context from recent activity"""
        cutoff_time = datetime.now() - timedelta(minutes=minutes)
        
        recent_context = {}
        for key, value_info in self.current_context.items():
            timestamp = datetime.fromisoformat(value_info["timestamp"])
            if timestamp > cutoff_time:
                recent_context[key] = value_info["value"]
        
        return recent_context
    
    def get_conversation_summary(self, last_n: int = 5) -> str:
        """Get a summary of recent conversation"""
        if not self.conversation_history:
            return "No previous conversation"
        
        recent_turns = self.conversation_history[-last_n:]
        
        summary_parts = []
        for turn in recent_turns:
            summary_parts.append(f"User: {turn['user_input'][:100]}...")
            summary_parts.append(f"Agent: {turn['agent_response'][:100]}...")
        
        return "\n".join(summary_parts)
    
    def clear_context(self):
        """Clear current context"""
        self.current_context.clear()
        self.update_context("context_cleared", True)
    
    def clear_history(self):
        """Clear conversation and task history"""
        self.conversation_history.clear()
        self.task_history.clear()
        self.update_context("history_cleared", True)
    
    async def save_session(self) -> bool:
        """Save current session to file"""
        try:
            session_data = {
                "session_id": self.session_id,
                "timestamp": datetime.now().isoformat(),
                "context": self.current_context,
                "conversation_history": self.conversation_history,
                "task_history": self.task_history
            }
            
            file_path = self.save_path / f"{self.session_id}.json"
            
            async with aiofiles.open(file_path, 'w') as f:
                await f.write(json.dumps(session_data, indent=2))
            
            return True
            
        except Exception as e:
            print(f"Error saving session: {e}")
            return False
    
    async def load_session(self, session_id: str) -> bool:
        """Load session from file"""
        try:
            file_path = self.save_path / f"{session_id}.json"
            
            if not file_path.exists():
                return False
            
            async with aiofiles.open(file_path, 'r') as f:
                content = await f.read()
                session_data = json.loads(content)
            
            self.session_id = session_data["session_id"]
            self.current_context = session_data.get("context", {})
            self.conversation_history = session_data.get("conversation_history", [])
            self.task_history = session_data.get("task_history", [])
            
            return True
            
        except Exception as e:
            print(f"Error loading session: {e}")
            return False
    
    def get_session_stats(self) -> Dict[str, Any]:
        """Get statistics about the current session"""
        return {
            "session_id": self.session_id,
            "conversation_turns": len(self.conversation_history),
            "completed_tasks": len(self.task_history),
            "successful_tasks": sum(1 for task in self.task_history if task["success"]),
            "context_entries": len(self.current_context),
            "session_duration": self._calculate_session_duration()
        }
    
    def _calculate_session_duration(self) -> Optional[str]:
        """Calculate session duration"""
        if not self.conversation_history:
            return None
        
        try:
            start_time = datetime.fromisoformat(self.conversation_history[0]["timestamp"])
            end_time = datetime.fromisoformat(self.conversation_history[-1]["timestamp"])
            duration = end_time - start_time
            
            return str(duration).split('.')[0]  # Remove microseconds
            
        except Exception:
            return None 