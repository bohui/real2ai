import React from "react";
import { motion } from "framer-motion";
import {
  User,
  Bell,
  Shield,
  CreditCard,
  Save,
  Eye,
  EyeOff,
  Key,
  Sun,
  Moon,
  Monitor,
} from "lucide-react";

import Button from "@/components/ui/Button";
import Input from "@/components/ui/Input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { useAuthStore } from "@/store/authStore";
import { useUIStore } from "@/store/uiStore";
import { usePageSEO } from "@/contexts/SEOContext";
import { cn } from "@/utils";
import type { AustralianState } from "@/types";

const SettingsPage: React.FC = () => {
  const { user, updateProfile } = useAuthStore();
  const { addNotification, theme, setTheme } = useUIStore();

  // SEO for Settings page
  usePageSEO({
    title: "Settings - Real2AI",
    description:
      "Manage your Real2AI account settings, preferences, and subscription. Customize your AI-powered real estate analysis experience.",
    keywords: [
      "account settings",
      "Real2AI settings",
      "user preferences",
      "subscription management",
      "profile settings",
    ],
    canonical: "/app/settings",
    noIndex: true, // Private settings page
  });

  // Form states
  const [activeTab, setActiveTab] = React.useState<
    "profile" | "notifications" | "security" | "billing" | "appearance"
  >("profile");
  const [showCurrentPassword, setShowCurrentPassword] = React.useState(false);
  const [showNewPassword, setShowNewPassword] = React.useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = React.useState(false);

  // Profile form
  const [profileForm, setProfileForm] = React.useState({
    email: user?.email || "",
    full_name: user?.full_name || "",
    phone_number: user?.phone_number || "",
    australian_state: user?.australian_state || ("NSW" as AustralianState),
    organization: user?.organization || "",
  });

  // Password form
  const [passwordForm, setPasswordForm] = React.useState({
    current_password: "",
    new_password: "",
    confirm_password: "",
  });

  // Notification preferences
  const [notificationPrefs, setNotificationPrefs] = React.useState({
    analysis_complete: true,
    weekly_summary: true,
    security_alerts: true,
    product_updates: false,
    marketing_emails: false,
  });

  const australianStates: AustralianState[] = [
    "NSW",
    "VIC",
    "QLD",
    "WA",
    "SA",
    "TAS",
    "ACT",
    "NT",
  ];

  const tabs = [
    { key: "profile", label: "Profile", icon: User },
    { key: "notifications", label: "Notifications", icon: Bell },
    { key: "security", label: "Security", icon: Shield },
    { key: "billing", label: "Billing", icon: CreditCard },
    { key: "appearance", label: "Appearance", icon: Sun },
  ] as const;

  // Theme preview (resolve system to current preference)
  const [prefersDark, setPrefersDark] = React.useState(
    () => window.matchMedia("(prefers-color-scheme: dark)").matches
  );
  React.useEffect(() => {
    const mql = window.matchMedia("(prefers-color-scheme: dark)");
    const handler = (e: MediaQueryListEvent) => setPrefersDark(e.matches);
    mql.addEventListener("change", handler);
    return () => mql.removeEventListener("change", handler);
  }, []);
  const effectiveTheme =
    theme === "system" ? (prefersDark ? "dark" : "light") : theme;

  // Handle profile update
  const handleProfileUpdate = async (e: React.FormEvent) => {
    e.preventDefault();

    try {
      await updateProfile(profileForm);
      addNotification({
        type: "success",
        title: "Profile updated",
        message: "Your profile information has been successfully updated.",
      });
    } catch (error) {
      addNotification({
        type: "error",
        title: "Update failed",
        message: "Unable to update profile. Please try again.",
      });
    }
  };

  // Handle password change
  const handlePasswordChange = async (e: React.FormEvent) => {
    e.preventDefault();

    if (passwordForm.new_password !== passwordForm.confirm_password) {
      addNotification({
        type: "error",
        title: "Password mismatch",
        message: "New password and confirmation do not match.",
      });
      return;
    }

    try {
      // Implementation would call password change API
      addNotification({
        type: "success",
        title: "Password changed",
        message: "Your password has been successfully updated.",
      });
      setPasswordForm({
        current_password: "",
        new_password: "",
        confirm_password: "",
      });
    } catch (error) {
      addNotification({
        type: "error",
        title: "Password change failed",
        message:
          "Unable to change password. Please check your current password.",
      });
    }
  };

  // Handle notification preferences update
  const handleNotificationUpdate = async () => {
    try {
      // Implementation would call API to update preferences
      addNotification({
        type: "success",
        title: "Preferences updated",
        message: "Your notification preferences have been saved.",
      });
    } catch (error) {
      addNotification({
        type: "error",
        title: "Update failed",
        message: "Unable to update notification preferences.",
      });
    }
  };

  return (
    <div className="max-w-5xl mx-auto space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-neutral-900">Settings</h1>
        <p className="text-neutral-600 mt-1">
          Manage your account settings and preferences
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
        {/* Navigation */}
        <div className="lg:col-span-1">
          <nav className="space-y-2">
            {tabs.map((tab) => {
              const IconComponent = tab.icon;

              return (
                <button
                  key={tab.key}
                  onClick={() => setActiveTab(tab.key)}
                  className={cn(
                    "w-full flex items-center gap-3 px-4 py-3 text-left rounded-lg transition-colors",
                    activeTab === tab.key
                      ? "bg-primary-50 text-primary-700 border border-primary-200"
                      : "text-neutral-600 hover:text-neutral-900 hover:bg-neutral-50"
                  )}
                >
                  <IconComponent className="w-5 h-5" />
                  <span className="font-medium">{tab.label}</span>
                </button>
              );
            })}
          </nav>
        </div>

        {/* Content */}
        <div className="lg:col-span-3">
          <motion.div
            key={activeTab}
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.3 }}
          >
            {activeTab === "profile" && (
              <Card>
                <CardHeader>
                  <CardTitle>Profile Information</CardTitle>
                </CardHeader>
                <CardContent>
                  <form onSubmit={handleProfileUpdate} className="space-y-6">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                      <div>
                        <label className="block text-sm font-medium text-neutral-700 mb-2">
                          Email Address
                        </label>
                        <Input
                          type="email"
                          value={profileForm.email}
                          onChange={(e) =>
                            setProfileForm({
                              ...profileForm,
                              email: e.target.value,
                            })
                          }
                          disabled
                        />
                        <p className="text-xs text-neutral-500 mt-1">
                          Contact support to change your email address
                        </p>
                      </div>

                      <div>
                        <label className="block text-sm font-medium text-neutral-700 mb-2">
                          Full Name
                        </label>
                        <Input
                          type="text"
                          value={profileForm.full_name}
                          onChange={(e) =>
                            setProfileForm({
                              ...profileForm,
                              full_name: e.target.value,
                            })
                          }
                          placeholder="Enter your full name"
                        />
                      </div>

                      <div>
                        <label className="block text-sm font-medium text-neutral-700 mb-2">
                          Phone Number
                        </label>
                        <Input
                          type="tel"
                          value={profileForm.phone_number}
                          onChange={(e) =>
                            setProfileForm({
                              ...profileForm,
                              phone_number: e.target.value,
                            })
                          }
                          placeholder="+61 4XX XXX XXX"
                        />
                      </div>

                      <div>
                        <label className="block text-sm font-medium text-neutral-700 mb-2">
                          Australian State
                        </label>
                        <select
                          value={profileForm.australian_state}
                          onChange={(e) =>
                            setProfileForm({
                              ...profileForm,
                              australian_state: e.target
                                .value as AustralianState,
                            })
                          }
                          className="w-full px-3 py-2 rounded-lg border border-neutral-200 focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                        >
                          {australianStates.map((state) => (
                            <option key={state} value={state}>
                              {state}
                            </option>
                          ))}
                        </select>
                      </div>

                      <div className="md:col-span-2">
                        <label className="block text-sm font-medium text-neutral-700 mb-2">
                          Organization
                        </label>
                        <Input
                          type="text"
                          value={profileForm.organization}
                          onChange={(e) =>
                            setProfileForm({
                              ...profileForm,
                              organization: e.target.value,
                            })
                          }
                          placeholder="Your company or organization"
                        />
                      </div>
                    </div>

                    <div className="flex justify-end">
                      <Button
                        type="submit"
                        variant="primary"
                        leftIcon={<Save className="w-4 h-4" />}
                      >
                        Save Changes
                      </Button>
                    </div>
                  </form>
                </CardContent>
              </Card>
            )}

            {activeTab === "notifications" && (
              <Card>
                <CardHeader>
                  <CardTitle>Notification Preferences</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-6">
                    <div className="space-y-4">
                      <h3 className="text-lg font-medium text-neutral-900">
                        Email Notifications
                      </h3>

                      {Object.entries({
                        analysis_complete: "Analysis Complete",
                        weekly_summary: "Weekly Summary",
                        security_alerts: "Security Alerts",
                        product_updates: "Product Updates",
                        marketing_emails: "Marketing Emails",
                      }).map(([key, label]) => (
                        <div
                          key={key}
                          className="flex items-center justify-between py-3 border-b border-neutral-100 last:border-b-0"
                        >
                          <div>
                            <div className="font-medium text-neutral-900">
                              {label}
                            </div>
                            <div className="text-sm text-neutral-500">
                              {key === "analysis_complete" &&
                                "Get notified when your contract analysis is complete"}
                              {key === "weekly_summary" &&
                                "Weekly summary of your analysis activity"}
                              {key === "security_alerts" &&
                                "Important security and account alerts"}
                              {key === "product_updates" &&
                                "New features and product announcements"}
                              {key === "marketing_emails" &&
                                "Tips, case studies, and promotional content"}
                            </div>
                          </div>
                          <label className="relative inline-flex items-center cursor-pointer">
                            <input
                              type="checkbox"
                              checked={
                                notificationPrefs[
                                  key as keyof typeof notificationPrefs
                                ]
                              }
                              onChange={(e) =>
                                setNotificationPrefs({
                                  ...notificationPrefs,
                                  [key]: e.target.checked,
                                })
                              }
                              className="sr-only peer"
                            />
                            <div className="w-11 h-6 bg-neutral-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-primary-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-neutral-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary-600"></div>
                          </label>
                        </div>
                      ))}
                    </div>

                    <div className="flex justify-end">
                      <Button
                        onClick={handleNotificationUpdate}
                        variant="primary"
                        leftIcon={<Save className="w-4 h-4" />}
                      >
                        Save Preferences
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            )}

            {activeTab === "security" && (
              <div className="space-y-6">
                <Card>
                  <CardHeader>
                    <CardTitle>Change Password</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <form onSubmit={handlePasswordChange} className="space-y-6">
                      <div>
                        <label className="block text-sm font-medium text-neutral-700 mb-2">
                          Current Password
                        </label>
                        <div className="relative">
                          <Input
                            type={showCurrentPassword ? "text" : "password"}
                            value={passwordForm.current_password}
                            onChange={(e) =>
                              setPasswordForm({
                                ...passwordForm,
                                current_password: e.target.value,
                              })
                            }
                            placeholder="Enter current password"
                          />
                          <button
                            type="button"
                            onClick={() =>
                              setShowCurrentPassword(!showCurrentPassword)
                            }
                            className="absolute right-3 top-1/2 transform -translate-y-1/2 text-neutral-400 hover:text-neutral-600"
                          >
                            {showCurrentPassword ? (
                              <EyeOff className="w-4 h-4" />
                            ) : (
                              <Eye className="w-4 h-4" />
                            )}
                          </button>
                        </div>
                      </div>

                      <div>
                        <label className="block text-sm font-medium text-neutral-700 mb-2">
                          New Password
                        </label>
                        <div className="relative">
                          <Input
                            type={showNewPassword ? "text" : "password"}
                            value={passwordForm.new_password}
                            onChange={(e) =>
                              setPasswordForm({
                                ...passwordForm,
                                new_password: e.target.value,
                              })
                            }
                            placeholder="Enter new password"
                          />
                          <button
                            type="button"
                            onClick={() => setShowNewPassword(!showNewPassword)}
                            className="absolute right-3 top-1/2 transform -translate-y-1/2 text-neutral-400 hover:text-neutral-600"
                          >
                            {showNewPassword ? (
                              <EyeOff className="w-4 h-4" />
                            ) : (
                              <Eye className="w-4 h-4" />
                            )}
                          </button>
                        </div>
                      </div>

                      <div>
                        <label className="block text-sm font-medium text-neutral-700 mb-2">
                          Confirm New Password
                        </label>
                        <div className="relative">
                          <Input
                            type={showConfirmPassword ? "text" : "password"}
                            value={passwordForm.confirm_password}
                            onChange={(e) =>
                              setPasswordForm({
                                ...passwordForm,
                                confirm_password: e.target.value,
                              })
                            }
                            placeholder="Confirm new password"
                          />
                          <button
                            type="button"
                            onClick={() =>
                              setShowConfirmPassword(!showConfirmPassword)
                            }
                            className="absolute right-3 top-1/2 transform -translate-y-1/2 text-neutral-400 hover:text-neutral-600"
                          >
                            {showConfirmPassword ? (
                              <EyeOff className="w-4 h-4" />
                            ) : (
                              <Eye className="w-4 h-4" />
                            )}
                          </button>
                        </div>
                      </div>

                      <div className="flex justify-end">
                        <Button
                          type="submit"
                          variant="primary"
                          leftIcon={<Key className="w-4 h-4" />}
                        >
                          Update Password
                        </Button>
                      </div>
                    </form>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <CardTitle>Account Security</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-4">
                      <div className="flex items-center justify-between py-3 border-b border-neutral-100">
                        <div>
                          <div className="font-medium text-neutral-900">
                            Two-Factor Authentication
                          </div>
                          <div className="text-sm text-neutral-500">
                            Add an extra layer of security to your account
                          </div>
                        </div>
                        <Button variant="outline" size="sm">
                          Enable
                        </Button>
                      </div>

                      <div className="flex items-center justify-between py-3 border-b border-neutral-100">
                        <div>
                          <div className="font-medium text-neutral-900">
                            Active Sessions
                          </div>
                          <div className="text-sm text-neutral-500">
                            Manage your active login sessions
                          </div>
                        </div>
                        <Button variant="outline" size="sm">
                          View Sessions
                        </Button>
                      </div>

                      <div className="flex items-center justify-between py-3">
                        <div>
                          <div className="font-medium text-neutral-900">
                            Download Account Data
                          </div>
                          <div className="text-sm text-neutral-500">
                            Export all your account data and analyses
                          </div>
                        </div>
                        <Button variant="outline" size="sm">
                          Download
                        </Button>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </div>
            )}

            {activeTab === "billing" && (
              <div className="space-y-6">
                <Card>
                  <CardHeader>
                    <CardTitle>Current Plan</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="flex items-center justify-between">
                      <div>
                        <div className="font-semibold text-lg text-neutral-900 capitalize">
                          {user?.subscription_status || "Free"} Plan
                        </div>
                        <div className="text-neutral-500">
                          {user?.credits_remaining} credits remaining
                        </div>
                      </div>
                      <Button variant="primary">Upgrade Plan</Button>
                    </div>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <CardTitle>Usage Statistics</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                      <div className="text-center">
                        <div className="text-2xl font-bold text-primary-600">
                          24
                        </div>
                        <div className="text-sm text-neutral-500">
                          Analyses This Month
                        </div>
                      </div>
                      <div className="text-center">
                        <div className="text-2xl font-bold text-success-600">
                          96
                        </div>
                        <div className="text-sm text-neutral-500">
                          Credits Used
                        </div>
                      </div>
                      <div className="text-center">
                        <div className="text-2xl font-bold text-warning-600">
                          4
                        </div>
                        <div className="text-sm text-neutral-500">
                          Credits Remaining
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <CardTitle>Billing History</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="text-center py-8">
                      <CreditCard className="w-12 h-12 text-neutral-400 mx-auto mb-4" />
                      <p className="text-neutral-500">
                        No billing history available
                      </p>
                    </div>
                  </CardContent>
                </Card>
              </div>
            )}

            {activeTab === "appearance" && (
              <div className="space-y-6">
                <Card>
                  <CardHeader>
                    <CardTitle>Theme</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div
                      className="grid grid-cols-1 md:grid-cols-3 gap-4"
                      role="group"
                      aria-label="Theme"
                    >
                      <button
                        type="button"
                        onClick={() => setTheme("light")}
                        aria-pressed={theme === "light"}
                        className={cn(
                          "p-4 rounded-lg border",
                          theme === "light"
                            ? "border-primary-400 bg-primary-50"
                            : "border-neutral-200 hover:bg-neutral-50"
                        )}
                      >
                        <div className="flex items-center gap-3">
                          <Sun className="w-5 h-5" />
                          <div className="text-left">
                            <div className="font-medium">Light</div>
                            <div className="text-xs text-neutral-500">
                              Bright backgrounds
                            </div>
                          </div>
                        </div>
                      </button>
                      <button
                        type="button"
                        onClick={() => setTheme("dark")}
                        aria-pressed={theme === "dark"}
                        className={cn(
                          "p-4 rounded-lg border",
                          theme === "dark"
                            ? "border-primary-400 bg-primary-50"
                            : "border-neutral-200 hover:bg-neutral-50"
                        )}
                      >
                        <div className="flex items-center gap-3">
                          <Moon className="w-5 h-5" />
                          <div className="text-left">
                            <div className="font-medium">Dark</div>
                            <div className="text-xs text-neutral-500">
                              Dimmed, high-contrast
                            </div>
                          </div>
                        </div>
                      </button>
                      <button
                        type="button"
                        onClick={() => setTheme("system")}
                        aria-pressed={theme === "system"}
                        className={cn(
                          "p-4 rounded-lg border",
                          theme === "system"
                            ? "border-primary-400 bg-primary-50"
                            : "border-neutral-200 hover:bg-neutral-50"
                        )}
                      >
                        <div className="flex items-center gap-3">
                          <Monitor className="w-5 h-5" />
                          <div className="text-left">
                            <div className="font-medium">System</div>
                            <div className="text-xs text-neutral-500">
                              Follow OS setting
                            </div>
                          </div>
                        </div>
                      </button>
                    </div>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <CardTitle>Preview</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div
                      className={cn(
                        "rounded-lg p-6 border",
                        effectiveTheme === "dark"
                          ? "bg-neutral-900 text-neutral-100 border-neutral-700"
                          : "bg-white text-neutral-900 border-neutral-200"
                      )}
                    >
                      <div className="font-semibold mb-2">
                        {effectiveTheme === "dark" ? "Dark Mode" : "Light Mode"}{" "}
                        Preview
                      </div>
                      <p className="text-sm mb-4">
                        This area previews basic UI colors and text contrast for
                        the selected theme.
                      </p>
                      <div className="flex gap-3">
                        <Button variant="primary">Primary</Button>
                        <Button variant="outline">Outline</Button>
                        <Button variant="ghost">Ghost</Button>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </div>
            )}
          </motion.div>
        </div>
      </div>
    </div>
  );
};
export default SettingsPage;
