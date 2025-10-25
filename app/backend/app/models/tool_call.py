from pydantic import BaseModel
from typing import Dict, Any, Optional

class ToolDefinition(BaseModel):
    name: str
    description: str
    inputSchema: Dict[str, Any]

class ToolCallEvent(BaseModel):
    event_type: str  # "tool_call_start", "tool_call_result", "tool_call_error"
    tool_name: str
    arguments: Optional[Dict[str, Any]] = None
    result: Optional[str] = None
    error: Optional[str] = None
    timestamp: str