"""
MCP Client with Together AI - STREAMING VERSION (FIXED)
"""

import asyncio
import json
import os
from typing import List, Dict, Any
from fastmcp import Client
from together import Together


class TogetherMCPClient:
    
    def __init__(self, 
                 mcp_server_url: str = "http://localhost:8000/sse",
                 model: str = "meta-llama/Llama-3.3-70B-Instruct-Turbo-Free",
                 api_key: str = None):
        self.mcp_server_url = mcp_server_url
        self.model = model
        self.api_key = api_key or os.getenv("TOGETHER_API_KEY")
        self.together_client = Together(api_key=self.api_key)
        self.mcp_client = None
        self.available_tools = []
        self.conversation_history = []
        
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
    
    def _format_tools_for_together(self) -> List[Dict[str, Any]]:
        """Convert MCP tools to Together AI format."""
        together_tools = []
        
        for tool in self.available_tools:
            properties = {}
            required = []
            
            if hasattr(tool, 'inputSchema') and tool.inputSchema:
                schema = tool.inputSchema
                properties = schema.get('properties', {})
                required = schema.get('required', [])
            
            together_tools.append({
                'type': 'function',
                'function': {
                    'name': tool.name,
                    'description': tool.description or f"Execute {tool.name}",
                    'parameters': {
                        'type': 'object',
                        'properties': properties,
                        'required': required
                    }
                }
            })
        
        return together_tools
    
    def _create_system_prompt(self) -> str:
        """Create system prompt for the model."""
        return """You are a Kubernetes assistant with access to tools.

RULES:
1. Only call tools when the user asks for K8s information
2. For greetings/general questions, respond directly WITHOUT tools
3. You can call multiple tools if needed
4. After tool results, provide a clear, formatted response

Think: Does this query need tools? If no, just respond naturally."""
    
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
    
    async def chat_stream(self, user_message: str, max_iterations: int = 5):
        """Process user message with streaming output."""
        self.conversation_history.append({
            'role': 'user',
            'content': user_message
        })
        
        messages = [
            {'role': 'system', 'content': self._create_system_prompt()},
            *self.conversation_history
        ]
        
        tools = self._format_tools_for_together()
        iteration = 0
        
        while iteration < max_iterations:
            iteration += 1
            
            # Stream the response from Together AI
            stream = self.together_client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=tools,
                stream=True,
            )
            
            current_content = ""
            tool_calls_list = []
            tool_call_buffer = {}
            
            # Process stream chunks
            for chunk in stream:
                if not chunk.choices:
                    continue
                
                delta = chunk.choices[0].delta
                
                # Handle content streaming
                if hasattr(delta, 'content') and delta.content:
                    content = delta.content
                    current_content += content
                    print(content, end='', flush=True)
                
                # Handle tool calls (delta format)
                if hasattr(delta, 'tool_calls') and delta.tool_calls:
                    for tc_delta in delta.tool_calls:
                        # Get index - handle both object and dict
                        if isinstance(tc_delta, dict):
                            idx = tc_delta.get('index', 0)
                            tc_id = tc_delta.get('id')
                            tc_function = tc_delta.get('function', {})
                        else:
                            idx = getattr(tc_delta, 'index', 0)
                            tc_id = getattr(tc_delta, 'id', None)
                            tc_function = getattr(tc_delta, 'function', None)
                        
                        # Initialize buffer for this index
                        if idx not in tool_call_buffer:
                            tool_call_buffer[idx] = {
                                'id': tc_id or f"call_{idx}",
                                'type': 'function',
                                'function': {
                                    'name': '',
                                    'arguments': ''
                                }
                            }
                        
                        # Update ID if present
                        if tc_id:
                            tool_call_buffer[idx]['id'] = tc_id
                        
                        # Update function name and arguments
                        if tc_function:
                            if isinstance(tc_function, dict):
                                if 'name' in tc_function and tc_function['name']:
                                    tool_call_buffer[idx]['function']['name'] = tc_function['name']
                                if 'arguments' in tc_function and tc_function['arguments']:
                                    tool_call_buffer[idx]['function']['arguments'] += tc_function['arguments']
                            else:
                                if hasattr(tc_function, 'name') and tc_function.name:
                                    tool_call_buffer[idx]['function']['name'] = tc_function.name
                                if hasattr(tc_function, 'arguments') and tc_function.arguments:
                                    tool_call_buffer[idx]['function']['arguments'] += tc_function.arguments
            
            # Convert tool call buffer to list
            if tool_call_buffer:
                tool_calls_list = [tool_call_buffer[i] for i in sorted(tool_call_buffer.keys())]
            
            # Check if there were tool calls
            if tool_calls_list:
                print(f"\n\n[Iteration {iteration}] Calling {len(tool_calls_list)} tool(s)...")
                
                # Add assistant message with tool calls
                messages.append({
                    'role': 'assistant',
                    'content': current_content or None,
                    'tool_calls': tool_calls_list
                })
                
                for tool_call in tool_calls_list:
                    tool_name = tool_call['function']['name']
                    tool_args_str = tool_call['function']['arguments']
                    
                    # Parse arguments
                    try:
                        tool_args = json.loads(tool_args_str) if isinstance(tool_args_str, str) else tool_args_str
                    except json.JSONDecodeError:
                        tool_args = {}
                    
                    print(f"  → {tool_name}({json.dumps(tool_args)})")
                    
                    tool_result = await self._call_mcp_tool(tool_name, tool_args)
                    print(f"    ✓ Got result")
                    
                    # Add tool result message
                    messages.append({
                        'role': 'tool',
                        'tool_call_id': tool_call['id'],
                        'name': tool_name,
                        'content': tool_result,
                    })
                
                print()
                continue
            
            # No tool calls - final response
            if current_content:
                self.conversation_history.append({
                    'role': 'assistant',
                    'content': current_content
                })
            
            break
        
        if iteration >= max_iterations:
            print("\n\n(Max iterations reached)")
    
    async def run_interactive(self):
        """Interactive chat loop with streaming."""
        print("="*60)
        print("  MCP Client with Together AI - STREAMING MODE")
        print("="*60)
        print(f"  Model: {self.model}")
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
    client = TogetherMCPClient(
        mcp_server_url="http://localhost:8000/sse",
        model="meta-llama/Llama-3.3-70B-Instruct-Turbo-Free",
    )
    
    try:
        await client.connect()
        await client.run_interactive()
    finally:
        await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
