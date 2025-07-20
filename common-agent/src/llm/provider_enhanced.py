"""
Enhanced SiliconFlow LLM Provider

Enhanced provider implementation with better error handling, configuration validation,
and connection testing.
"""

from typing import Dict, List, Any, AsyncGenerator, Optional, Tuple
import json
import httpx
import asyncio
import time
from .client import LLMProvider


class EnhancedSiliconFlowProvider(LLMProvider):
    """Enhanced SiliconFlow API provider with better error handling"""
    
    def __init__(self, api_key: str, model: str, base_url: str = "https://api.siliconflow.cn/v1", timeout: int = 60):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url
        self.timeout = timeout
        self.client = httpx.AsyncClient(timeout=timeout)
        self._connection_verified = False
        
    async def verify_connection(self) -> Tuple[bool, str]:
        """Verify connection to LLM service"""
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            # Use a simple test request
            test_payload = {
                "model": self.model,
                "messages": [{"role": "user", "content": "Hello"}],
                "max_tokens": 10
            }
            
            response = await self.client.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=test_payload
            )
            
            if response.status_code == 200:
                self._connection_verified = True
                return True, "Connection successful"
            elif response.status_code == 401:
                return False, "Authentication failed - check API key"
            elif response.status_code == 404:
                return False, "Model not found - check model name"
            else:
                return False, f"HTTP {response.status_code}: {response.text[:200]}"
                
        except httpx.TimeoutException:
            return False, f"Connection timeout after {self.timeout}s"
        except httpx.NetworkError as e:
            return False, f"Network error: {str(e)}"
        except Exception as e:
            return False, f"Unexpected error: {str(e)}"
    
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        **kwargs
    ) -> Dict[str, Any]:
        """Send chat completion request to SiliconFlow with enhanced error handling"""
        
        # Verify connection if not already done
        if not self._connection_verified:
            is_connected, error_msg = await self.verify_connection()
            if not is_connected:
                return {
                    "choices": [
                        {
                            "message": {
                                "content": f"LLM connection failed: {error_msg}"
                            }
                        }
                    ],
                    "error": error_msg
                }
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # Prepare payload with safe defaults
        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": kwargs.get("max_tokens", 4096),
            "temperature": kwargs.get("temperature", 0.7),
            **{k: v for k, v in kwargs.items() if k not in ["max_tokens", "temperature"]}
        }
        
        try:
            start_time = time.time()
            response = await self.client.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload
            )
            
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                response_data = response.json()
                response_data["_response_time"] = response_time
                return response_data
            elif response.status_code == 401:
                return {
                    "choices": [{"message": {"content": "LLM authentication failed - check API key"}}],
                    "error": "authentication_failed"
                }
            elif response.status_code == 429:
                return {
                    "choices": [{"message": {"content": "LLM rate limit exceeded - please try again later"}}],
                    "error": "rate_limit_exceeded"
                }
            elif response.status_code >= 500:
                return {
                    "choices": [{"message": {"content": "LLM service unavailable - server error"}}],
                    "error": "server_error"
                }
            else:
                error_detail = response.text[:300] if response.text else "Unknown error"
                return {
                    "choices": [{"message": {"content": f"LLM request failed: HTTP {response.status_code}"}}],
                    "error": f"http_error_{response.status_code}",
                    "details": error_detail
                }
                
        except httpx.TimeoutException:
            return {
                "choices": [{"message": {"content": f"LLM request timeout after {self.timeout}s"}}],
                "error": "timeout"
            }
        except httpx.NetworkError as e:
            return {
                "choices": [{"message": {"content": f"LLM network error: {str(e)}"}}],
                "error": "network_error"
            }
        except json.JSONDecodeError:
            return {
                "choices": [{"message": {"content": "LLM returned invalid JSON response"}}],
                "error": "invalid_response"
            }
        except Exception as e:
            return {
                "choices": [{"message": {"content": f"LLM unexpected error: {str(e)}"}}],
                "error": "unexpected_error"
            }
    
    async def stream_completion(
        self,
        messages: List[Dict[str, str]],
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """Stream chat completion from SiliconFlow with enhanced error handling"""
        
        # Verify connection if not already done
        if not self._connection_verified:
            is_connected, error_msg = await self.verify_connection()
            if not is_connected:
                yield f"LLM connection failed: {error_msg}"
                return
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": True,
            "max_tokens": kwargs.get("max_tokens", 4096),
            "temperature": kwargs.get("temperature", 0.7),
            **{k: v for k, v in kwargs.items() if k not in ["max_tokens", "temperature", "stream"]}
        }
        
        try:
            async with self.client.stream(
                "POST",
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload
            ) as response:
                
                if response.status_code != 200:
                    yield f"LLM streaming error: HTTP {response.status_code}"
                    return
                
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]  # Remove "data: " prefix
                        if data.strip() == "[DONE]":
                            break
                        
                        try:
                            chunk = json.loads(data)
                            delta = chunk.get("choices", [{}])[0].get("delta", {})
                            content = delta.get("content", "")
                            if content:
                                yield content
                        except json.JSONDecodeError:
                            continue
                            
        except httpx.TimeoutException:
            yield f"LLM streaming timeout after {self.timeout}s"
        except httpx.NetworkError as e:
            yield f"LLM streaming network error: {str(e)}"
        except Exception as e:
            yield f"LLM streaming unexpected error: {str(e)}"
    
    def get_status(self) -> Dict[str, Any]:
        """Get provider status information"""
        return {
            "provider": "SiliconFlow",
            "model": self.model,
            "base_url": self.base_url,
            "timeout": self.timeout,
            "connection_verified": self._connection_verified,
            "api_key_length": len(self.api_key) if self.api_key else 0,
            "api_key_prefix": self.api_key[:10] + "..." if self.api_key else "Not set"
        }
    
    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()


