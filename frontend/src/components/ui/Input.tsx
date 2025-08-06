import React from "react";
import { cn } from "@/utils";
import { AlertCircle, Eye, EyeOff } from "lucide-react";

interface InputProps extends Omit<React.InputHTMLAttributes<HTMLInputElement>, 'size'> {
  label?: string;
  error?: string;
  helpText?: string;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
  showPasswordToggle?: boolean;
  containerClassName?: string;
  size?: "sm" | "md" | "lg";
}

const Input = React.forwardRef<HTMLInputElement, InputProps>(
  (
    {
      className,
      containerClassName,
      label,
      error,
      helpText,
      leftIcon,
      rightIcon,
      showPasswordToggle = false,
      type = "text",
      size = "md",
      id,
      required,
      disabled,
      ...props
    },
    ref
  ) => {
    const [showPassword, setShowPassword] = React.useState(false);
    const [currentType, setCurrentType] = React.useState(type);

    const inputId = id || `input-${Date.now()}`;
    const hasError = Boolean(error);

    React.useEffect(() => {
      if (type === "password" && showPasswordToggle) {
        setCurrentType(showPassword ? "text" : "password");
      } else {
        setCurrentType(type);
      }
    }, [type, showPassword, showPasswordToggle]);

    const sizeClasses = {
      sm: "h-8 px-3 py-1.5 text-sm",
      md: "h-10 px-3 py-2.5 text-sm",
      lg: "h-12 px-4 py-3 text-base",
    };

    const baseClasses = [
      "block w-full rounded-lg border-0",
      sizeClasses[size],
      "text-neutral-900 shadow-sm ring-1 ring-inset",
      "placeholder:text-neutral-400",
      "focus:ring-2 focus:ring-inset",
      "transition-all duration-200",
      disabled &&
        "cursor-not-allowed opacity-50 bg-neutral-50 text-neutral-500",
    ]
      .filter(Boolean)
      .join(" ");

    const stateClasses = hasError
      ? "ring-red-300 focus:ring-red-500 border-red-500"
      : "ring-neutral-300 focus:ring-primary-500";

    const paddingClasses = cn(
      leftIcon && "pl-10",
      (rightIcon || (showPasswordToggle && type === "password")) && "pr-10"
    );

    return (
      <div className={cn("space-y-1", containerClassName)}>
        {label && (
          <label
            htmlFor={inputId}
            className="block text-sm font-medium text-neutral-700"
          >
            {label}
            {required && " *"}
          </label>
        )}

        <div className="relative">
          {leftIcon && (
            <div className="absolute inset-y-0 left-0 flex items-center pl-3 pointer-events-none">
              <span className="text-neutral-400" aria-hidden="true">
                {leftIcon}
              </span>
            </div>
          )}

          <input
            type={currentType}
            id={inputId}
            className={cn(baseClasses, stateClasses, paddingClasses, className)}
            ref={ref}
            required={required}
            disabled={disabled}
            aria-invalid={hasError}
            aria-describedby={
              error
                ? `${inputId}-error`
                : helpText
                ? `${inputId}-help`
                : undefined
            }
            {...props}
          />

          {(rightIcon || (showPasswordToggle && type === "password")) && (
            <div className="absolute inset-y-0 right-0 flex items-center pr-3">
              {showPasswordToggle && type === "password" ? (
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="text-neutral-400 hover:text-neutral-600 focus:outline-none"
                  aria-label={showPassword ? "Hide password" : "Show password"}
                >
                  {showPassword ? (
                    <EyeOff className="w-5 h-5" />
                  ) : (
                    <Eye className="w-5 h-5" />
                  )}
                </button>
              ) : (
                <span className="text-neutral-400" aria-hidden="true">
                  {rightIcon}
                </span>
              )}
            </div>
          )}
        </div>

        {error && (
          <div
            id={`${inputId}-error`}
            className="flex items-center gap-1.5 text-sm"
            role="alert"
          >
            <AlertCircle className="w-4 h-4 text-red-600" aria-hidden="true" />
            <span className="text-red-600">{error}</span>
          </div>
        )}

        {helpText && !error && (
          <p id={`${inputId}-help`} className="text-sm text-neutral-600">
            {helpText}
          </p>
        )}
      </div>
    );
  }
);

Input.displayName = "Input";

// Export both named and default for compatibility
export { Input };
export default Input;
