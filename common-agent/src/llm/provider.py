"""
SiliconFlow LLM Provider

Provider implementation for SiliconFlow's API service.
"""

from typing import Dict, List, Any, AsyncGenerator
import json
import httpx
from .client import LLMProvider


class SiliconFlowProvider(LLMProvider):
    """SiliconFlow API provider"""
    
    def __init__(self, api_key: str, model: str, base_url: str = "https://api.siliconflow.cn/v1"):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url
        self.client = httpx.AsyncClient()
    
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        **kwargs
    ) -> Dict[str, Any]:
        """Send chat completion request to SiliconFlow"""
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": messages,
            **kwargs
        }
        
        try:
            response = await self.client.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            return response.json()
            
        except Exception as e:
            # Return error in OpenAI-compatible format
            return {
                "choices": [
                    {
                        "message": {
                            "content": f"Error communicating with LLM: {str(e)}"
                        }
                    }
                ]
            }
    
    async def stream_completion(
        self,
        messages: List[Dict[str, str]],
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """Stream chat completion from SiliconFlow"""
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": True,
            **kwargs
        }
        
        try:
            async with self.client.stream(
                "POST",
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload
            ) as response:
                response.raise_for_status()
                
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
                            
        except Exception as e:
            yield f"Error streaming from LLM: {str(e)}"
    
    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose() 