import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { useWebSocket } from '../useWebSocket'

// Simplified Mock WebSocket with synchronous behavior for reliable testing
class MockWebSocket {
  static CONNECTING = 0
  static OPEN = 1
  static CLOSING = 2
  static CLOSED = 3

  readyState: number = MockWebSocket.CONNECTING
  url: string
  onopen: ((event: Event) => void) | null = null
  onclose: ((event: CloseEvent) => void) | null = null
  onmessage: ((event: MessageEvent) => void) | null = null
  onerror: ((event: Event) => void) | null = null

  constructor(url: string) {
    this.url = url
    // Store instance for test access
    MockWebSocket.lastInstance = this
  }

  send(_data: string) {
    if (this.readyState !== MockWebSocket.OPEN) {
      throw new Error('WebSocket is not open')
    }
  }

  close(code = 1000) {
    this.readyState = MockWebSocket.CLOSING
    setTimeout(() => {
      this.readyState = MockWebSocket.CLOSED
      this.onclose?.(new CloseEvent('close', { code }))
    }, 0)
  }

  // Test helper methods
  simulateOpen() {
    this.readyState = MockWebSocket.OPEN
    this.onopen?.(new Event('open'))
  }

  simulateError() {
    this.onerror?.(new Event('error'))
  }

  simulateMessage(data: any) {
    if (this.readyState === MockWebSocket.OPEN) {
      this.onmessage?.(new MessageEvent('message', { 
        data: JSON.stringify(data) 
      }))
    }
  }

  // Store last created instance for testing
  static lastInstance: MockWebSocket | null = null
}

// Mock WebSocket globally
vi.stubGlobal('WebSocket', MockWebSocket)

