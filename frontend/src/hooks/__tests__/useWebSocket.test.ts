import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'

// Remove the hook mock from setup to test the actual hook
vi.unmock('@/hooks/useWebSocket')
const { useWebSocket } = await import('../useWebSocket')

// Enhanced Mock WebSocket with better test support
class TestMockWebSocket {
  static CONNECTING = 0
  static OPEN = 1
  static CLOSING = 2
  static CLOSED = 3

  readyState: number = TestMockWebSocket.CONNECTING
  url: string
  onopen: ((event: Event) => void) | null = null
  onclose: ((event: CloseEvent) => void) | null = null
  onmessage: ((event: MessageEvent) => void) | null = null
  onerror: ((event: Event) => void) | null = null

  constructor(url: string) {
    this.url = url
    TestMockWebSocket.lastInstance = this
    TestMockWebSocket.instances.push(this)
  }

  send(data: string) {
    if (this.readyState !== TestMockWebSocket.OPEN) {
      throw new Error('WebSocket is not open')
    }
  }

  close(code = 1000) {
    this.readyState = TestMockWebSocket.CLOSING
    setTimeout(() => {
      this.readyState = TestMockWebSocket.CLOSED
      this.onclose?.(new CloseEvent('close', { code }))
    }, 0)
  }

  // Test helper methods
  simulateOpen() {
    this.readyState = TestMockWebSocket.OPEN
    this.onopen?.(new Event('open'))
  }

  simulateError() {
    this.onerror?.(new Event('error'))
  }

  simulateMessage(data: any) {
    if (this.readyState === TestMockWebSocket.OPEN) {
      this.onmessage?.(new MessageEvent('message', { 
        data: JSON.stringify(data) 
      }))
    }
  }

  static lastInstance: TestMockWebSocket | null = null
  static instances: TestMockWebSocket[] = []
  
  static reset() {
    TestMockWebSocket.lastInstance = null
    TestMockWebSocket.instances = []
  }
}

// Override global WebSocket for this test file
vi.stubGlobal('WebSocket', TestMockWebSocket)

describe('useWebSocket', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    TestMockWebSocket.reset()
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
      expect(result.current.ws).toBeInstanceOf(TestMockWebSocket)
      expect(result.current.isConnecting).toBe(true)
      expect(result.current.isConnected).toBe(false)
      expect(result.current.error).toBeNull()
      expect(TestMockWebSocket.lastInstance?.url).toBe('ws://localhost:8000/ws')
    })
  })

  describe('Connection Management', () => {
    it('should transition to connected state when WebSocket opens', async () => {
      const onOpen = vi.fn()
      const { result } = renderHook(() => 
        useWebSocket('ws://localhost:8000/ws', { onOpen })
      )

      const mockWs = TestMockWebSocket.lastInstance!
      
      await act(async () => {
        mockWs.simulateOpen()
      })

      expect(result.current.isConnected).toBe(true)
      expect(result.current.isConnecting).toBe(false)
      expect(onOpen).toHaveBeenCalledOnce()
    })

    it('should handle manual disconnect', () => {
      const { result } = renderHook(() => useWebSocket('ws://localhost:8000/ws'))
      
      const mockWs = TestMockWebSocket.lastInstance!
      
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
      
      const originalWs = TestMockWebSocket.lastInstance!
      
      await act(async () => {
        originalWs.simulateOpen()
      })
      
      expect(result.current.isConnected).toBe(true)

      // Trigger reconnect
      await act(async () => {
        result.current.reconnect()
      })

      // Wait for the reconnect timeout
      await act(async () => {
        await new Promise(resolve => setTimeout(resolve, 150))
      })

      // Should create new WebSocket instance
      const newWs = TestMockWebSocket.lastInstance!
      expect(newWs).not.toBe(originalWs)
      expect(result.current.isConnecting).toBe(true)
      
      // New connection should work
      await act(async () => {
        newWs.simulateOpen()
      })
      
      expect(result.current.isConnected).toBe(true)
    })
  })

  describe('Message Handling', () => {
    it('should send messages when connected', () => {
      const { result } = renderHook(() => useWebSocket('ws://localhost:8000/ws'))
      
      const mockWs = TestMockWebSocket.lastInstance!
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
      
      const mockWs = TestMockWebSocket.lastInstance!
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
      
      const mockWs = TestMockWebSocket.lastInstance!
      
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
      
      const mockWs = TestMockWebSocket.lastInstance!
      
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
      
      const mockWs = TestMockWebSocket.lastInstance!

      act(() => {
        mockWs.simulateError()
      })

      expect(result.current.error).toBe('WebSocket connection error')
      expect(result.current.isConnecting).toBe(false)
      expect(onError).toHaveBeenCalled()
    })

    it('should set error when sending fails', () => {
      const { result } = renderHook(() => useWebSocket('ws://localhost:8000/ws'))
      
      const mockWs = TestMockWebSocket.lastInstance!
      
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
      
      const mockWs = TestMockWebSocket.lastInstance!
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
      
      expect(result.current.ws).toBeInstanceOf(TestMockWebSocket)
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
      
      const mockWs = TestMockWebSocket.lastInstance!

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