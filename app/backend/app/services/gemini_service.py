import os
import json
from google import genai
from typing import List, Dict, Any, Optional
from app.config import config

class GeminiService:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or config.GOOGLE_API_KEY
        self.client = genai.Client(api_key=self.api_key)
        self.model_name = config.GEMINI_MODEL
    
    def _clean_schema_for_gemini(self, schema: Dict) -> Dict:
        """Remove Gemini-incompatible fields from schema"""
        if not isinstance(schema, dict):
            return schema
        
        cleaned = {}
        skip_keys = {'additional_properties', 'additionalProperties', 'anyOf', 
                     'any_of', 'allOf', 'all_of', 'oneOf', 'one_of'}
        
        for key, value in schema.items():
            if key in skip_keys:
                continue
            
            if isinstance(value, dict):
                cleaned[key] = self._clean_schema_for_gemini(value)
            elif isinstance(value, list):
                cleaned[key] = [
                    self._clean_schema_for_gemini(item) if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                cleaned[key] = value
        
        return cleaned
    
    def _format_tools_for_gemini(self, tools: List[Dict]) -> List[Dict]:
        """Convert tools to Gemini format (matching mcp_client.py)"""
        gemini_tools = []
        
        for tool in tools:
            if isinstance(tool, dict):
                properties = {}
                required = []
                
                if 'inputSchema' in tool:
                    schema = tool['inputSchema']
                    raw_properties = schema.get('properties', {})
                    required = schema.get('required', [])
                    
                    # Clean each property for Gemini compatibility
                    for prop_name, prop_schema in raw_properties.items():
                        properties[prop_name] = self._clean_schema_for_gemini(prop_schema)
                
                gemini_tools.append({
                    'function_declarations': [{
                        'name': tool.get('name', 'unknown'),
                        'description': tool.get('description', 'A tool'),
                        'parameters': {
                            'type': 'OBJECT',
                            'properties': properties,
                            'required': required
                        }
                    }]
                })
        
        return gemini_tools
    
    def _create_system_instruction(self) -> str:
        """Create system instruction for the model"""
        return """You are a Kubernetes assistant with access to tools.

RULES:
1. Only call tools when the user asks for K8s information (pods, deployments, services, etc.)
2. For greetings/general questions, respond directly WITHOUT tools
3. You can call multiple tools if needed
4. After tool results, provide a clear, formatted response
5. Format pod/deployment tables nicely for readability

Think: Does this query need tools? If no, just respond naturally."""
    
    def generate_with_tools(self, 
                          conversation_history: List[Dict],
                          tools: List[Dict]):
        """Generate response with tool support"""
        try:
            # Format tools for Gemini
            gemini_tools = self._format_tools_for_gemini(tools)
            
            # Create config (using the correct parameter name)
            config_dict = {
                'system_instruction': self._create_system_instruction(),
            }
            
            if gemini_tools:
                config_dict['tools'] = gemini_tools
            
            # Generate response with streaming
            response = self.client.models.generate_content_stream(
                model=self.model_name,
                contents=conversation_history,
                config=config_dict
            )
            
            return response
        except Exception as e:
            print(f"Error in generate_with_tools: {e}")
            import traceback
            traceback.print_exc()
            raise