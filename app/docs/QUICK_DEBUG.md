# Quick Debugging - Tool Calls in Messages

## What to Do Right Now

### 1. Reload Frontend
```
http://localhost:5173 (refresh page)
```

### 2. Open Browser DevTools
- Windows/Linux: Press F12
- Mac: Press Cmd + Option + I
- Click "Console" tab

### 3. Send a Test Message
```
Type: "list all pods"
Press: Enter
```

### 4. Watch Console Logs
You should see logs like:
```
[WS] thinking
[WS] text
[Store] New message: role=assistant, messageId=abc-123
[Store] currentMessageId set to: abc-123
[WS] tool_call_start
[Store] addToolCall: list_pods, currentMessageId: abc-123
[Store] Linking tool call to message: abc-123
[Store] Found matching message, adding tool call
[Message] Found 1 tool calls in message
[WS] tool_call_end
[WS] complete
```

### 5. Check Chat Message
After the logs finish:
- Look at the chat message from the AI
- **Below the response text**, you should see:
  ```
  🔧 Tool Calls:
  ✅ list_pods ▶
  ```

## If You See Tool Calls ✅

Great! It's working. You can:
- Click the tool to expand and see details
- Remove the console.log() statements if you want cleaner logs
- Continue using the app!

## If You DON'T See Tool Calls ❌

Tell me what logs you see in the console. Common issues:

### Logs Show: "No currentMessageId set"
→ Message not being created with assistant role
→ Need to fix addMessage logic

### Logs Show: "Found matching message" but still no tools
→ Message re-render issue
→ Need to check React component update

### No logs at all after "complete"
→ WebSocket not receiving tool events
→ Backend issue, not frontend

## Share This Info

Please run through steps 1-5 and tell me:
1. What's the first log you see?
2. Do you see "currentMessageId set to"?
3. What's the last log before you check the chat?
4. Do you see the tool calls in the message? Yes/No

This will help me fix it!
