import React from "react";
import { cn } from "@/utils";
import { Loader2 } from "lucide-react";

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?:
    | "primary"
    | "secondary"
    | "destructive"
    | "outline"
    | "ghost"
    | "success"
    | "warning"
    | "premium";
  size?: "xs" | "sm" | "md" | "lg" | "xl";
  loading?: boolean;
  loadingText?: string;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
  fullWidth?: boolean;
  elevated?: boolean;
  rounded?: boolean;
  gradient?: boolean;
  as?: React.ElementType;
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      className,
      variant = "primary",
      size = "md",
      loading = false,
      loadingText,
      leftIcon,
      rightIcon,
      fullWidth = false,
      elevated = false,
      rounded = false,
      gradient = false,
      disabled,
      children,
      as: Component = "button",
      ...props
    },
    ref
  ) => {
    const baseClasses = [
      "inline-flex items-center justify-center",
      "font-medium transition-all duration-200 ease-in-out",
      "focus:outline-none focus:ring-2 focus:ring-offset-2",
      "disabled:opacity-50 disabled:cursor-not-allowed",
      "select-none relative overflow-hidden",
      "transform hover:scale-[1.01] active:scale-95 motion-reduce:transform-none motion-reduce:transition-none",
      "whitespace-nowrap",
    ].join(" ");

    const variantClasses = {
      primary: [
        gradient
          ? "bg-gradient-to-r from-primary-600 to-primary-700"
          : "bg-primary-600",
        "text-white shadow-soft",
        "hover:from-primary-700 hover:to-primary-800 hover:shadow-primary",
        "focus:ring-primary-500/50",
        "active:from-primary-800 active:to-primary-900",
      ].join(" "),
      secondary: [
        "bg-neutral-200 text-neutral-900",
        "hover:bg-neutral-300",
        "focus:ring-neutral-500/50",
        "active:bg-neutral-400",
      ].join(" "),
      destructive: [
        "bg-red-600 text-white",
        "hover:bg-red-700",
        "focus:ring-red-500/50",
        "active:bg-red-800",
      ].join(" "),
      success: [
        gradient
          ? "bg-gradient-to-r from-success-500 to-success-600"
          : "bg-success-500",
        "text-white shadow-soft",
        "hover:from-success-600 hover:to-success-700 hover:shadow-success",
        "focus:ring-success-500/50",
        "active:from-success-700 active:to-success-800",
      ].join(" "),
      warning: [
        gradient
          ? "bg-gradient-to-r from-warning-500 to-warning-600"
          : "bg-warning-500",
        "text-white shadow-soft",
        "hover:from-warning-600 hover:to-warning-700 hover:shadow-warning",
        "focus:ring-warning-500/50",
        "active:from-warning-700 active:to-warning-800",
      ].join(" "),
      premium: [
        "bg-gradient-to-r from-accent-500 via-primary-600 to-accent-500",
        "text-white shadow-large",
        "hover:from-accent-600 hover:via-primary-700 hover:to-accent-600",
        "focus:ring-primary-500/50 animate-glow",
        "active:from-accent-700 active:via-primary-800 active:to-accent-700",
      ].join(" "),
      outline: [
        "border border-neutral-300 bg-white text-neutral-700 shadow-soft",
        "hover:border-primary-400 hover:bg-primary-50 hover:text-primary-700",
        "focus:ring-primary-500/50 focus:border-primary-500",
        "active:bg-primary-100 active:border-primary-600",
      ].join(" "),
      ghost: [
        "text-neutral-700 bg-transparent",
        "hover:bg-neutral-100 hover:text-neutral-900",
        "focus:ring-primary-500/30 focus:bg-neutral-50",
        "active:bg-neutral-200",
      ].join(" "),
    };

    const sizeClasses = {
      xs: `h-7 px-2.5 py-1.5 text-xs gap-1 ${
        rounded ? "rounded-full" : "rounded-md"
      }`,
      sm: `h-8 px-3 py-2 text-sm gap-1.5 ${
        rounded ? "rounded-full" : "rounded-lg"
      }`,
      md: `h-10 px-4 py-2.5 text-sm gap-2 ${
        rounded ? "rounded-full" : "rounded-lg"
      }`,
      lg: `h-12 px-6 py-3 text-base gap-2.5 ${
        rounded ? "rounded-full" : "rounded-xl"
      }`,
      xl: `h-14 px-8 py-4 text-lg gap-3 ${
        rounded ? "rounded-full" : "rounded-xl"
      }`,
    };

    const isDisabled = disabled || loading;

    return (
      <Component
        className={cn(
          baseClasses,
          variantClasses[variant],
          sizeClasses[size],
          fullWidth && "w-full",
          elevated && "shadow-large hover:shadow-xl",
          className
        )}
        disabled={isDisabled}
        ref={ref}
        aria-disabled={isDisabled}
        onClick={loading ? undefined : props.onClick}
        {...props}
      >
        {loading && (
          <Loader2 className="w-4 h-4 animate-spin" aria-hidden="true" />
        )}
        {!loading && leftIcon && (
          <span className="inline-flex" aria-hidden="true">
            {leftIcon}
          </span>
        )}
        {loading && loadingText ? (
          <span className="whitespace-nowrap">{loadingText}</span>
        ) : (
          children
        )}
        {!loading && rightIcon && (
          <span className="inline-flex" aria-hidden="true">
            {rightIcon}
          </span>
        )}
      </Component>
    );
  }
);

Button.displayName = "Button";

// Export both named and default for compatibility
export { Button };
export default Button;
