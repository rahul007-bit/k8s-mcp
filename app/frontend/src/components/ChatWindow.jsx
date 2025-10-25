import Message from './Message'
import LoadingSpinner from './LoadingSpinner'
import '../styles/ChatWindow.css'

export default function ChatWindow({ messages, loading }) {
  return (
    <div className="chat-window">
      {messages.length === 0 && (
        <div className="chat-empty">
          <h2>🚀 Welcome to K8s MCP Chat</h2>
          <p>Ask me about your Kubernetes cluster!</p>
          <div className="example-prompts">
            <p className="prompt-label">Try asking:</p>
            <button className="example-btn">List all pods</button>
            <button className="example-btn">What storage classes do we have?</button>
            <button className="example-btn">Show me deployments in default namespace</button>
          </div>
        </div>
      )}
      
      <div className="messages-list">
        {messages.map((msg, idx) => (
          <Message key={idx} message={msg} />
        ))}
        {loading && <LoadingSpinner />}
      </div>
    </div>
  )
}