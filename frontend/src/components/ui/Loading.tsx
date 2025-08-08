import React from "react";
import { motion, useReducedMotion } from "framer-motion";
import { Loader2, FileText, Shield, TrendingUp } from "lucide-react";
import { cn } from "@/utils";

interface LoadingProps {
  variant?: "spinner" | "dots" | "pulse" | "skeleton" | "legal" | "analysis";
  size?: "sm" | "md" | "lg" | "xl";
  text?: string;
  className?: string;
  color?: "primary" | "secondary" | "trust" | "neutral";
}

const Loading: React.FC<LoadingProps> = ({
  variant = "spinner",
  size = "md",
  text,
  className,
  color = "primary",
}) => {
  const shouldReduceMotion = useReducedMotion();
  const sizeClasses = {
    sm: "w-4 h-4",
    md: "w-6 h-6",
    lg: "w-8 h-8",
    xl: "w-12 h-12",
  };

  const colorClasses = {
    primary: "text-primary-600",
    secondary: "text-secondary-600",
    trust: "text-trust-600",
    neutral: "text-neutral-600",
  };

  const textSizes = {
    sm: "text-xs",
    md: "text-sm",
    lg: "text-base",
    xl: "text-lg",
  };

  if (variant === "spinner") {
    return (
      <div className={cn("flex flex-col items-center gap-3", className)}>
        <Loader2
          className={cn(sizeClasses[size], colorClasses[color], "animate-spin")}
        />
        {text && (
          <p className={cn(textSizes[size], "text-neutral-600 font-medium")}>
            {text}
          </p>
        )}
      </div>
    );
  }

  if (variant === "dots") {
    return (
      <div className={cn("flex flex-col items-center gap-3", className)}>
        <div className="flex gap-1">
          {[0, 1, 2].map((i) => (
            <motion.div
              key={i}
              className={cn(
                "rounded-full",
                size === "sm" && "w-1.5 h-1.5",
                size === "md" && "w-2 h-2",
                size === "lg" && "w-2.5 h-2.5",
                size === "xl" && "w-3 h-3",
                colorClasses[color].replace("text-", "bg-")
              )}
              animate={
                shouldReduceMotion
                  ? undefined
                  : { scale: [1, 1.2, 1], opacity: [0.5, 1, 0.5] }
              }
              transition={
                shouldReduceMotion
                  ? undefined
                  : { duration: 1, repeat: Infinity, delay: i * 0.2 }
              }
            />
          ))}
        </div>
        {text && (
          <p className={cn(textSizes[size], "text-neutral-600 font-medium")}>
            {text}
          </p>
        )}
      </div>
    );
  }

  if (variant === "pulse") {
    return (
      <div className={cn("flex flex-col items-center gap-3", className)}>
        <motion.div
          className={cn(
            "rounded-full border-2",
            sizeClasses[size],
            colorClasses[color].replace("text-", "border-")
          )}
          animate={
            shouldReduceMotion
              ? undefined
              : { scale: [1, 1.1, 1], opacity: [1, 0.7, 1] }
          }
          transition={
            shouldReduceMotion ? undefined : { duration: 1.5, repeat: Infinity }
          }
        />
        {text && (
          <p className={cn(textSizes[size], "text-neutral-600 font-medium")}>
            {text}
          </p>
        )}
      </div>
    );
  }

  if (variant === "legal") {
    return (
      <div className={cn("flex flex-col items-center gap-4", className)}>
        <div className="relative">
          <motion.div
            className="w-16 h-16 bg-gradient-to-br from-trust-100 to-primary-100 rounded-full flex items-center justify-center"
            animate={shouldReduceMotion ? undefined : { scale: [1, 1.05, 1] }}
            transition={
              shouldReduceMotion ? undefined : { duration: 2, repeat: Infinity }
            }
          >
            <Shield className="w-8 h-8 text-trust-600" />
          </motion.div>
          <motion.div
            className="absolute inset-0 w-16 h-16 border-2 border-trust-300 rounded-full"
            animate={shouldReduceMotion ? undefined : { rotate: [0, 360] }}
            transition={
              shouldReduceMotion
                ? undefined
                : { duration: 3, repeat: Infinity, ease: "linear" }
            }
            style={{
              background:
                "conic-gradient(from 0deg, transparent, #8B5CF6, transparent)",
            }}
          />
        </div>
        {text && (
          <div className="text-center">
            <p className="text-lg font-semibold text-neutral-800 mb-1">
              {text}
            </p>
            <p className="text-sm text-neutral-500">
              Analyzing with Australian legal expertise
            </p>
          </div>
        )}
      </div>
    );
  }

  if (variant === "analysis") {
    const analysisSteps = [
      { icon: FileText, label: "Reading contract", delay: 0 },
      { icon: Shield, label: "Checking compliance", delay: 0.5 },
      { icon: TrendingUp, label: "Risk assessment", delay: 1 },
    ];

    return (
      <div className={cn("flex flex-col items-center gap-6", className)}>
        <div className="flex items-center gap-4">
          {analysisSteps.map((step, index) => (
            <motion.div
              key={index}
              className="flex flex-col items-center gap-2"
              initial={{ opacity: 0.3 }}
              animate={
                shouldReduceMotion ? undefined : { opacity: [0.3, 1, 0.3] }
              }
              transition={
                shouldReduceMotion
                  ? undefined
                  : { duration: 1.5, repeat: Infinity, delay: step.delay }
              }
            >
              <div
                className={cn(
                  "w-12 h-12 rounded-full flex items-center justify-center",
                  "bg-gradient-to-br from-primary-100 to-trust-100"
                )}
              >
                <step.icon className="w-6 h-6 text-primary-600" />
              </div>
              <span className="text-xs text-neutral-600 font-medium">
                {step.label}
              </span>
            </motion.div>
          ))}
        </div>
        {text && (
          <p className="text-base font-semibold text-neutral-800 text-center">
            {text}
          </p>
        )}
      </div>
    );
  }

  if (variant === "skeleton") {
    return (
      <div className={cn("space-y-3", className)}>
        {[...Array(3)].map((_, i) => (
          <motion.div
            key={i}
            className="h-4 bg-neutral-200 rounded"
            style={{
              width: `${Math.random() * 40 + 60}%`,
            }}
            animate={
              shouldReduceMotion ? undefined : { opacity: [0.5, 1, 0.5] }
            }
            transition={
              shouldReduceMotion
                ? undefined
                : { duration: 1.5, repeat: Infinity, delay: i * 0.2 }
            }
          />
        ))}
      </div>
    );
  }

  return null;
};

export default Loading;
