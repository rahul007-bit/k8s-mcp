import { useMemo, useState } from 'react'
import '../styles/Message.css'

// Simple markdown renderer
function renderMessageContent(content) {
  if (!content) return null

  // Split by double newlines for paragraphs
  const paragraphs = content.split('\n\n')
  
  return paragraphs.map((para, pIdx) => {
    if (!para.trim()) return null
    
    const parts = []
    let lastIndex = 0
    
    // Split by code blocks
    const codeBlockRegex = /```([\s\S]*?)```/g
    let match
    
    while ((match = codeBlockRegex.exec(para)) !== null) {
      // Add text before code block
      if (match.index > lastIndex) {
        parts.push({
          type: 'text',
          value: para.substring(lastIndex, match.index)
        })
      }
      
      // Add code block
      parts.push({
        type: 'code',
        value: match[1].trim()
      })
      
      lastIndex = match.index + match[0].length
    }
    
    // Add remaining text
    if (lastIndex < para.length) {
      parts.push({
        type: 'text',
        value: para.substring(lastIndex)
      })
    }
    
    // If no code blocks found, treat whole content as text
    if (parts.length === 0) {
      parts.push({
        type: 'text',
        value: para
      })
    }
    
    return (
      <div key={pIdx} className="message-paragraph">
        {parts.map((part, partIdx) => {
          if (part.type === 'code') {
            return (
              <pre key={partIdx} className="message-code-block">
                <code>{part.value}</code>
              </pre>
            )
          } else {
            // Parse text for bold/italic and line breaks
            const lines = part.value.split('\n').map((line, lineIdx) => (
              <div key={lineIdx} className="message-line">
                {line || <br />}
              </div>
            ))
            return <div key={partIdx}>{lines}</div>
          }
        })}
      </div>
    )
  })
}

// Format JSON with syntax highlighting
function SyntaxHighlightedJSON({ data }) {
  const json = typeof data === 'string' ? data : JSON.stringify(data, null, 2)
  
  // Simple JSON syntax highlighting
  const highlighted = json
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/("(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*"(\s*:)?|\b(true|false|null)\b|-?\d+(?:\.\d*)?(?:[eE][+\-]?\d+)?)/g, (match) => {
      let cls = 'json-number'
      if (/^"/.test(match)) {
        cls = /:$/.test(match) ? 'json-key' : 'json-string'
      } else if (/true|false/.test(match)) {
        cls = 'json-boolean'
      } else if (/null/.test(match)) {
        cls = 'json-null'
      }
      return `<span class="${cls}">${match}</span>`
    })
  
  return (
    <pre 
      className="json-pre"
      dangerouslySetInnerHTML={{ __html: highlighted }}
    />
  )
}

// Tool call inline display
function ToolCallInline({ toolCall }) {
  const [expanded, setExpanded] = useState(false)

  const statusEmoji = {
    'pending': '⏳',
    'executing': '⚙️',
    'completed': '✅',
    'failed': '❌'
  }

  return (
    <div className={`inline-tool-call inline-tool-${toolCall.status}`}>
      <div 
        className="inline-tool-header"
        onClick={() => setExpanded(!expanded)}
      >
        <span className="inline-tool-emoji">
          {statusEmoji[toolCall.status] || '❓'}
        </span>
        <span className="inline-tool-name">{toolCall.tool_name}</span>
        <span className="inline-expand-icon">{expanded ? '▼' : '▶'}</span>
      </div>
      
      {expanded && (
        <div className="inline-tool-details">
          <div className="inline-tool-args">
            <strong>Arguments:</strong>
            <SyntaxHighlightedJSON data={toolCall.arguments} />
          </div>
          
          {toolCall.result && (
            <div className="inline-tool-result">
              <strong>Result:</strong>
              {typeof toolCall.result === 'string' && toolCall.result.includes('\n') ? (
                <pre>{toolCall.result}</pre>
              ) : typeof toolCall.result === 'object' ? (
                <SyntaxHighlightedJSON data={toolCall.result} />
              ) : (
                <pre>{String(toolCall.result)}</pre>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default function Message({ message }) {
  const renderedContent = useMemo(() => renderMessageContent(message.content), [message.content])
  
  // Debug: Log tool calls
  if (message.toolCalls && message.toolCalls.length > 0) {
    console.log(`[Message] Found ${message.toolCalls.length} tool calls in message:`, message.toolCalls)
  }
  
  return (
    <div className={`message message-${message.role}`}>
      <div className="message-avatar">
        {message.role === 'user' ? '👤' : '🤖'}
      </div>
      <div className="message-content">
        <div className="message-text">
          {renderedContent}
        </div>
        
        {/* Display tool calls inline */}
        {message.toolCalls && message.toolCalls.length > 0 && (
          <div className="message-tool-calls">
            <div className="tool-calls-label">🔧 Tool Calls:</div>
            {message.toolCalls.map((toolCall) => (
              <ToolCallInline key={toolCall.id || toolCall.tool_name} toolCall={toolCall} />
            ))}
          </div>
        )}
        
        {message.timestamp && (
          <span className="message-time">
            {new Date(message.timestamp).toLocaleTimeString()}
          </span>
        )}
      </div>
    </div>
  )
}