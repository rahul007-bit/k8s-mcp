import { create } from 'zustand'
import { v4 as uuidv4 } from 'uuid'

export const useChatStore = create((set) => ({
  messages: [],
  toolCalls: [],
  conversationId: null,
  loading: false,
  currentMessageId: null, // Track which message is being responded to

  initConversation: () => set({ conversationId: uuidv4() }),

  addMessage: (message) => set((state) => {
    // If it's a streamed message, append to the last assistant message
    if (message.stream && state.messages.length > 0) {
      const lastMessage = state.messages[state.messages.length - 1]
      if (lastMessage.role === 'assistant') {
        console.log(`[Store] Streaming: appending to message ${lastMessage.messageId}`)
        // Just update the content, keep everything else
        const updated = [
          ...state.messages.slice(0, -1),
          {
            ...lastMessage,
            content: (lastMessage.content || '') + (message.content || '')
          }
        ]
        return { messages: updated }
      }
    }
    
    // Add new message with unique ID
    const messageId = uuidv4()
    console.log(`[Store] addMessage: role=${message.role}, messageId=${messageId}`)
    const newState = {
      messages: [...state.messages, { ...message, messageId, toolCalls: [] }]
    }
    
    // Set currentMessageId for assistant messages so tool calls get associated
    if (message.role === 'assistant') {
      newState.currentMessageId = messageId
      console.log(`[Store] Set currentMessageId: ${messageId}`)
    }
    
    return newState
  }),

  addToolCall: (toolCall) => set((state) => {
    console.log(`[Store] addToolCall: ${toolCall.tool_name}, currentMessageId=${state.currentMessageId}`)
    
    // Add to global tool calls list
    const newToolCall = {
      ...toolCall,
      id: uuidv4(),
      timestamp: new Date().toISOString()
    }
    const updatedToolCalls = [...state.toolCalls, newToolCall]
    
    // If we have a current message, add tool call to it
    if (state.currentMessageId) {
      console.log(`[Store] Linking tool to message ${state.currentMessageId}`)
      const updatedMessages = state.messages.map(msg => {
        if (msg.messageId === state.currentMessageId) {
          console.log(`[Store] ✓ Added tool to message`)
          return {
            ...msg,
            toolCalls: [...(msg.toolCalls || []), newToolCall]
          }
        }
        return msg
      })
      
      return {
        toolCalls: updatedToolCalls,
        messages: updatedMessages
      }
    }
    
    // If no current message, just add to global list
    console.log(`[Store] ✗ No currentMessageId, tool only added to global list`)
    return { toolCalls: updatedToolCalls }
  }),

  clearHistory: () => set({
    messages: [],
    toolCalls: [],
    conversationId: uuidv4(),
    currentMessageId: null
  })
}))