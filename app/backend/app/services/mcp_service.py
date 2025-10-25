import asyncio
import json
from typing import Dict, Any, List, Optional
from fastmcp import Client

class MCPService:
    def __init__(self, mcp_server_url: str):
        self.mcp_server_url = mcp_server_url
        self.available_tools = []
        self.mcp_client = None
    
    async def connect(self):
        """Connect to MCP server and fetch available tools"""
        try:
            # Connect to the MCP server using SSE transport
            self.mcp_client = Client(self.mcp_server_url)
            await self.mcp_client.__aenter__()
            
            # Fetch all available tools
            tools_response = await self.mcp_client.list_tools()
            
            # Convert tool objects to dictionaries
            for tool in tools_response:
                tool_dict = {
                    'name': tool.name,
                    'description': tool.description or f"Execute {tool.name}",
                    'inputSchema': {}
                }
                
                if hasattr(tool, 'inputSchema') and tool.inputSchema:
                    schema = tool.inputSchema
                    if isinstance(schema, str):
                        schema = json.loads(schema)
                    tool_dict['inputSchema'] = schema
                
                self.available_tools.append(tool_dict)
            
            print(f"✓ Connected to MCP server at {self.mcp_server_url}")
            print(f"✓ Found {len(self.available_tools)} tools")
        except Exception as e:
            print(f"Error connecting to MCP: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    async def disconnect(self):
        """Disconnect from MCP server"""
        if self.mcp_client:
            try:
                await self.mcp_client.__aexit__(None, None, None)
            except Exception as e:
                print(f"Error disconnecting: {e}")
    
    async def call_tool_async(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """Call a tool via MCP (async)"""
        try:
            if not self.mcp_client:
                return "Error: MCP client not connected"
            
            print(f"[DEBUG] Calling tool {tool_name} with args: {arguments}")
            result = await self.mcp_client.call_tool(tool_name, arguments)
            print(f"[DEBUG] Tool result type: {type(result)}")
            
            if hasattr(result, 'content') and result.content:
                if isinstance(result.content, list):
                    return '\n'.join([
                        item.text if hasattr(item, 'text') else str(item)
                        for item in result.content
                    ])
                return str(result.content)
            
            return str(result)
        except Exception as e:
            print(f"[DEBUG] Tool call exception: {str(e)}")
            import traceback
            traceback.print_exc()
            return f"Error calling tool: {str(e)}"
    
    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """Call a tool via MCP (synchronous wrapper - DEPRECATED, use call_tool_async instead)"""
        try:
            # Run async call in new event loop
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(self.call_tool_async(tool_name, arguments))
            loop.close()
            return result
        except Exception as e:
            return f"Error: {str(e)}"
    
    def get_tools_for_gemini(self) -> List[Dict]:
        """Format tools for Gemini API"""
        return self.available_tools