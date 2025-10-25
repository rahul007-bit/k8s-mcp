# Debugging Tool Calls in Chat Messages

## Steps to Debug

1. **Open Browser DevTools** (F12 or Cmd+Option+I)

2. **Go to Console Tab**

3. **Send a message** that triggers tool calls (e.g., "list all pods")

4. **Look for these logs**:

### Expected Console Output:

```
[WS] thinking
[WS] text
[WS] tool_call_start
[Store] addToolCall: list_pods, currentMessageId: abc-123-def
[Store] Linking tool call to message: abc-123-def
[Store] Found matching message, adding tool call
[Message] Found 1 tool calls in message:
[WS] tool_call_end
[WS] complete
```

### What Each Log Means:

- `[Store] addToolCall: list_pods, currentMessageId: (uuid)` 
  - ✅ currentMessageId is set correctly
  - ❌ If it shows `null`, the tool won't appear in the message

- `[Store] Linking tool call to message: (uuid)`
  - ✅ We found a currentMessageId
  - ❌ If missing, tool goes only to sidebar

- `[Store] Found matching message, adding tool call`
  - ✅ Tool successfully added to message
  - ❌ If missing, message doesn't have matching ID

- `[Message] Found N tool calls in message`
  - ✅ Message component sees the tool calls
  - ❌ If missing, tool calls aren't rendering

## If Tool Calls Don't Appear:

### Check 1: Is currentMessageId being set?
Look for this log when you send a message:
```
[Store] addMessage: role=assistant, messageId=(uuid)
[Store] currentMessageId set to: (uuid)
```

### Check 2: Is it staying set?
The currentMessageId should persist through multiple tool calls:
```
[WS] tool_call_end (first tool)
[Store] addToolCall: list_pods, currentMessageId: abc-123-def ✓

[WS] tool_call_end (second tool)  
[Store] addToolCall: list_services, currentMessageId: abc-123-def ✓
```

### Check 3: Are message IDs matching?
```
Message created with messageId: xyz-789-uvw
Tool added to message: xyz-789-uvw
↓
Should match!
```

## Browser DevTools Inspection

In Console, run:
```javascript
// Get current store state
// (This depends on your store setup - if Zustand doesn't expose it)

// Or check the actual DOM elements:
document.querySelectorAll('.inline-tool-call').length
// Should return > 0 if tools are rendering
```

## Common Issues & Fixes

### Issue: currentMessageId is null
**Cause**: Assistant message not marked with role
**Fix**: Check ChatPage.jsx - message should have `role: 'assistant'`

### Issue: currentMessageId changes between tool calls
**Cause**: New assistant message being created
**Fix**: Use `stream: true` flag and check streamed messages

### Issue: Message ID doesn't match
**Cause**: messageId not being preserved during updates
**Fix**: Ensure spread operator preserves messageId in updates

## Quick Verification

1. Open DevTools Console
2. Run: `document.querySelectorAll('.message-tool-calls').length`
   - **Result > 0** = Tool calls rendering! ✅
   - **Result = 0** = Tool calls not showing ❌

3. If result is 0, check logs for "No currentMessageId set"

## Reset State

If debugging gets messy:
```javascript
// Hard refresh the page
Ctrl+Shift+R (or Cmd+Shift+R on Mac)
```

## Additional Notes

- Tool calls appear in both message AND sidebar
- Sidebar shows all calls, message shows related ones
- Each tool call should have status: "completed" or "failed"
- Expandable UI needs CSS to work

## Next Steps

1. Check console logs
2. Share the log output
3. We'll identify which step is failing
4. Fix accordingly
