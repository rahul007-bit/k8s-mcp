import { useState, useEffect, useRef } from 'react'
import ChatWindow from '../components/ChatWindow'
import ToolCallHistory from '../components/ToolCallHistory'
import '../styles/ChatPage.css'
import { useChatStore } from '../store/chatStore'
import { useChatWebSocket } from '../hooks/useChatWebSocket'

export default function ChatPage() {
  const [userInput, setUserInput] = useState('')
  const [loading, setLoading] = useState(false)
  const messagesEndRef = useRef(null)
  
  const { 
    messages, 
    toolCalls, 
    conversationId, 
    addMessage, 
    addToolCall,
    initConversation 
  } = useChatStore()

  const hasCreatedAssistantMessage = useRef(false)

  const handleWebSocketMessage = (event) => {
    const { type, data } = event
    
    console.log(`[WS] ${type}`)
    
    switch (type) {
      case 'thinking':
        break
        
      case 'text':
        console.log(`[WS] text: "${data.text.substring(0, 30)}..."`)
        // Create assistant message on first text event
        if (!hasCreatedAssistantMessage.current) {
          hasCreatedAssistantMessage.current = true
          addMessage({
            role: 'assistant',
            content: data.text,
            timestamp: new Date().toISOString()
          })
        } else {
          // Stream to existing message
          addMessage({
            role: 'assistant',
            content: data.text,
            timestamp: new Date().toISOString(),
            stream: true
          })
        }
        break
        
      case 'tool_call_start':
        console.log(`[WS] tool_call_start: ${data.tool_name}`)
        // Create message if we haven't already
        if (!hasCreatedAssistantMessage.current) {
          hasCreatedAssistantMessage.current = true
          addMessage({
            role: 'assistant',
            content: '',
            timestamp: new Date().toISOString()
          })
        }
        break
        
      case 'tool_call_end':
        console.log(`[WS] tool_call_end: ${data.tool_name}`)
        addToolCall({
          tool_name: data.tool_name,
          arguments: data.arguments,
          result: data.result,
          status: data.status
        })
        break
        
      case 'complete':
        console.log('[WS] complete')
        hasCreatedAssistantMessage.current = false
        setLoading(false)
        break
        
      case 'error':
        console.error('[WS] error:', data.error)
        hasCreatedAssistantMessage.current = false
        addMessage({
          role: 'assistant',
          content: `Error: ${data.error}`,
          timestamp: new Date().toISOString()
        })
        setLoading(false)
        break
    }
  }

  const { connect, send, disconnect } = useChatWebSocket(
    handleWebSocketMessage,
    (error) => {
      console.error('WebSocket error:', error)
      setLoading(false)
    }
  )

  useEffect(() => {
    if (!conversationId) {
      initConversation()
    }
    // Connect to WebSocket
    connect()
    
    return () => {
      disconnect()
    }
  }, [conversationId])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleSendMessage = async (e) => {
    e.preventDefault()
    if (!userInput.trim() || loading) return

    const message = userInput
    setUserInput('')
    setLoading(true)

    // Add user message to UI
    addMessage({
      role: 'user',
      content: message,
      timestamp: new Date().toISOString()
    })

    try {
      // Send message via WebSocket
      send({
        message,
        conversation_id: conversationId
      })
    } catch (error) {
      console.error('Error:', error)
      addMessage({
        role: 'assistant',
        content: `Error: ${error.message}`,
        timestamp: new Date().toISOString()
      })
      setLoading(false)
    }
  }

  const handleKeyDown = (e) => {
    // Allow Shift+Enter for new line, Enter alone to send
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSendMessage(e)
    }
  }

  return (
    <div className="chat-page">
      <div className="chat-container">
        <div className="chat-main">
          <ChatWindow messages={messages} loading={loading} />
          <div ref={messagesEndRef} />
          
          <form onSubmit={handleSendMessage} className="message-input-form">
            <textarea
              value={userInput}
              onChange={(e) => setUserInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask me anything about Kubernetes... (Shift+Enter for new line, Enter to send)"
              disabled={loading}
              className="message-input"
              rows="3"
            />
            <button 
              type="submit" 
              disabled={loading || !userInput.trim()}
              className="send-button"
            >
              {loading ? 'Sending...' : 'Send'}
            </button>
          </form>
        </div>

        <div className="sidebar">
          <ToolCallHistory toolCalls={toolCalls} />
        </div>
      </div>
    </div>
  )
}