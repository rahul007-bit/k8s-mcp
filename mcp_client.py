"""
MCP Client with Google Gemini - STREAMING VERSION (New SDK)
"""

import asyncio
import json
import os
from typing import List, Dict, Any
from fastmcp import Client
from google import genai


GENI_API_KEY = os.getenv("GOOGLE_API_KEY")

if not GENI_API_KEY:
    raise ValueError("GOOGLE_API_KEY environment variable not set")

class GeminiMCPClient:
    
    def __init__(self, 
                 mcp_server_url: str = "http://localhost:8000/sse",
                 model: str = "gemini-2.5-flash",
                 api_key: str = ""):
        self.mcp_server_url = mcp_server_url
        self.model_name = model
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        print(self.api_key)
        
        self.client = genai.Client(api_key=self.api_key)
        
        self.mcp_client = None
        self.available_tools = []
        self.conversation_history = []

    def _clean_schema_for_gemini(self, schema: Dict) -> Dict:
        """Remove Gemini-incompatible fields from schema."""
        if not isinstance(schema, dict):
            return schema
        
        cleaned = {}
        
        for key, value in schema.items():
            # Skip incompatible fields
            if key in ['additional_properties', 'additionalProperties', 'anyOf', 'any_of', 'allOf', 'all_of', 'oneOf', 'one_of']:
                continue
            
            # Recursively clean nested objects
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

    async def connect(self):
        """Connect to the MCP server and discover available tools."""
        self.mcp_client = Client(self.mcp_server_url)
        await self.mcp_client.__aenter__()
        
        tools_response = await self.mcp_client.list_tools()
        self.available_tools = tools_response
        
        print(f"✓ Connected to {self.mcp_server_url}")
        print(f"✓ Found {len(self.available_tools)} tools:")
        for tool in self.available_tools:
            print(f"  • {tool.name}")
        print()
        
    async def disconnect(self):
        if self.mcp_client:
            await self.mcp_client.__aexit__(None, None, None)
    
    def _format_tools_for_gemini(self) -> List[Dict]:
        """Convert MCP tools to Gemini format."""
        gemini_tools = []
        
        for tool in self.available_tools:
            properties = {}
            required = []
            
            if hasattr(tool, 'inputSchema') and tool.inputSchema:
                schema = tool.inputSchema
                raw_properties = schema.get('properties', {})
                required = schema.get('required', [])
                
                # Clean each property for Gemini compatibility
                for prop_name, prop_schema in raw_properties.items():
                    properties[prop_name] = self._clean_schema_for_gemini(prop_schema)
            
            gemini_tools.append({
                'function_declarations': [{
                    'name': tool.name,
                    'description': tool.description or f"Execute {tool.name}",
                    'parameters': {
                        'type': 'OBJECT',
                        'properties': properties,
                        'required': required
                    }
                }]
            })
        
        return gemini_tools
    
    def _create_system_instruction(self) -> str:
        """Create system instruction for the model."""
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
    
    async def _call_mcp_tool(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """Call an MCP tool."""
        try:
            result = await self.mcp_client.call_tool(tool_name, arguments)
            
            if hasattr(result, 'content') and result.content:
                if isinstance(result.content, list):
                    return '\n'.join([
                        item.text if hasattr(item, 'text') else str(item) 
                        for item in result.content
                    ])
                return str(result.content)
            
            return str(result)
        except Exception as e:
            return f"Error: {str(e)}"
    
    async def chat_stream(self, user_message: str, max_iterations: int = 10):
        """Process user message with streaming output."""
        # Add user message to history
        self.conversation_history.append({
            'role': 'user',
            'parts': [{'text': user_message}]
        })
        
        tools = self._format_tools_for_gemini()
        iteration = 0
        
        while iteration < max_iterations:
            iteration += 1
            
            # Create config
            config = {
                'system_instruction': self._create_system_instruction(),
                'tools': tools if tools else None,
            }
            
            # Generate content with streaming
            response = self.client.models.generate_content_stream(
                model=self.model_name,
                contents=self.conversation_history,
                config=config
            )
            
            current_text = ""
            function_calls = []
            
            # Process streaming chunks
            for chunk in response:
                # Check for function calls and text in parts
                if hasattr(chunk, 'candidates') and chunk.candidates:
                    for candidate in chunk.candidates:
                        if hasattr(candidate, 'content') and candidate.content:
                            if hasattr(candidate.content, 'parts') and candidate.content.parts:
                                for part in candidate.content.parts:
                                    # Handle text parts
                                    if hasattr(part, 'text') and part.text:
                                        current_text += part.text
                                        print(part.text, end='', flush=True)
                                    
                                    # Handle function calls
                                    if hasattr(part, 'function_call') and part.function_call:
                                        function_calls.append(part.function_call)            
            # If no function calls, we're done
            if not function_calls:
                if current_text:
                    self.conversation_history.append({
                        'role': 'model',
                        'parts': [{'text': current_text}]
                    })
                break
            
            # Execute function calls
            print(f"\n\n[Iteration {iteration}] Calling {len(function_calls)} tool(s)...")
            
            # Add assistant message with function calls
            self.conversation_history.append({
                'role': 'model',
                'parts': [{'function_call': fc} for fc in function_calls]
            })
            
            # Execute each function and collect responses
            function_response_parts = []
            for fc in function_calls:
                tool_name = fc.name
                tool_args = dict(fc.args) if hasattr(fc, 'args') else {}
                
                print(f"  → {tool_name}({json.dumps(tool_args)})")
                
                # Call the MCP tool
                tool_result = await self._call_mcp_tool(tool_name, tool_args)
                print(f"    ✓ Got result")
                
                # Add function response
                function_response_parts.append({
                    'function_response': {
                        'name': tool_name,
                        'response': {'result': tool_result}
                    }
                })
            
            # Add function responses to history
            self.conversation_history.append({
                'role': 'user',
                'parts': function_response_parts
            })
            
            print()
        
        if iteration >= max_iterations:
            print("\n\n(Max iterations reached)")
    
    async def run_interactive(self):
        """Interactive chat loop with streaming."""
        print("="*60)
        print("  MCP Client with Google Gemini - STREAMING MODE")
        print("="*60)
        print(f"  Model: {self.model_name}")
        print("  Commands: clear, tools, exit")
        print("="*60)
        print()
        
        while True:
            try:
                user_input = input("\nYou: ").strip()
                
                if not user_input:
                    continue
                
                if user_input.lower() in ['exit', 'quit']:
                    break
                
                if user_input.lower() == 'clear':
                    self.conversation_history = []
                    print("✓ History cleared")
                    continue
                
                if user_input.lower() == 'tools':
                    for tool in self.available_tools:
                        print(f"  • {tool.name}")
                    continue
                
                print("\nA: ", end='', flush=True)
                await self.chat_stream(user_input)
                print()
                
            except KeyboardInterrupt:
                print("\n\nGoodbye!")
                break
            except Exception as e:
                print(f"\nError: {str(e)}")
                import traceback
                traceback.print_exc()


async def main():
    client = GeminiMCPClient(
        mcp_server_url="http://localhost:8000/sse",
        model="gemini-2.5-flash",
        api_key= GENI_API_KEY
    )
    
    try:
        await client.connect()
        await client.run_interactive()
    finally:
        await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
