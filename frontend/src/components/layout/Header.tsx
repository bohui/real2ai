import React from "react";
import { Link } from "react-router-dom";
import {
  Menu,
  Bell,
  Search,
  Settings,
  LogOut,
  User,
  CreditCard,
  HelpCircle,
} from "lucide-react";
import { Menu as HeadlessMenu } from "@headlessui/react";

import Button from "@/components/ui/Button";
import { useAuthStore } from "@/store/authStore";
import { useUIStore } from "@/store/uiStore";
import { cn } from "@/utils";

const Header: React.FC = () => {
  const { user, logout } = useAuthStore();
  const { toggleSidebar, notifications } = useUIStore();

  const unreadCount = notifications.filter((n) => n.type === "info").length;

  return (
    <header className="bg-white shadow-sm border-b border-neutral-200">
      <div className="px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          {/* Left side */}
          <div className="flex items-center gap-4">
            {/* Mobile sidebar toggle */}
            <Button
              variant="ghost"
              size="sm"
              onClick={toggleSidebar}
              className="lg:hidden"
            >
              <Menu className="w-5 h-5" />
            </Button>

            {/* Search */}
            <div className="hidden md:block">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-neutral-400" />
                <input
                  type="text"
                  placeholder="Search contracts..."
                  className="pl-10 pr-4 py-2 w-64 rounded-lg border border-neutral-200 focus:ring-2 focus:ring-primary-500 focus:border-primary-500 text-sm"
                />
              </div>
            </div>
          </div>

          {/* Right side */}
          <div className="flex items-center gap-3">
            {/* Credits indicator */}
            {user && (
              <div className="hidden sm:flex items-center gap-2 px-3 py-1.5 bg-primary-50 text-primary-700 rounded-full text-sm font-medium">
                <CreditCard className="w-4 h-4" />
                {user.credits_remaining} credits
              </div>
            )}

            {/* Notifications */}
            <div className="relative">
              <Button variant="ghost" size="sm">
                <Bell className="w-5 h-5" />
                {unreadCount > 0 && (
                  <span className="absolute -top-1 -right-1 w-4 h-4 bg-danger-500 text-white text-xs rounded-full flex items-center justify-center">
                    {unreadCount > 9 ? "9+" : unreadCount}
                  </span>
                )}
              </Button>
            </div>

            {/* Help */}
            <Button variant="ghost" size="sm">
              <HelpCircle className="w-5 h-5" />
            </Button>

            {/* User menu */}
            <HeadlessMenu as="div" className="relative">
              <HeadlessMenu.Button className="flex items-center gap-2 p-2 rounded-lg hover:bg-neutral-100 transition-colors">
                <div className="w-8 h-8 bg-primary-600 rounded-full flex items-center justify-center text-white font-semibold text-sm">
                  {user?.email.charAt(0).toUpperCase()}
                </div>
                <div className="hidden md:block text-left">
                  <div className="text-sm font-medium text-neutral-900">
                    {user?.email.split("@")[0]}
                  </div>
                  <div className="text-xs text-neutral-500 capitalize">
                    {user?.user_type}
                  </div>
                </div>
              </HeadlessMenu.Button>

              <HeadlessMenu.Items className="absolute right-0 mt-2 w-56 bg-white rounded-lg shadow-lg border border-neutral-200 focus:outline-none z-50">
                <div className="p-3 border-b border-neutral-100">
                  <div className="text-sm font-medium text-neutral-900">
                    {user?.email}
                  </div>
                  <div className="text-xs text-neutral-500 mt-1">
                    {user?.australian_state} • {user?.subscription_status}
                  </div>
                </div>

                <div className="py-1">
                  <HeadlessMenu.Item>
                    {({ active }) => (
                      <Link
                        to="/app/settings"
                        className={cn(
                          "flex items-center gap-3 px-3 py-2 text-sm",
                          active
                            ? "bg-neutral-50 text-neutral-900"
                            : "text-neutral-700"
                        )}
                      >
                        <User className="w-4 h-4" />
                        Profile Settings
                      </Link>
                    )}
                  </HeadlessMenu.Item>

                  <HeadlessMenu.Item>
                    {({ active }) => (
                      <Link
                        to="/app/billing"
                        className={cn(
                          "flex items-center gap-3 px-3 py-2 text-sm",
                          active
                            ? "bg-neutral-50 text-neutral-900"
                            : "text-neutral-700"
                        )}
                      >
                        <CreditCard className="w-4 h-4" />
                        Billing & Credits
                      </Link>
                    )}
                  </HeadlessMenu.Item>

                  <HeadlessMenu.Item>
                    {({ active }) => (
                      <Link
                        to="/app/settings"
                        className={cn(
                          "flex items-center gap-3 px-3 py-2 text-sm",
                          active
                            ? "bg-neutral-50 text-neutral-900"
                            : "text-neutral-700"
                        )}
                      >
                        <Settings className="w-4 h-4" />
                        Preferences
                      </Link>
                    )}
                  </HeadlessMenu.Item>
                </div>

                <div className="py-1 border-t border-neutral-100">
                  <HeadlessMenu.Item>
                    {({ active }) => (
                      <button
                        onClick={logout}
                        className={cn(
                          "w-full flex items-center gap-3 px-3 py-2 text-sm",
                          active
                            ? "bg-neutral-50 text-danger-600"
                            : "text-danger-600"
                        )}
                      >
                        <LogOut className="w-4 h-4" />
                        Sign out
                      </button>
                    )}
                  </HeadlessMenu.Item>
                </div>
              </HeadlessMenu.Items>
            </HeadlessMenu>
          </div>
        </div>
      </div>
    </header>
  );
};

export default Header;
