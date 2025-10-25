# Testing WebSocket Chat Implementation

## Setup

### 1. Start MCP Server (Terminal 1)
```bash
cd /home/amazinrahul/practice/mcp-k8s
uv run k8s_mcp_server.py
```
Expected output: `Application startup complete` and `Found 32 tools`

### 2. Start Backend (Terminal 2)
```bash
cd /home/amazinrahul/practice/mcp-k8s/app/backend
uv run run.py
```
Expected output: 
```
✓ Connected to MCP server at http://localhost:8000/sse
✓ Found 32 tools
Uvicorn running on http://localhost:8001
```

### 3. Start Frontend (Terminal 3)
```bash
cd /home/amazinrahul/practice/mcp-k8s/app/frontend
bun run dev
```
Expected output: `Local: http://localhost:5173`

## Test Scenarios

### Test 1: Real-time Text Streaming
**Query:** `hello, what can you do?`

**Expected behavior:**
- See text appear in chat window as it streams
- No placeholder messages
- Smooth animation as text arrives

### Test 2: Tool Execution
**Query:** `list all pods in the cluster`

**Expected behavior:**
1. See "Processing..." thinking indicator
2. Model text streams in real-time
3. Tool call starts - see `tool_call_start` event
4. Tool executes - pod list appears in ToolCallHistory
5. Response completes - see final message

### Test 3: Multiple Tool Calls
**Query:** `show me deployments and pods`

**Expected behavior:**
- Multiple tool calls execute in sequence
- Each tool shows in ToolCallHistory as it completes
- Real-time updates without waiting

### Test 4: Error Handling
**Query:** `apply invalid yaml config`

**Expected behavior:**
- Error appears in real-time
- Tool marked as `failed` status
- Error message displayed to user

## Debugging

### Check WebSocket Connection
Open browser DevTools → Network → WS tab
- Should see `/ws/chat` connection in `101 Switching Protocols`
- Messages should appear as they're sent/received

### Check Backend Logs
Look for `[DEBUG]` logs showing:
```
[DEBUG] Processing stream message: ...
[DEBUG] Got text: ...
[DEBUG] Got tool call: ...
[DEBUG] Tool result type: ...
```

### Check Frontend Console
Should see:
```
WebSocket connected
[WS] Received thinking: ...
[WS] Received text: ...
[WS] Received tool_call_start: ...
[WS] Received tool_call_end: ...
[WS] Received complete: ...
```

## Performance Tips

1. **Multi-line input**: Use Shift+Enter for new lines, Enter to send
2. **Code blocks**: Wrap k8s YAML with triple backticks for formatting
3. **Conversation context**: Each conversation_id maintains separate history
4. **Tool results**: Check ToolCallHistory sidebar for full output

## Known Behaviors

- WebSocket reconnects automatically if connection drops
- Tool calls execute sequentially (not parallel)
- Frontend stores conversation history in Zustand store
- Browser DevTools can inspect all WebSocket messages in real-time
