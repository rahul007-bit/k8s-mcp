# Setup & Testing Guide

## Prerequisites

All three services must be running:

### 1. MCP K8s Server (Terminal 1)
```bash
cd /home/amazinrahul/practice/mcp-k8s
uv run k8s_mcp_server.py
```

✅ Expected output:
```
Application startup complete
Found 32 tools
```

### 2. Backend API Server (Terminal 2)
```bash
cd /home/amazinrahul/practice/mcp-k8s/app/backend
uv run run.py
```

✅ Expected output:
```
✓ Connected to MCP server at http://localhost:8000/sse
✓ Found 32 tools
Uvicorn running on http://localhost:8001
```

### 3. Frontend Dev Server (Terminal 3)
```bash
cd /home/amazinrahul/practice/mcp-k8s/app/frontend
bun run dev
```

✅ Expected output:
```
Local:   http://localhost:5173
```

## Architecture

```
┌─────────────────────────────────────────────────────┐
│ Frontend (React + Vite) - localhost:5173            │
│  • WebSocket Proxy: /ws/chat → backend /ws/chat    │
│  • API Proxy: /api/* → backend /api/*              │
└────────┬────────────────────────────────────────────┘
         │ (proxied)
         ↓
┌─────────────────────────────────────────────────────┐
│ Backend API (FastAPI) - localhost:8001              │
│  • GET  /health → Health check                      │
│  • POST /api/chat/message → HTTP fallback           │
│  • WS   /ws/chat → Real-time streaming             │
└────────┬────────────────────────────────────────────┘
         │ (connects to)
         ↓
┌─────────────────────────────────────────────────────┐
│ K8s MCP Server - localhost:8000/sse                 │
│  • 32+ Tools for Kubernetes operations              │
│  • list_pods, list_deployments, apply_yaml, etc.   │
└─────────────────────────────────────────────────────┘
```

## WebSocket Connection Flow

1. **Frontend connects** on page load
   - Browser: `ws://localhost:5173/ws/chat` (proxied)
   - Backend: `ws://localhost:8001/ws/chat` (actual)

2. **User sends message**
   - Event: `{ "message": "...", "conversation_id": "..." }`

3. **Backend processes**
   - Sends real-time events to frontend
   - Event types: `thinking`, `text`, `tool_call_start`, `tool_call_end`, `complete`, `error`

4. **Frontend updates UI**
   - Text streams in real-time
   - Tool results show as they complete
   - No loading placeholders

## Troubleshooting

### ❌ "WebSocket error" in console

**Problem**: Backend not running on port 8001

**Solution**: 
1. Check that backend started: `cd app/backend && uv run run.py`
2. Verify output shows `Uvicorn running on http://localhost:8001`
3. Reload frontend page after backend starts

### ❌ "Cannot run the event loop" error

**Problem**: Event loop conflict in backend

**Solution**: Already fixed! Process using `async def process_message_stream()` and `await call_tool_async()`

### ❌ Tool results showing truncated

**Problem**: Using old ToolCall component

**Solution**: Already fixed! New component shows full output with scrollable code blocks

### ⚠️  "Make sure backend is running on port 8001"

**Check**:
```bash
# Terminal 2 - Backend must be running
curl http://localhost:8001/health
# Should return: {"status":"ok"}
```

## Testing Scenarios

### Test 1: Simple Chat
```
User: "hello"
Expected: Sees model response in real-time
```

### Test 2: Tool Execution  
```
User: "list all pods"
Expected:
- Sees thinking indicator
- Model text streams in
- Tool executes: list_pods
- Result appears in ToolCallHistory
- Tool shows ✅ completed status
```

### Test 3: Multiple Tools
```
User: "show me pods and deployments"
Expected:
- Both tools execute
- Each result appears in history as it completes
```

### Test 4: Multi-line Input
```
User: Type multiple lines (Shift+Enter)
Then: Press Enter to send
Expected: Works correctly
```

## Performance Tips

1. **WebSocket is primary** - Real-time streaming
2. **HTTP is fallback** - Still available at `/api/chat/message`
3. **Conversation context** - Each conversation_id maintains separate history
4. **Tool execution** - Sequential (not parallel)

## Development

### File Structure
```
frontend/
  ├── src/
  │   ├── hooks/useChatWebSocket.js    ← WebSocket handler
  │   ├── pages/ChatPage.jsx           ← Main chat UI
  │   ├── store/chatStore.js           ← Zustand state
  │   └── components/
  │       ├── ChatWindow.jsx           ← Message display
  │       ├── ToolCall.jsx             ← Tool result display
  │       └── ToolCallHistory.jsx      ← Tool execution history
  └── vite.config.js                   ← Proxy config

backend/
  ├── app/
  │   ├── main.py                      ← FastAPI + WebSocket
  │   ├── api/
  │   │   ├── websocket.py             ← WebSocket handler
  │   │   └── routes/chat.py           ← HTTP endpoint
  │   └── services/
  │       ├── chat_service.py          ← Chat logic + streaming
  │       ├── gemini_service.py        ← LLM integration
  │       └── mcp_service.py           ← K8s tool execution
  └── run.py                           ← Entry point
```

### Environment Variables

**Frontend (.env)**:
```
REACT_APP_BACKEND_URL=localhost:8001
```

(Vite proxy handles this automatically during development)

**Backend (.env)**:
```
GOOGLE_API_KEY=your_key_here
MCP_SERVER_URL=http://localhost:8000/sse
```

## Production Deployment

For production, update:

**Vite Config**: Remove proxy, use absolute URLs
**Backend**: Update CORS origins
**WebSocket**: Use `wss://` with proper TLS
