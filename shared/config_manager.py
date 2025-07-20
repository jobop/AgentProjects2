#!/usr/bin/env python3
"""
配置管理器

负责读取和管理系统配置，特别是超时时间配置
"""

import os
import yaml
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        初始化配置管理器
        
        Args:
            config_path: 配置文件路径，默认为 config/system.yaml
        """
        if config_path is None:
            # 默认配置文件路径
            config_path = os.path.join(os.path.dirname(__file__), "..", "config", "system.yaml")
        
        self.config_path = os.path.abspath(config_path)
        self.config: Dict[str, Any] = {}
        
        # 默认超时配置（作为备用）
        self.default_timeouts = {
            "agent_communication": 600,  # 10分钟
            "llm_api": 600,             # 10分钟
            "mcp_tools": 600,           # 10分钟
            "http_request": 600,        # 10分钟
            "task_processing": 1800,    # 30分钟
            "health_check": 30,         # 30秒
            "agent_discovery": 60,      # 1分钟
        }
        
        self.load_config()
    
    def load_config(self):
        """加载配置文件"""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    self.config = yaml.safe_load(f) or {}
                logger.info(f"✅ 配置文件加载成功: {self.config_path}")
            else:
                logger.warning(f"⚠️ 配置文件不存在: {self.config_path}，使用默认配置")
                self.config = {}
        except Exception as e:
            logger.error(f"❌ 配置文件加载失败: {e}，使用默认配置")
            self.config = {}
    
    def get_timeout(self, timeout_type: str) -> int:
        """
        获取指定类型的超时时间
        
        Args:
            timeout_type: 超时类型，如 'agent_communication', 'llm_api' 等
            
        Returns:
            超时时间（秒）
        """
        timeouts = self.config.get("timeouts", {})
        timeout_value = timeouts.get(timeout_type)
        
        if timeout_value is not None:
            return int(timeout_value)
        
        # 使用默认值
        default_value = self.default_timeouts.get(timeout_type, 300)  # 默认5分钟
        logger.warning(f"⚠️ 超时配置 '{timeout_type}' 未找到，使用默认值: {default_value}秒")
        return default_value
    
    def get_llm_config(self) -> Dict[str, Any]:
        """获取LLM配置"""
        llm_config = self.config.get("llm", {})
        
        # 确保超时时间使用配置的值
        if "timeout" not in llm_config:
            llm_config["timeout"] = self.get_timeout("llm_api")
        
        return llm_config
    
    def get_agent_config(self, agent_name: str = "common_agent") -> Dict[str, Any]:
        """获取Agent配置"""
        return self.config.get(agent_name, {})
    
    def get_system_config(self) -> Dict[str, Any]:
        """获取系统配置"""
        return self.config.get("system", {})
    
    def get_all_timeouts(self) -> Dict[str, int]:
        """获取所有超时配置"""
        timeouts = {}
        for timeout_type in self.default_timeouts.keys():
            timeouts[timeout_type] = self.get_timeout(timeout_type)
        return timeouts
    
    def log_timeout_info(self):
        """记录当前超时配置信息"""
        logger.info("⏱️ 当前超时配置:")
        timeouts = self.get_all_timeouts()
        for timeout_type, timeout_value in timeouts.items():
            logger.info(f"  📋 {timeout_type}: {timeout_value}秒 ({timeout_value/60:.1f}分钟)")

# 全局配置管理器实例
config_manager = ConfigManager()

def get_timeout(timeout_type: str) -> int:
    """便捷函数：获取超时时间"""
    return config_manager.get_timeout(timeout_type)

def get_llm_config() -> Dict[str, Any]:
    """便捷函数：获取LLM配置"""
    return config_manager.get_llm_config()

def get_system_config() -> Dict[str, Any]:
    """便捷函数：获取系统配置"""
    return config_manager.get_system_config() 