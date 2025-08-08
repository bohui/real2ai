import React from 'react'
import { Toaster, toast, Toast } from 'react-hot-toast'

const NotificationSystem: React.FC = () => {
  const [liveMessage, setLiveMessage] = React.useState<string>("")

  React.useEffect(() => {
    const unsub = toast.onChange((event: { id: string; visible: boolean; toast: Toast }) => {
      const { toast: t } = event
      if (t?.message) {
        // Announce toast message for screen readers
        setLiveMessage(String(t.message))
      }
    })
    return () => {
      unsub()
    }
  }, [])

  return (
    <>
      {/* Screen reader announcement region for toasts */}
      <div aria-live="polite" aria-atomic="true" className="sr-only">
        {liveMessage}
      </div>
      <Toaster
        position="top-right"
        toastOptions={{
          duration: 4000,
          style: {
            background: '#363636',
            color: '#fff',
          },
          success: {
            duration: 3000,
            iconTheme: {
              primary: '#10b981',
              secondary: '#fff',
            },
          },
          error: {
            duration: 5000,
            iconTheme: {
              primary: '#ef4444',
              secondary: '#fff',
            },
          },
        }}
      />
    </>
  )
}

export default NotificationSystem 