describe('useWebSocket', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    MockWebSocket.lastInstance = null
  })

  describe('Initial State', () => {
    it('should have correct initial state when url is null', () => {
      const { result } = renderHook(() => useWebSocket(null))
      
      expect(result.current.ws).toBeNull()
      expect(result.current.isConnected).toBe(false)
      expect(result.current.isConnecting).toBe(false)
      expect(result.current.error).toBeNull()
    })

    it('should create WebSocket when url is provided', () => {
      const { result } = renderHook(() => useWebSocket('ws://localhost:8000/ws'))
      
      // Hook creates WebSocket immediately when URL provided
      expect(result.current.ws).toBeInstanceOf(MockWebSocket)
      expect(result.current.isConnecting).toBe(true)
      expect(result.current.isConnected).toBe(false)
      expect(result.current.error).toBeNull()
      expect(MockWebSocket.lastInstance?.url).toBe('ws://localhost:8000/ws')
    })
  })

  describe('Connection Management', () => {
    it('should transition to connected state when WebSocket opens', async () => {
      const onOpen = vi.fn()
      const { result } = renderHook(() => 
        useWebSocket('ws://localhost:8000/ws', { onOpen })
      )

      const mockWs = MockWebSocket.lastInstance!
      
      await act(async () => {
        mockWs.simulateOpen()
      })

      expect(result.current.isConnected).toBe(true)
      expect(result.current.isConnecting).toBe(false)
      expect(onOpen).toHaveBeenCalledOnce()
    })

    it('should handle manual disconnect', () => {
      const { result } = renderHook(() => useWebSocket('ws://localhost:8000/ws'))
      
      const mockWs = MockWebSocket.lastInstance!
      
      act(() => {
        mockWs.simulateOpen()
      })
      
      expect(result.current.isConnected).toBe(true)

      act(() => {
        result.current.disconnect()
      })

      expect(result.current.isConnected).toBe(false)
      expect(result.current.isConnecting).toBe(false)
      expect(result.current.ws).toBeNull()
      expect(result.current.error).toBeNull()
    })

    it('should provide reconnect functionality', async () => {
      const { result } = renderHook(() => useWebSocket('ws://localhost:8000/ws'))
      
      let mockWs = MockWebSocket.lastInstance!
      
      await act(async () => {
        mockWs.simulateOpen()
      })
      
      expect(result.current.isConnected).toBe(true)

      // Trigger reconnect
      await act(async () => {
        result.current.reconnect()
      })

      // Should create new WebSocket instance
      expect(MockWebSocket.lastInstance).not.toBe(mockWs)
      expect(result.current.isConnecting).toBe(true)
      
      // New connection should work
      mockWs = MockWebSocket.lastInstance!
      await act(async () => {
        mockWs.simulateOpen()
      })
      
      expect(result.current.isConnected).toBe(true)
    })
  })

  describe('Message Handling', () => {
    it('should send messages when connected', () => {
      const { result } = renderHook(() => useWebSocket('ws://localhost:8000/ws'))
      
      const mockWs = MockWebSocket.lastInstance!
      const sendSpy = vi.spyOn(mockWs, 'send')
      
      act(() => {
        mockWs.simulateOpen()
      })

      act(() => {
        result.current.send({ type: 'test', data: 'hello' })
      })

      expect(sendSpy).toHaveBeenCalledWith('{"type":"test","data":"hello"}')
    })

    it('should not send messages when disconnected', () => {
      const { result } = renderHook(() => useWebSocket('ws://localhost:8000/ws'))
      
      const mockWs = MockWebSocket.lastInstance!
      const sendSpy = vi.spyOn(mockWs, 'send')

      // Don't open the connection
      act(() => {
        result.current.send({ type: 'test', data: 'hello' })
      })

      expect(sendSpy).not.toHaveBeenCalled()
      expect(result.current.error).toBe('WebSocket is not connected')
    })

    it('should handle incoming messages', () => {
      const onMessage = vi.fn()
      renderHook(() => 
        useWebSocket('ws://localhost:8000/ws', { onMessage })
      )
      
      const mockWs = MockWebSocket.lastInstance!
      
      act(() => {
        mockWs.simulateOpen()
      })

      act(() => {
        mockWs.simulateMessage({ type: 'notification', data: 'test message' })
      })

      expect(onMessage).toHaveBeenCalledWith({
        type: 'notification',
        data: 'test message'
      })
    })

    it('should ignore pong messages', () => {
      const onMessage = vi.fn()
      renderHook(() => 
        useWebSocket('ws://localhost:8000/ws', { onMessage })
      )
      
      const mockWs = MockWebSocket.lastInstance!
      
      act(() => {
        mockWs.simulateOpen()
      })

      act(() => {
        mockWs.simulateMessage({ type: 'pong', timestamp: Date.now() })
      })

      expect(onMessage).not.toHaveBeenCalled()
    })
  })

  describe('Error Handling', () => {
    it('should handle connection errors', () => {
      const onError = vi.fn()
      const { result } = renderHook(() => 
        useWebSocket('ws://localhost:8000/ws', { onError })
      )
      
      const mockWs = MockWebSocket.lastInstance!

      act(() => {
        mockWs.simulateError()
      })

      expect(result.current.error).toBe('WebSocket connection error')
      expect(result.current.isConnecting).toBe(false)
      expect(onError).toHaveBeenCalled()
    })

    it('should set error when sending fails', () => {
      const { result } = renderHook(() => useWebSocket('ws://localhost:8000/ws'))
      
      const mockWs = MockWebSocket.lastInstance!
      
      act(() => {
        mockWs.simulateOpen()
      })

      // Mock send to throw error
      vi.spyOn(mockWs, 'send').mockImplementation(() => {
        throw new Error('Send failed')
      })

      act(() => {
        result.current.send('test')
      })

      expect(result.current.error).toBe('Failed to send message')
    })
  })

  describe('Cleanup', () => {
    it('should cleanup on unmount', () => {
      const { result, unmount } = renderHook(() => 
        useWebSocket('ws://localhost:8000/ws')
      )
      
      const mockWs = MockWebSocket.lastInstance!
      const closeSpy = vi.spyOn(mockWs, 'close')
      
      act(() => {
        mockWs.simulateOpen()
      })

      expect(result.current.isConnected).toBe(true)

      unmount()

      expect(closeSpy).toHaveBeenCalled()
    })
  })

  describe('Configuration', () => {
    it('should respect reconnection configuration', () => {
      const { result } = renderHook(() => 
        useWebSocket('ws://localhost:8000/ws', { 
          reconnectAttempts: 0  // Disable reconnection
        })
      )
      
      expect(result.current.ws).toBeInstanceOf(MockWebSocket)
      expect(result.current.isConnecting).toBe(true)
    })

    it('should call callbacks appropriately', () => {
      const callbacks = {
        onOpen: vi.fn(),
        onClose: vi.fn(),
        onError: vi.fn(),
        onMessage: vi.fn()
      }

      renderHook(() => 
        useWebSocket('ws://localhost:8000/ws', callbacks)
      )
      
      const mockWs = MockWebSocket.lastInstance!

      // Test open callback
      act(() => {
        mockWs.simulateOpen()
      })
      expect(callbacks.onOpen).toHaveBeenCalledOnce()

      // Test message callback
      act(() => {
        mockWs.simulateMessage({ type: 'test' })
      })
      expect(callbacks.onMessage).toHaveBeenCalledWith({ type: 'test' })

      // Test error callback
      act(() => {
        mockWs.simulateError()
      })
      expect(callbacks.onError).toHaveBeenCalledOnce()
    })
  })
})