import ToolCall from './ToolCall'
import '../styles/ToolCallHistory.css'

export default function ToolCallHistory({ toolCalls }) {
  return (
    <div className="tool-call-history">
      <h3>🔧 Tool Calls ({toolCalls.length})</h3>
      
      {toolCalls.length === 0 ? (
        <p className="empty-history">No tools called yet</p>
      ) : (
        <div className="tools-list">
          {toolCalls.map((call, idx) => (
            <ToolCall key={idx} call={call} />
          ))}
        </div>
      )}
    </div>
  )
}