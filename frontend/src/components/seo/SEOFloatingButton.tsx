/**
 * SEO Floating Button for Development
 * Shows SEO dev tools in development mode only
 */

import React, { useState } from "react";
import { Search } from "lucide-react";
import SEODevTools from "./SEODevTools";

const SEOFloatingButton: React.FC = () => {
  const [showDevTools, setShowDevTools] = useState(false);

  // Only show in development mode
  if (process.env.NODE_ENV !== "development") {
    return null;
  }

  return (
    <>
      <button
        onClick={() => setShowDevTools(true)}
        className="fixed bottom-4 right-4 z-40 w-12 h-12 bg-primary-600 text-white rounded-full shadow-lg hover:bg-primary-700 transition-colors flex items-center justify-center group"
        title="SEO Dev Tools"
      >
        <Search className="w-5 h-5 group-hover:scale-110 transition-transform" />
      </button>

      <SEODevTools
        isOpen={showDevTools}
        onClose={() => setShowDevTools(false)}
      />
    </>
  );
};

export default SEOFloatingButton;
