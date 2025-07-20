"""
Enumeration types used across the system
"""

from enum import Enum


class AgentType(str, Enum):
    """Agent types"""
    COMMON = "common"
    USER_RESEARCH = "user_research"
    PRODUCT_MANAGER = "product_manager"
    UI_DESIGNER = "ui_designer"


class MessageType(str, Enum):
    """Message types"""
    REQUEST = "request"
    RESPONSE = "response"
    REGISTRATION = "registration"
    HEARTBEAT = "heartbeat"
    NOTIFICATION = "notification"
    ERROR = "error"


class TaskStatus(str, Enum):
    """Task execution status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class MCPToolType(str, Enum):
    """MCP tool types"""
    FUNCTION = "function"
    RESOURCE = "resource"
    PROMPT = "prompt" 