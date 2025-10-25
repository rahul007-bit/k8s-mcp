from pydantic import BaseModel
from typing import List, Optional, Dict, Any

class Message(BaseModel):
    role: str  # "user" or "assistant"
    content: str
    timestamp: Optional[str] = None

class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None

class ToolCall(BaseModel):
    tool_name: str
    arguments: Dict[str, Any]
    result: Optional[str] = None
    status: str = "pending"  # pending, executing, completed, failed

class ChatResponse(BaseModel):
    message: str
    tool_calls: List[ToolCall] = []
    conversation_id: str