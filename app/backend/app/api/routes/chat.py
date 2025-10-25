from fastapi import APIRouter, HTTPException
from app.models.chat import ChatRequest, ChatResponse
from app.services.chat_service import ChatService
import json

router = APIRouter(prefix="/api/chat", tags=["chat"])

# Global chat service (we'll inject this properly later)
chat_service: ChatService = None

@router.post("/message")
async def send_message(request: ChatRequest):
    """Send a message and get response"""
    if not chat_service:
        raise HTTPException(status_code=500, detail="Chat service not initialized")
    
    try:
        conversation_id = request.conversation_id
        message = request.message
        
        # Process message through chat service (now async)
        response_text = ""
        tool_calls = []
        
        response_obj = await chat_service.process_message(message, conversation_id)
        
        if response_obj:
            response_text = response_obj.get('message', '')
            tool_calls = response_obj.get('tool_calls', [])
        
        return {
            'message': response_text,
            'tool_calls': tool_calls,
            'conversation_id': conversation_id
        }
    except Exception as e:
        print(f"Error in send_message: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error processing message: {str(e)}")