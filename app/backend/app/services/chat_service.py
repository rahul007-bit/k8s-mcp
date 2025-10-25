from typing import Dict, List, Any, Optional
from app.services.mcp_service import MCPService
from app.services.gemini_service import GeminiService
import uuid
from datetime import datetime
import json
import asyncio

class ChatService:
    def __init__(self, mcp_service: MCPService, gemini_service: GeminiService):
        self.mcp_service = mcp_service
        self.gemini_service = gemini_service
        self.conversations: Dict[str, List[Dict]] = {}
    
    def create_conversation(self) -> str:
        """Create a new conversation"""
        conversation_id = str(uuid.uuid4())
        self.conversations[conversation_id] = []
        return conversation_id
    
    async def process_message(self, message: str, conversation_id: Optional[str] = None) -> Dict[str, Any]:
        """Process user message and return response with tool calls"""
        if not conversation_id:
            conversation_id = self.create_conversation()
        
        if conversation_id not in self.conversations:
            self.conversations[conversation_id] = []
        
        history = self.conversations[conversation_id]
        
        # Add user message to history
        history.append({
            'role': 'user',
            'parts': [{'text': message}]
        })
        
        print(f"[DEBUG] Processing message: {message}")
        print(f"[DEBUG] Conversation history length: {len(history)}")
        
        try:
            # Get available tools from MCP server
            tools = self.mcp_service.get_tools_for_gemini()
            print(f"[DEBUG] Got {len(tools)} tools")
            
            # Generate response from Gemini with streaming
            response = self.gemini_service.generate_with_tools(history, tools)
            print(f"[DEBUG] Got response from Gemini")
            
            # Parse response
            response_text = ""
            tool_calls = []
            
            # Process streaming response
            for chunk in response:
                print(f"[DEBUG] Processing chunk: {type(chunk)}")
                
                if hasattr(chunk, 'candidates') and chunk.candidates:
                    for candidate in chunk.candidates:
                        if hasattr(candidate, 'content') and candidate.content:
                            if hasattr(candidate.content, 'parts') and candidate.content.parts:
                                for part in candidate.content.parts:
                                    # Handle text
                                    if hasattr(part, 'text') and part.text:
                                        print(f"[DEBUG] Got text: {part.text[:50]}...")
                                        response_text += part.text
                                    
                                    # Handle function calls
                                    if hasattr(part, 'function_call') and part.function_call:
                                        tool_name = part.function_call.name
                                        tool_args = {}
                                        
                                        if hasattr(part.function_call, 'args') and part.function_call.args:
                                            # Convert args (could be dict or other type)
                                            args = part.function_call.args
                                            if isinstance(args, dict):
                                                tool_args = args
                                            else:
                                                tool_args = dict(args)
                                        
                                        print(f"[DEBUG] Got tool call: {tool_name}")
                                        
                                        # Call the MCP tool asynchronously
                                        try:
                                            result = await self.mcp_service.call_tool_async(tool_name, tool_args)
                                            
                                            tool_calls.append({
                                                'tool_name': tool_name,
                                                'arguments': tool_args,
                                                'result': result,
                                                'status': 'completed'
                                            })
                                        except Exception as e:
                                            print(f"[DEBUG] Tool call failed: {str(e)}")
                                            import traceback
                                            traceback.print_exc()
                                            tool_calls.append({
                                                'tool_name': tool_name,
                                                'arguments': tool_args,
                                                'result': f"Error: {str(e)}",
                                                'status': 'failed'
                                            })
            
            print(f"[DEBUG] Final response text length: {len(response_text)}")
            print(f"[DEBUG] Tool calls: {len(tool_calls)}")
            
            # Add assistant response to history
            if response_text or tool_calls:
                history.append({
                    'role': 'model',
                    'parts': [{'text': response_text if response_text else 'Tool call executed'}]
                })
            
            return {
                'message': response_text,
                'tool_calls': tool_calls,
                'conversation_id': conversation_id
            }
        except Exception as e:
            print(f"[ERROR] Error processing message: {str(e)}")
            import traceback
            traceback.print_exc()
            raise
    
    async def process_message_stream(self, message: str, conversation_id: Optional[str] = None):
        """Process message with real-time streaming of text and tool calls"""
        if not conversation_id:
            conversation_id = self.create_conversation()
        
        if conversation_id not in self.conversations:
            self.conversations[conversation_id] = []
        
        history = self.conversations[conversation_id]
        
        # Add user message to history
        history.append({
            'role': 'user',
            'parts': [{'text': message}]
        })
        
        print(f"[DEBUG] Processing stream message: {message}")
        print(f"[DEBUG] Conversation history length: {len(history)}")
        
        try:
            # Get available tools from MCP server
            tools = self.mcp_service.get_tools_for_gemini()
            print(f"[DEBUG] Got {len(tools)} tools")
            
            # Yield thinking indicator
            yield {
                'type': 'thinking',
                'data': {'message': 'Processing...'}
            }
            
            # Generate response from Gemini with streaming
            response = self.gemini_service.generate_with_tools(history, tools)
            print(f"[DEBUG] Got response from Gemini")
            
            # Parse response
            response_text = ""
            tool_calls = []
            
            # Process streaming response
            for chunk in response:
                print(f"[DEBUG] Processing chunk: {type(chunk)}")
                
                if hasattr(chunk, 'candidates') and chunk.candidates:
                    for candidate in chunk.candidates:
                        if hasattr(candidate, 'content') and candidate.content:
                            if hasattr(candidate.content, 'parts') and candidate.content.parts:
                                for part in candidate.content.parts:
                                    # Handle text
                                    if hasattr(part, 'text') and part.text:
                                        print(f"[DEBUG] Got text: {part.text[:50]}...")
                                        response_text += part.text
                                        
                                        # Stream text in chunks
                                        yield {
                                            'type': 'text',
                                            'data': {
                                                'text': part.text,
                                                'conversation_id': conversation_id
                                            }
                                        }
                                    
                                    # Handle function calls
                                    if hasattr(part, 'function_call') and part.function_call:
                                        tool_name = part.function_call.name
                                        tool_args = {}
                                        
                                        if hasattr(part.function_call, 'args') and part.function_call.args:
                                            # Convert args (could be dict or other type)
                                            args = part.function_call.args
                                            if isinstance(args, dict):
                                                tool_args = args
                                            else:
                                                tool_args = dict(args)
                                        
                                        print(f"[DEBUG] Got tool call: {tool_name}")
                                        
                                        # Stream tool call start
                                        yield {
                                            'type': 'tool_call_start',
                                            'data': {
                                                'tool_name': tool_name,
                                                'arguments': tool_args,
                                                'conversation_id': conversation_id
                                            }
                                        }
                                        
                                        # Call the MCP tool asynchronously
                                        try:
                                            result = await self.mcp_service.call_tool_async(tool_name, tool_args)
                                            
                                            tool_calls.append({
                                                'tool_name': tool_name,
                                                'arguments': tool_args,
                                                'result': result,
                                                'status': 'completed'
                                            })
                                            
                                            # Stream tool call result
                                            yield {
                                                'type': 'tool_call_end',
                                                'data': {
                                                    'tool_name': tool_name,
                                                    'arguments': tool_args,
                                                    'result': result,
                                                    'status': 'completed',
                                                    'conversation_id': conversation_id
                                                }
                                            }
                                        except Exception as e:
                                            print(f"[DEBUG] Tool call failed: {str(e)}")
                                            import traceback
                                            traceback.print_exc()
                                            
                                            tool_calls.append({
                                                'tool_name': tool_name,
                                                'arguments': tool_args,
                                                'result': f"Error: {str(e)}",
                                                'status': 'failed'
                                            })
                                            
                                            # Stream tool call error
                                            yield {
                                                'type': 'tool_call_end',
                                                'data': {
                                                    'tool_name': tool_name,
                                                    'arguments': tool_args,
                                                    'result': f"Error: {str(e)}",
                                                    'status': 'failed',
                                                    'conversation_id': conversation_id
                                                }
                                            }
            
            print(f"[DEBUG] Final response text length: {len(response_text)}")
            print(f"[DEBUG] Tool calls: {len(tool_calls)}")
            
            # Add assistant response to history
            if response_text or tool_calls:
                history.append({
                    'role': 'model',
                    'parts': [{'text': response_text if response_text else 'Tool call executed'}]
                })
            
            # Yield completion event
            yield {
                'type': 'complete',
                'data': {
                    'message': response_text,
                    'tool_calls': tool_calls,
                    'conversation_id': conversation_id
                }
            }
        except Exception as e:
            print(f"[ERROR] Error processing stream: {str(e)}")
            import traceback
            traceback.print_exc()
            
            yield {
                'type': 'error',
                'data': {'error': str(e)}
            }