import { create } from 'zustand'
import { NotificationState } from '@/types'

interface UIState {
  // Navigation
  sidebarOpen: boolean
  
  // Notifications
  notifications: NotificationState[]
  
  // Loading states
  globalLoading: boolean
  loadingMessage: string
  
  // Modals
  modalStack: string[]
  
  // Theme
  theme: 'light' | 'dark' | 'system'
  
  // Mobile
  isMobile: boolean
  
  // Onboarding
  showOnboarding: boolean
  
  // Actions
  toggleSidebar: () => void
  setSidebarOpen: (open: boolean) => void
  
  addNotification: (notification: Omit<NotificationState, 'id'>) => void
  removeNotification: (id: string) => void
  clearNotifications: () => void
  
  setGlobalLoading: (loading: boolean, message?: string) => void
  
  openModal: (modalId: string) => void
  closeModal: (modalId?: string) => void
  isModalOpen: (modalId: string) => boolean
  
  setTheme: (theme: 'light' | 'dark' | 'system') => void
  setIsMobile: (isMobile: boolean) => void
  
  setShowOnboarding: (show: boolean) => void
}

export const useUIStore = create<UIState>((set, get) => ({
  // Initial state
  sidebarOpen: false,
  notifications: [],
  globalLoading: false,
  loadingMessage: '',
  modalStack: [],
  theme: 'light',
  isMobile: false,
  showOnboarding: false,

  // Navigation actions
  toggleSidebar: () => {
    set(state => ({ sidebarOpen: !state.sidebarOpen }))
  },

  setSidebarOpen: (open: boolean) => {
    set({ sidebarOpen: open })
  },

  // Notification actions
  addNotification: (notification) => {
    const id = Date.now().toString()
    const newNotification: NotificationState = {
      ...notification,
      id,
      duration: notification.duration || 5000
    }
    
    set(state => ({
      notifications: [...state.notifications, newNotification]
    }))
    
    // Auto-remove notification after duration
    if (newNotification.duration && newNotification.duration > 0) {
      setTimeout(() => {
        get().removeNotification(id)
      }, newNotification.duration)
    }
  },

  removeNotification: (id: string) => {
    set(state => ({
      notifications: state.notifications.filter(n => n.id !== id)
    }))
  },

  clearNotifications: () => {
    set({ notifications: [] })
  },

  // Loading actions
  setGlobalLoading: (loading: boolean, message: string = '') => {
    set({ globalLoading: loading, loadingMessage: message })
  },

  // Modal actions
  openModal: (modalId: string) => {
    set(state => ({
      modalStack: [...state.modalStack, modalId]
    }))
  },

  closeModal: (modalId?: string) => {
    set(state => {
      if (modalId) {
        return {
          modalStack: state.modalStack.filter(id => id !== modalId)
        }
      } else {
        // Close topmost modal
        return {
          modalStack: state.modalStack.slice(0, -1)
        }
      }
    })
  },

  isModalOpen: (modalId: string) => {
    return get().modalStack.includes(modalId)
  },

  // Theme actions
  setTheme: (theme: 'light' | 'dark' | 'system') => {
    set({ theme })
    
    // Apply theme to document
    const root = document.documentElement
    if (theme === 'dark') {
      root.classList.add('dark')
    } else if (theme === 'light') {
      root.classList.remove('dark')
    } else {
      // System theme
      const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches
      if (prefersDark) {
        root.classList.add('dark')
      } else {
        root.classList.remove('dark')
      }
    }
  },

  // Mobile actions
  setIsMobile: (isMobile: boolean) => {
    set({ isMobile })
    
    // Close sidebar on mobile
    if (isMobile) {
      set({ sidebarOpen: false })
    }
  },

  // Onboarding actions
  setShowOnboarding: (show: boolean) => {
    set({ showOnboarding: show })
  }
}))

// Initialize theme on load
const savedTheme = localStorage.getItem('theme') as 'light' | 'dark' | 'system' || 'light'
useUIStore.getState().setTheme(savedTheme)

// Listen for theme changes
useUIStore.subscribe((state) => {
  localStorage.setItem('theme', state.theme)
})

// Listen for system theme changes
window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {
  const currentTheme = useUIStore.getState().theme
  if (currentTheme === 'system') {
    useUIStore.getState().setTheme('system')
  }
})

// Listen for window resize
window.addEventListener('resize', () => {
  const isMobile = window.innerWidth < 768
  useUIStore.getState().setIsMobile(isMobile)
})

// Initialize mobile state
useUIStore.getState().setIsMobile(window.innerWidth < 768)