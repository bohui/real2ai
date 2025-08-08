import React from "react";
import { Outlet } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";

import Sidebar from "./Sidebar";
import Header from "./Header";
import { useUIStore } from "@/store/uiStore";
import { cn } from "@/utils";

const Layout: React.FC = () => {
  const { sidebarOpen, isMobile } = useUIStore();

  return (
    <div className="h-screen flex overflow-hidden bg-neutral-50">
      <a
        href="#main-content"
        className="absolute left-[-999px] focus:left-2 focus:top-2 focus:z-50 bg-white text-neutral-900 px-3 py-2 rounded shadow"
      >
        Skip to content
      </a>
      {/* Sidebar */}
      <div
        className={cn(
          "fixed inset-y-0 left-0 z-50 w-64 transition-transform duration-300 ease-in-out",
          "lg:relative lg:z-auto lg:translate-x-0",
          sidebarOpen ? "translate-x-0" : "-translate-x-full"
        )}
      >
        <Sidebar />
      </div>

      {/* Mobile sidebar overlay */}
      <AnimatePresence>
        {sidebarOpen && isMobile && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="fixed inset-0 z-40 bg-neutral-900 bg-opacity-50 lg:hidden"
            onClick={() => useUIStore.getState().setSidebarOpen(false)}
          />
        )}
      </AnimatePresence>

      {/* Main content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Header */}
        <Header />

        {/* Page content */}
        <main id="main-content" className="flex-1 overflow-auto" tabIndex={-1}>
          <div className="py-6 px-4 sm:px-6 lg:px-8">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
};

export default Layout;
