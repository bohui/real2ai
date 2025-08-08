import React from "react";
import { Toaster, useToasterStore } from "react-hot-toast";

const NotificationSystem: React.FC = () => {
  const [liveMessage, setLiveMessage] = React.useState<string>("");
  const { toasts } = useToasterStore();

  React.useEffect(() => {
    // Announce the most recent visible toast message
    const visible = toasts.filter((t) => t.visible);
    const last = visible[visible.length - 1];
    if (last && last.message) {
      setLiveMessage(String(last.message));
    }
  }, [toasts]);

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
            background: "#363636",
            color: "#fff",
          },
          success: {
            duration: 3000,
            iconTheme: {
              primary: "#10b981",
              secondary: "#fff",
            },
          },
          error: {
            duration: 5000,
            iconTheme: {
              primary: "#ef4444",
              secondary: "#fff",
            },
          },
        }}
      />
    </>
  );
};

export default NotificationSystem;