class LLMConfigValidator:
    """Validator for LLM configuration"""
    
    @staticmethod
    def validate_config(config: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate LLM configuration"""
        errors = []
        
        # Required fields
        required_fields = ["api_key", "model", "base_url"]
        for field in required_fields:
            if field not in config or not config[field]:
                errors.append(f"Missing required field: {field}")
        
        # API key format check
        if "api_key" in config:
            api_key = config["api_key"]
            if not api_key.startswith("sk-"):
                errors.append("API key should start with 'sk-'")
            if len(api_key) < 20:
                errors.append("API key seems too short")
        
        # URL format check
        if "base_url" in config:
            base_url = config["base_url"]
            if not base_url.startswith(("http://", "https://")):
                errors.append("Base URL should start with http:// or https://")
        
        # Numeric field validation
        numeric_fields = {
            "max_tokens": (1, 32000),
            "temperature": (0.0, 2.0),
            "timeout": (1, 300)
        }
        
        for field, (min_val, max_val) in numeric_fields.items():
            if field in config:
                try:
                    value = float(config[field])
                    if not (min_val <= value <= max_val):
                        errors.append(f"{field} should be between {min_val} and {max_val}")
                except (TypeError, ValueError):
                    errors.append(f"{field} should be a number")
        
        return len(errors) == 0, errors
    
    @staticmethod
    def suggest_fixes(config: Dict[str, Any]) -> List[str]:
        """Suggest fixes for common configuration issues"""
        suggestions = []
        
        if not config.get("api_key"):
            suggestions.append("Set your SiliconFlow API key in the configuration")
        
        if config.get("model") == "deepseek-ai/DeepSeek-V3":
            suggestions.append("Verify that the DeepSeek-V3 model is available in your SiliconFlow account")
        
        if config.get("timeout", 60) < 30:
            suggestions.append("Consider increasing timeout to at least 30 seconds for complex requests")
        
        return suggestions 