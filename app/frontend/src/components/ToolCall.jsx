import { useState } from 'react'
import '../styles/ToolCall.css'

export default function ToolCall({ call }) {
  const [expanded, setExpanded] = useState(false)

  const statusEmoji = {
    'pending': '⏳',
    'executing': '⚙️',
    'completed': '✅',
    'failed': '❌'
  }

  // Format result for display - show full content
  const formatResult = (result) => {
    if (!result) return ''
    if (typeof result === 'string') return result
    return JSON.stringify(result, null, 2)
  }

  return (
    <div className={`tool-call tool-call-${call.status}`}>
      <div 
        className="tool-call-header"
        onClick={() => setExpanded(!expanded)}
      >
        <span className="tool-status-emoji">
          {statusEmoji[call.status] || '❓'}
        </span>
        <span className="tool-name">{call.tool_name}</span>
        <span className="tool-status-badge">{call.status}</span>
        <span className="expand-icon">{expanded ? '▼' : '▶'}</span>
      </div>
      
      {expanded && (
        <div className="tool-call-details">
          <div className="tool-args">
            <p className="label">Arguments:</p>
            <pre className="args-code">{JSON.stringify(call.arguments, null, 2)}</pre>
          </div>
          
          {call.result && (
            <div className="tool-result">
              <p className="label">Result:</p>
              <pre className="result-code">{formatResult(call.result)}</pre>
            </div>
          )}
        </div>
      )}
    </div>
  )
}