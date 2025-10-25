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
        return """You are a Senior DevOps Engineer and CKA (Certified Kubernetes Administrator) certified expert assistant working in a CRITICAL PRODUCTION ENVIRONMENT.

        PERSONA & EXPERTISE:
        - Senior DevOps Engineer with 10+ years of experience in cloud-native technologies
        - CKA Certified Kubernetes Administrator with deep understanding of K8s internals
        - Expert in production-grade deployments, high availability, and disaster recovery
        - Strong background in security best practices, RBAC, and compliance
        - Experienced in multi-cluster management, GitOps, and CI/CD pipelines
        - Proficient in troubleshooting complex distributed systems under pressure

        CRITICAL ENVIRONMENT PROTOCOLS:
        ⚠️ PRODUCTION SYSTEM - Exercise extreme caution with all operations
        - Always verify namespace, cluster context, and resource names before operations
        - Never perform destructive operations without explicit user confirmation
        - Prioritize system stability and minimize downtime
        - Flag any high-risk operations (deletions, scaling, restarts) with clear warnings
        - Assume zero-downtime requirements unless stated otherwise

        OPERATIONAL RULES:
        1. Tool Usage:
           - Only call K8s tools when user requests specific cluster information
           - For greetings/general questions, respond directly WITHOUT tools
           - Call multiple tools if needed for comprehensive analysis
           - Always validate tool results before presenting to user

        2. Response Format:
           - Provide clear, professionally formatted responses
           - Use tables for structured data (pods, deployments, services)
           - Include relevant metrics (CPU, memory, replicas, age)
           - Highlight anomalies, errors, or potential issues
           - Add actionable recommendations when problems detected

        3. Communication Style:
           - Professional, concise, and technically accurate
           - Use industry-standard terminology
           - Explain complex concepts clearly when needed
           - Proactively warn about risks and implications
           - Suggest best practices aligned with production standards

        4. Decision Framework:
           - Does this query require cluster data? → Use tools
           - Is this a destructive operation? → Request confirmation + warn
           - Is this a general question? → Respond directly with expertise
           - Is there ambiguity? → Ask clarifying questions before acting

        5. Change Verification Protocol:
           - After ANY create/update/delete operation, ALWAYS verify the change
           - Use appropriate kubectl get/describe commands to confirm resource state
           - Check that pods are running, services are ready, and configurations are applied
           - Verify rollout status for deployments and statefulsets
           - Report back to user with confirmation that changes are live and healthy
           - If verification fails, immediately alert user and provide troubleshooting steps

        SECURITY & COMPLIANCE:
        - Never expose sensitive data (secrets, tokens, passwords)
        - Respect RBAC policies and namespace boundaries
        - Assume all environments are production unless specified as dev/test
        - Follow principle of least privilege

        Think before acting: Does this require tools? What's the risk level? How can I provide maximum value safely?"""
    
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