import json
import asyncio
from fastapi import WebSocket, WebSocketDisconnect
from app.services.chat_service import ChatService

async def handle_chat_stream(websocket: WebSocket, chat_service: ChatService):
    """
    Handle WebSocket connection for real-time chat streaming.
    
    Expected message format:
    {
        "message": "user message",
        "conversation_id": "optional-uuid" or null
    }
    
    Sends real-time updates:
    {
        "type": "thinking" | "text" | "tool_call_start" | "tool_call_end" | "error",
        "data": {...}
    }
    """
    await websocket.accept()
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            request_data = json.loads(data)
            
            message = request_data.get('message', '')
            conversation_id = request_data.get('conversation_id')
            
            if not message:
                await websocket.send_json({
                    "type": "error",
                    "data": {"error": "Message is required"}
                })
                continue
            
            try:
                # Process message with streaming callbacks
                async for event in chat_service.process_message_stream(message, conversation_id):
                    await websocket.send_json(event)
                    
            except Exception as e:
                print(f"Error processing message: {str(e)}")
                import traceback
                traceback.print_exc()
                await websocket.send_json({
                    "type": "error",
                    "data": {"error": str(e)}
                })
                
    except WebSocketDisconnect:
        print("WebSocket disconnected")
    except Exception as e:
        print(f"WebSocket error: {str(e)}")
        import traceback
        traceback.print_exc()
        try:
            await websocket.close(code=1000)
        except:
            pass
