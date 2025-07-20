"""
Enhanced JSON Parser for LLM Responses

Handles various formats of LLM responses including Markdown code blocks,
plain JSON, and mixed content.
"""

import json
import re
from typing import Dict, Any, Optional, Tuple


class LLMResponseParser:
    """Enhanced parser for LLM responses with JSON content"""
    
    @staticmethod
    def extract_json_from_markdown(text: str) -> Optional[str]:
        """Extract JSON from Markdown code blocks"""
        # Pattern for JSON code blocks
        patterns = [
            r'```json\s*\n(.*?)\n```',  # ```json ... ```
            r'```\s*\n(.*?)\n```',      # ``` ... ``` (generic code block)
            r'`(.*?)`',                 # `...` (inline code)
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.DOTALL | re.IGNORECASE)
            for match in matches:
                try:
                    # Try to parse as JSON
                    json.loads(match.strip())
                    return match.strip()
                except json.JSONDecodeError:
                    continue
        
        return None
    
    @staticmethod
    def extract_json_from_text(text: str) -> Optional[str]:
        """Extract JSON from plain text using various methods"""
        # Method 1: Try to find JSON object patterns
        json_patterns = [
            r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}',  # Simple nested JSON
            r'\{.*?\}',                          # Basic JSON object
        ]
        
        for pattern in json_patterns:
            matches = re.findall(pattern, text, re.DOTALL)
            for match in matches:
                try:
                    json.loads(match.strip())
                    return match.strip()
                except json.JSONDecodeError:
                    continue
        
        # Method 2: Try to extract from start/end markers
        start_markers = ['{', '[']
        end_markers = ['}', ']']
        
        for start_char, end_char in zip(start_markers, end_markers):
            start_idx = text.find(start_char)
            if start_idx != -1:
                # Find matching closing bracket
                bracket_count = 0
                for i, char in enumerate(text[start_idx:], start_idx):
                    if char == start_char:
                        bracket_count += 1
                    elif char == end_char:
                        bracket_count -= 1
                        if bracket_count == 0:
                            candidate = text[start_idx:i+1]
                            try:
                                json.loads(candidate)
                                return candidate
                            except json.JSONDecodeError:
                                break
        
        return None
    
    @staticmethod
    def parse_llm_response(response: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Parse LLM response with multiple fallback strategies
        
        Returns:
            (success: bool, parsed_data: dict)
        """
        if not response or not response.strip():
            return False, {"error": "Empty response"}
        
        response = response.strip()
        
        # Strategy 1: Direct JSON parsing
        try:
            data = json.loads(response)
            return True, data
        except json.JSONDecodeError:
            pass
        
        # Strategy 2: Extract from Markdown code blocks
        json_from_markdown = LLMResponseParser.extract_json_from_markdown(response)
        if json_from_markdown:
            try:
                data = json.loads(json_from_markdown)
                return True, data
            except json.JSONDecodeError:
                pass
        
        # Strategy 3: Extract from plain text
        json_from_text = LLMResponseParser.extract_json_from_text(response)
        if json_from_text:
            try:
                data = json.loads(json_from_text)
                return True, data
            except json.JSONDecodeError:
                pass
        
        # Strategy 4: Try to parse as YAML (sometimes LLMs return YAML-like structure)
        try:
            import yaml
            data = yaml.safe_load(response)
            if isinstance(data, dict):
                return True, data
        except:
            pass
        
        # Strategy 5: Create structured response from text
        # Look for key-value patterns
        lines = response.split('\n')
        extracted_data = {}
        
        for line in lines:
            line = line.strip()
            # Pattern: "key: value" or "key = value"
            kv_match = re.match(r'^([^:=]+)[:=]\s*(.+)$', line)
            if kv_match:
                key = kv_match.group(1).strip().lower().replace(' ', '_')
                value = kv_match.group(2).strip()
                
                # Try to parse value as JSON
                try:
                    value = json.loads(value)
                except:
                    pass
                
                extracted_data[key] = value
        
        if extracted_data:
            return True, extracted_data
        
        # Fallback: Return the response as a direct message
        return False, {
            "approach": "direct_response",
            "reasoning": "Could not parse as structured data",
            "response": response,
            "parse_attempted": True
        }
    
    @staticmethod
    def validate_decision_structure(data: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
        """
        Validate and normalize decision structure for the multi-agent system
        
        Expected structure:
        {
            "approach": "agent_coordination" | "direct_response" | "mcp_tools",
            "reasoning": "explanation",
            "steps": [...] (optional),
            "response": "direct response" (for direct_response approach)
        }
        """
        if not isinstance(data, dict):
            return False, {"error": "Data is not a dictionary"}
        
        # Check for direct response
        if "response" in data and not data.get("approach"):
            return True, {
                "approach": "direct_response",
                "reasoning": "Direct response provided",
                "response": data["response"]
            }
        
        # Ensure approach field exists
        if "approach" not in data:
            # Infer approach based on content
            if "steps" in data or any(key in data for key in ["agents", "tasks", "workflow"]):
                data["approach"] = "agent_coordination"
            elif any(key in data for key in ["tools", "mcp", "figma"]):
                data["approach"] = "mcp_tools"
            else:
                data["approach"] = "direct_response"
        
        # Ensure reasoning exists
        if "reasoning" not in data:
            data["reasoning"] = "Decision made based on user request"
        
        # Validate approach values
        valid_approaches = ["agent_coordination", "direct_response", "mcp_tools"]
        if data.get("approach") not in valid_approaches:
            data["approach"] = "direct_response"
            data["reasoning"] = f"Invalid approach specified, defaulting to direct_response"
        
        return True, data


def parse_decision_response(response: str) -> Dict[str, Any]:
    """
    Main function to parse LLM decision response
    
    This is the primary function that should be used by the CommonAgent
    """
    success, data = LLMResponseParser.parse_llm_response(response)
    
    if success:
        # Validate and normalize the structure
        valid, normalized_data = LLMResponseParser.validate_decision_structure(data)
        if valid:
            return normalized_data
        else:
            # If validation fails, treat as direct response
            return {
                "approach": "direct_response",
                "reasoning": "Response structure validation failed",
                "response": response,
                "validation_error": normalized_data.get("error", "Unknown validation error")
            }
    else:
        # Return the fallback response from the parser
        return data 