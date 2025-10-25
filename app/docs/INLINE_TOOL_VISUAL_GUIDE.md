# Inline Tool Calls - Visual Guide

## Layout Overview

```
┌─────────────────────────────────────────────────────────────┐
│                      CHAT PAGE                              │
├─────────────────────────────────────────┬───────────────────┤
│                                         │                   │
│  CHAT WINDOW                            │  TOOL CALL        │
│  ================================        │  HISTORY          │
│                                         │  ==============   │
│  👤 User Message:                       │                   │
│  "list all pods"                        │  ✅ list_pods     │
│                                         │  ✅ get_nodes     │
│  🤖 Assistant Response:                 │  ✅ deploy_app    │
│  Here are the pods in your cluster:     │                   │
│  [streaming text...]                    │                   │
│                                         │                   │
│  🔧 Tool Calls:                         │                   │
│  ✅ list_pods ▼                         │                   │
│     Arguments:                          │                   │
│     {                                   │                   │
│       "all_namespaces": true            │                   │
│     }                                   │                   │
│     Result:                             │                   │
│     NAMESPACE    NAME     READY  STATUS │                   │
│     argocd       argocd-  1/1    Running│                   │
│     ...                                 │                   │
│                                         │                   │
│  [Input box at bottom]                  │                   │
│                                         │                   │
└─────────────────────────────────────────┴───────────────────┘
```

## Feature Breakdown

### 1. Inline Tool Section
Located below the model response text with "🔧 Tool Calls:" header

```
🔧 Tool Calls:                  ← Label
  ✅ list_pods ▼                ← Expandable tool
  ✅ get_nodes ▶                ← Collapsed tool  
  ❌ deploy_app ▼               ← Failed tool
```

### 2. Expandable Tool Details

**Collapsed State** (click to expand):
```
✅ list_pods ▶
```

**Expanded State** (click to collapse):
```
✅ list_pods ▼
   Arguments:
   {
     "all_namespaces": true,
     "filter": "Running"
   }
   Result:
   NAMESPACE      NAME                READY  STATUS   RESTARTS  AGE
   argocd         argocd-app-ctrl-0   1/1    Running  7         198m
   argocd         argocd-dex-server   1/1    Running  7         198m
   default        nginx-app           2/2    Running  0         12m
   kube-system    coredns             2/2    Running  1         30d
```

### 3. Status Indicators

| Status | Emoji | Color | Meaning |
|--------|-------|-------|---------|
| ✅ | Green | Completed | Tool executed successfully |
| ❌ | Red | Failed | Tool execution error |
| ⏳ | Yellow | Pending | Waiting to execute |
| ⚙️ | Blue | Executing | Currently running |

### 4. Visual Styling

**Assistant Message Box**:
```
┌─────────────────────────────────────┐
│ 🤖 Response with inline tools       │
│                                     │
│ Model generated text...             │
│                                     │
│ ─────────────────────────────────── │ ← Divider
│ 🔧 Tool Calls:                      │
│                                     │
│ ┌─ ✅ tool_name ▼ ─────────────┐  │
│ │ Arguments:                    │  │
│ │ {...}                         │  │ ← Expandable box
│ │ Result:                       │  │
│ │ [scrollable output]           │  │
│ └───────────────────────────────┘  │
│                                     │
└─────────────────────────────────────┘
```

**User Message Box**:
```
┌─────────────────────────────────────┐
│ 👤 User message                     │
└─────────────────────────────────────┘
```

## Interaction Flow

### User sends message:
```
User Input: "show me all pods and services"
      ↓
[Send Button]
      ↓
Message added to chat
```

### Model responds in real-time:
```
1. Text streams in:
   "Here are all pods and services..."

2. Tool starts executing:
   ⏳ list_pods
   ⏳ list_services

3. Tool completes:
   ✅ list_pods ▶
   ✅ list_services ▶

4. User can expand:
   ✅ list_pods ▼
      [shows arguments and results]
```

## Color Scheme

### Light Mode (Sidebar)
- Background: #f9f9f9 (light gray)
- Text: #333 (dark gray)
- Accent: #667eea (blue)
- Borders: #e0e0e0 (light border)

### Assistant Messages
- Background: #f0f0f0 (light gray)
- Tool boxes: Blue accent (#667eea)
- Text: Dark (#333)
- Code block: Dark theme (#1e1e1e)

### User Messages
- Background: #667eea (blue)
- Tool boxes: White with transparency
- Text: White
- Code block: Dark with light text

## Responsive Behavior

### Desktop (> 1024px)
- Chat on left (70%)
- Tool history on right (30%)
- Inline tools visible in messages
- Full tool details in sidebar

### Tablet/Mobile (< 1024px)
- Chat full width
- Tool history below (collapsible)
- Inline tools still visible
- Scrollable code blocks

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| Enter | Send message |
| Shift+Enter | New line in input |
| ↑/↓ | (Future) Navigate history |

## Animation States

### Expand Animation
```
Tool Header Clicked
    ↓
Height: 0 → full
Opacity: 0 → 1
Details slide down (200ms)
```

### Hover Effects
```
Tool Header Hovered
    ↓
Background: slightly darker
Arrow: more visible
Cursor: pointer
```

## Example Scenarios

### Scenario 1: Simple Tool Call
```
User: "list pods"
↓
🤖: Here are the pods...
    🔧 Tool Calls:
    ✅ list_pods ▶
```

### Scenario 2: Multiple Tools
```
User: "show me pods and deployments"
↓
🤖: Found multiple resources...
    🔧 Tool Calls:
    ✅ list_pods ▶
    ✅ list_deployments ▶
```

### Scenario 3: Tool Failure
```
User: "apply invalid yaml"
↓
🤖: I encountered an error...
    🔧 Tool Calls:
    ❌ apply_yaml ▶
       [shows error details when expanded]
```

### Scenario 4: Expanded View
```
User: "get pod details"
↓
🤖: Here's the pod information...
    🔧 Tool Calls:
    ✅ list_pods ▼
       Arguments:
       {
         "namespace": "default",
         "all_namespaces": false
       }
       Result:
       [shows full table of pods]
```

## Performance Considerations

- **Lazy Rendering**: Details only render when expanded
- **Smooth Scrolling**: CSS scrollbars for long content
- **Optimized Updates**: Zustand batches updates
- **No Layout Shift**: Fixed heights for containers

## Accessibility

- Clickable headers have cursor pointer
- Arrow indicators show expand state
- Status emoji provide visual feedback
- Keyboard navigation supported
- Proper color contrast for visibility

## Tips & Tricks

1. **Expand All at Once**: Each tool expands independently
2. **Scroll Results**: Long outputs have scrollable boxes
3. **Copy Output**: Highlight and Cmd/Ctrl+C works
4. **Full History**: Check sidebar for complete history
5. **Export**: Can copy entire message text

## Future Enhancements

- [ ] Collapse/expand all at once
- [ ] Copy individual results
- [ ] Export as JSON/CSV
- [ ] Search tool history
- [ ] Tool execution timeline
- [ ] Result diff viewer
