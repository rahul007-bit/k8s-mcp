import { useEffect, useRef, useCallback } from 'react'

export function useChatWebSocket(onMessage, onError) {
  const wsRef = useRef(null)
  const reconnectAttemptsRef = useRef(0)
  const maxReconnectAttemptsRef = useRef(5)
  const reconnectDelayRef = useRef(1000)
  const reconnectTimeoutRef = useRef(null)

  const connect = useCallback(() => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsUrl = `${protocol}//${window.location.host}/ws/chat`
    
    console.log('Connecting to WebSocket:', wsUrl)
    wsRef.current = new WebSocket(wsUrl)

    wsRef.current.onopen = () => {
      console.log('✓ WebSocket connected')
      reconnectAttemptsRef.current = 0
      reconnectDelayRef.current = 1000
    }

    wsRef.current.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data)
        console.log('[WS]', message.type)
        onMessage(message)
      } catch (error) {
        console.error('Failed to parse WebSocket message:', error)
      }
    }

    wsRef.current.onerror = (error) => {
      console.error('✗ WebSocket error')
      console.error(error)
      if (onError) onError(error)
    }

    wsRef.current.onclose = () => {
      console.log('WebSocket disconnected')
      attemptReconnect()
    }
  }, [onMessage, onError])

  const attemptReconnect = useCallback(() => {
    if (reconnectAttemptsRef.current < maxReconnectAttemptsRef.current) {
      reconnectAttemptsRef.current += 1
      const delay = reconnectDelayRef.current * Math.pow(1.5, reconnectAttemptsRef.current - 1)
      console.log(`Reconnecting in ${delay}ms (attempt ${reconnectAttemptsRef.current}/${maxReconnectAttemptsRef.current})`)
      
      reconnectTimeoutRef.current = setTimeout(() => {
        connect()
      }, delay)
    } else {
      console.error('Max reconnection attempts reached')
    }
  }, [connect])

  const send = useCallback((data) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(data))
    } else {
      console.error('WebSocket not ready. State:', wsRef.current?.readyState || 'null')
    }
  }, [])

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current)
    }
    if (wsRef.current) {
      wsRef.current.close()
    }
  }, [])

  return { connect, send, disconnect, ws: wsRef.current }
}
