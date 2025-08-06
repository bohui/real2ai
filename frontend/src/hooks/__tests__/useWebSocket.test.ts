import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, act, waitFor } from '@testing-library/react'
import { useWebSocket } from '../useWebSocket'

// Mock WebSocket
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
    // Simulate connection opening after a short delay
    setTimeout(() => {
      this.readyState = MockWebSocket.OPEN
      this.onopen?.(new Event('open'))
    }, 10)
  }

  send(data: string) {
    // Mock send implementation
  }

  close() {
    this.readyState = MockWebSocket.CLOSED
    this.onclose?.(new CloseEvent('close'))
  }

  // Helper methods for testing
  simulateMessage(data: any) {
    if (this.readyState === MockWebSocket.OPEN) {
      this.onmessage?.(new MessageEvent('message', { 
        data: JSON.stringify(data) 
      }))
    }
  }

  simulateError() {
    this.onerror?.(new Event('error'))
  }
}

// Replace global WebSocket with mock
vi.stubGlobal('WebSocket', MockWebSocket)

describe('useWebSocket', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
    vi.restoreAllMocks()
  })

  describe('Initial State', () => {
    it('should have correct initial state when url is null', () => {
      const { result } = renderHook(() => useWebSocket(null))
      
      expect(result.current.ws).toBeNull()
      expect(result.current.isConnected).toBe(false)
      expect(result.current.isConnecting).toBe(false)
      expect(result.current.error).toBeNull()
    })

    it('should have correct initial state when url is provided', () => {
      const { result } = renderHook(() => useWebSocket('ws://localhost:8000/ws'))
      
      expect(result.current.ws).toBeNull()
      expect(result.current.isConnected).toBe(false)
      expect(result.current.isConnecting).toBe(false)
      expect(result.current.error).toBeNull()
    })
  })

  describe('Connection Management', () => {
    it('should establish connection when connect is called', async () => {
      const onOpen = vi.fn()
      const { result } = renderHook(() => 
        useWebSocket('ws://localhost:8000/ws', { onOpen })
      )

      act(() => {
        result.current.connect()
      })

      expect(result.current.isConnecting).toBe(true)

      // Fast-forward timers to simulate connection opening
      await act(async () => {
        vi.advanceTimersByTime(15)
      })

      await waitFor(() => {
        expect(result.current.isConnected).toBe(true)
      })

      expect(result.current.isConnecting).toBe(false)
      expect(onOpen).toHaveBeenCalled()
    })

    it('should handle manual disconnect', async () => {
      const onClose = vi.fn()
      const { result } = renderHook(() => 
        useWebSocket('ws://localhost:8000/ws', { onClose })
      )

      // First connect
      act(() => {
        result.current.connect()
      })

      await act(async () => {
        vi.advanceTimersByTime(15)
      })

      await waitFor(() => {
        expect(result.current.isConnected).toBe(true)
      })

      // Then disconnect
      act(() => {
        result.current.disconnect()
      })

      expect(result.current.isConnected).toBe(false)
      expect(onClose).toHaveBeenCalled()
    })

    it('should handle reconnection', async () => {
      const { result } = renderHook(() => 
        useWebSocket('ws://localhost:8000/ws', {
          reconnectAttempts: 2,
          reconnectInterval: 1000
        })
      )

      // First connect
      act(() => {
        result.current.connect()
      })

      await act(async () => {
        vi.advanceTimersByTime(15)
      })

      await waitFor(() => {
        expect(result.current.isConnected).toBe(true)
      })

      // Simulate connection loss
      act(() => {
        const mockWs = result.current.ws as any
        mockWs.simulateError()
      })

      expect(result.current.isConnected).toBe(false)
      
      // Test reconnection
      act(() => {
        result.current.reconnect()
      })

      expect(result.current.isConnecting).toBe(true)
    })
  })

  describe('Message Handling', () => {
    it('should send messages when connected', async () => {
      const { result } = renderHook(() => 
        useWebSocket('ws://localhost:8000/ws')
      )

      // Connect first
      act(() => {
        result.current.connect()
      })

      await act(async () => {
        vi.advanceTimersByTime(15)
      })

      await waitFor(() => {
        expect(result.current.isConnected).toBe(true)
      })

      // Mock the send method to track calls
      const mockSend = vi.fn()
      const mockWs = result.current.ws as any
      mockWs.send = mockSend

      const testMessage = { type: 'test', data: 'hello' }

      act(() => {
        result.current.send(testMessage)
      })

      expect(mockSend).toHaveBeenCalledWith(JSON.stringify(testMessage))
    })

    it('should handle incoming messages', async () => {
      const onMessage = vi.fn()
      const { result } = renderHook(() => 
        useWebSocket('ws://localhost:8000/ws', { onMessage })
      )

      // Connect first
      act(() => {
        result.current.connect()
      })

      await act(async () => {
        vi.advanceTimersByTime(15)
      })

      await waitFor(() => {
        expect(result.current.isConnected).toBe(true)
      })

      const testMessage = {
        type: 'analysis_update',
        data: { progress: 50 }
      }

      // Simulate incoming message
      act(() => {
        const mockWs = result.current.ws as any
        mockWs.simulateMessage(testMessage)
      })

      expect(onMessage).toHaveBeenCalledWith(
        expect.objectContaining({
          type: 'analysis_update',
          data: { progress: 50 },
          timestamp: expect.any(Number)
        })
      )
    })

    it('should not send messages when disconnected', () => {
      const { result } = renderHook(() => 
        useWebSocket('ws://localhost:8000/ws')
      )

      const testMessage = { type: 'test', data: 'hello' }

      // Try to send while disconnected
      act(() => {
        result.current.send(testMessage)
      })

      // Should not throw error, just not send
      expect(result.current.isConnected).toBe(false)
    })
  })

  describe('Error Handling', () => {
    it('should handle connection errors', async () => {
      const onError = vi.fn()
      const { result } = renderHook(() => 
        useWebSocket('ws://localhost:8000/ws', { onError })
      )

      act(() => {
        result.current.connect()
      })

      // Simulate connection error
      act(() => {
        const mockWs = result.current.ws as any
        if (mockWs) {
          mockWs.simulateError()
        }
      })

      expect(onError).toHaveBeenCalled()
    })

    it('should set error state on connection failure', async () => {
      const { result } = renderHook(() => 
        useWebSocket('ws://invalid-url')
      )

      act(() => {
        result.current.connect()
      })

      // Simulate error during connection
      act(() => {
        const mockWs = result.current.ws as any
        if (mockWs) {
          mockWs.simulateError()
        }
      })

      expect(result.current.error).toBeTruthy()
    })
  })

  describe('Cleanup', () => {
    it('should cleanup WebSocket connection on unmount', async () => {
      const { result, unmount } = renderHook(() => 
        useWebSocket('ws://localhost:8000/ws')
      )

      act(() => {
        result.current.connect()
      })

      await act(async () => {
        vi.advanceTimersByTime(15)
      })

      await waitFor(() => {
        expect(result.current.isConnected).toBe(true)
      })

      const mockClose = vi.fn()
      const mockWs = result.current.ws as any
      mockWs.close = mockClose

      unmount()

      expect(mockClose).toHaveBeenCalled()
    })
  })

  describe('Options Configuration', () => {
    it('should respect reconnection configuration', () => {
      const { result } = renderHook(() => 
        useWebSocket('ws://localhost:8000/ws', {
          reconnectAttempts: 5,
          reconnectInterval: 2000
        })
      )

      // Configuration should be applied (internal state)
      expect(result.current.ws).toBeNull()
    })

    it('should handle heartbeat configuration', () => {
      const { result } = renderHook(() => 
        useWebSocket('ws://localhost:8000/ws', {
          heartbeatInterval: 10000
        })
      )

      expect(result.current.ws).toBeNull()
    })
  })

  describe('Callback Functions', () => {
    it('should call onOpen when connection opens', async () => {
      const onOpen = vi.fn()
      const { result } = renderHook(() => 
        useWebSocket('ws://localhost:8000/ws', { onOpen })
      )

      act(() => {
        result.current.connect()
      })

      await act(async () => {
        vi.advanceTimersByTime(15)
      })

      await waitFor(() => {
        expect(onOpen).toHaveBeenCalled()
      })
    })

    it('should call onClose when connection closes', async () => {
      const onClose = vi.fn()
      const { result } = renderHook(() => 
        useWebSocket('ws://localhost:8000/ws', { onClose })
      )

      act(() => {
        result.current.connect()
      })

      await act(async () => {
        vi.advanceTimersByTime(15)
      })

      await waitFor(() => {
        expect(result.current.isConnected).toBe(true)
      })

      act(() => {
        result.current.disconnect()
      })

      expect(onClose).toHaveBeenCalled()
    })

    it('should call onError when error occurs', async () => {
      const onError = vi.fn()
      const { result } = renderHook(() => 
        useWebSocket('ws://localhost:8000/ws', { onError })
      )

      act(() => {
        result.current.connect()
      })

      act(() => {
        const mockWs = result.current.ws as any
        if (mockWs) {
          mockWs.simulateError()
        }
      })

      expect(onError).toHaveBeenCalled()
    })
  })
})