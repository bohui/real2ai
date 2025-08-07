import React from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Link, useNavigate } from "react-router-dom";
import { Mail, Lock, AlertCircle } from "lucide-react";
import { motion } from "framer-motion";

import Button from "@/components/ui/Button";
import Input from "@/components/ui/Input";
import Select from "@/components/ui/Select";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from "@/components/ui/Card";
import { useAuthStore } from "@/store/authStore";
import { useUIStore } from "@/store/uiStore";
import { UserRegistrationRequest } from "@/types";
import { australianStates } from "@/utils";

const registerSchema = z
  .object({
    email: z
      .string()
      .min(1, "Email is required")
      .email("Please enter a valid email address"),
    password: z
      .string()
      .min(8, "Password must be at least 8 characters")
      .regex(/[a-z]/, "Password must contain at least one lowercase letter")
      .regex(/[A-Z]/, "Password must contain at least one uppercase letter")
      .regex(/[0-9]/, "Password must contain at least one number"),
    confirmPassword: z.string().min(1, "Please confirm your password"),
    australian_state: z.enum([
      "NSW",
      "VIC",
      "QLD",
      "SA",
      "WA",
      "TAS",
      "NT",
      "ACT",
    ]),
    user_type: z.enum(["buyer", "investor", "agent"]),
    terms: z.boolean().refine((val) => val === true, {
      message: "You must agree to the terms and conditions",
    }),
  })
  .refine((data) => data.password === data.confirmPassword, {
    message: "Passwords don't match",
    path: ["confirmPassword"],
  });

type RegisterFormData = z.infer<typeof registerSchema>;

interface RegisterFormProps {
  onSuccess?: () => void;
  redirectTo?: string;
}

const RegisterForm: React.FC<RegisterFormProps> = ({
  onSuccess,
  redirectTo = "/dashboard",
}) => {
  const { register: registerUser, isLoading, error } = useAuthStore();
  const { addNotification } = useUIStore();
  const navigate = useNavigate();

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
    watch,
  } = useForm<RegisterFormData>({
    resolver: zodResolver(registerSchema),
    mode: "onBlur",
    defaultValues: {
      australian_state: "NSW",
      user_type: "buyer",
    },
  });

  const password = watch("password");

  const onSubmit = async (data: RegisterFormData) => {
    try {
      const { confirmPassword, terms, ...registrationData } = data;
      await registerUser(registrationData as UserRegistrationRequest);

      addNotification({
        type: "success",
        title: "Welcome to Real2.AI!",
        message: "Your account has been created successfully.",
      });

      if (onSuccess) {
        onSuccess();
      } else {
        navigate(redirectTo);
      }
    } catch (err) {
      // Error is already handled in the store
      addNotification({
        type: "error",
        title: "Registration failed",
        message: "Please check your information and try again.",
      });
    }
  };

  const isProcessing = isLoading || isSubmitting;

  // Password strength indicator
  const getPasswordStrength = (password: string) => {
    if (!password) return { score: 0, label: "", color: "" };

    let score = 0;
    if (password.length >= 8) score++;
    if (/[a-z]/.test(password)) score++;
    if (/[A-Z]/.test(password)) score++;
    if (/[0-9]/.test(password)) score++;
    if (/[^a-zA-Z0-9]/.test(password)) score++;

    const labels = ["Very Weak", "Weak", "Fair", "Good", "Strong"];
    const colors = [
      "bg-danger-500",
      "bg-warning-500",
      "bg-warning-400",
      "bg-primary-500",
      "bg-success-500",
    ];

    return {
      score,
      label: labels[Math.min(score, 4)],
      color: colors[Math.min(score, 4)],
      percentage: (score / 5) * 100,
    };
  };

  const passwordStrength = getPasswordStrength(password || "");

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
      className="w-full max-w-md mx-auto"
    >
      <Card variant="elevated" padding="none">
        <CardHeader padding="lg">
          <div className="text-center mb-2">
            <div className="inline-flex items-center justify-center w-16 h-16 bg-primary-100 rounded-full mb-4">
              <span className="text-2xl font-bold text-primary-600">R2</span>
            </div>
          </div>
          <CardTitle className="text-center text-2xl">
            Create your account
          </CardTitle>
          <CardDescription className="text-center">
            Join Real2.AI and start analyzing Australian property contracts with
            AI
          </CardDescription>
        </CardHeader>

        <CardContent padding="lg">
          {error && (
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              className="mb-6 p-4 bg-danger-50 border border-danger-200 rounded-lg"
            >
              <div className="flex items-center gap-2 text-danger-700">
                <AlertCircle className="w-5 h-5" />
                <span className="text-sm font-medium">{error}</span>
              </div>
            </motion.div>
          )}

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
            <Input
              label="Email address"
              type="email"
              autoComplete="email"
              placeholder="Enter your email"
              leftIcon={<Mail className="w-5 h-5" />}
              error={errors.email?.message}
              disabled={isProcessing}
              {...register("email")}
            />

            <div className="grid grid-cols-2 gap-4">
              <Select
                label="State"
                error={errors.australian_state?.message}
                disabled={isProcessing}
                {...register("australian_state")}
              >
                {australianStates.map((state) => (
                  <option key={state.value} value={state.value}>
                    {state.label}
                  </option>
                ))}
              </Select>

              <Select
                label="I am a"
                error={errors.user_type?.message}
                disabled={isProcessing}
                {...register("user_type")}
              >
                <option value="buyer">Property Buyer</option>
                <option value="investor">Property Investor</option>
                <option value="agent">Real Estate Agent</option>
              </Select>
            </div>

            <div className="space-y-4">
              <Input
                label="Password"
                type="password"
                autoComplete="new-password"
                placeholder="Create a strong password"
                leftIcon={<Lock className="w-5 h-5" />}
                showPasswordToggle
                error={errors.password?.message}
                disabled={isProcessing}
                {...register("password")}
              />

              {password && (
                <div className="space-y-2">
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-neutral-600">Password strength</span>
                    <span
                      className={`font-medium ${
                        passwordStrength.score >= 4
                          ? "text-success-600"
                          : passwordStrength.score >= 3
                          ? "text-primary-600"
                          : passwordStrength.score >= 2
                          ? "text-warning-600"
                          : "text-danger-600"
                      }`}
                    >
                      {passwordStrength.label}
                    </span>
                  </div>
                  <div className="w-full bg-neutral-200 rounded-full h-1.5">
                    <div
                      className={`h-1.5 rounded-full transition-all duration-300 ${passwordStrength.color}`}
                      style={{ width: `${passwordStrength.percentage}%` }}
                    />
                  </div>
                </div>
              )}

              <Input
                label="Confirm password"
                type="password"
                autoComplete="new-password"
                placeholder="Confirm your password"
                leftIcon={<Lock className="w-5 h-5" />}
                showPasswordToggle
                error={errors.confirmPassword?.message}
                disabled={isProcessing}
                {...register("confirmPassword")}
              />
            </div>

            <div>
              <label className="flex items-start gap-3">
                <input
                  type="checkbox"
                  className="mt-0.5 rounded border-neutral-300 text-primary-600 focus:ring-primary-500"
                  disabled={isProcessing}
                  {...register("terms")}
                />
                <span className="text-sm text-neutral-600">
                  I agree to the{" "}
                  <Link
                    to="/terms"
                    className="text-primary-600 hover:text-primary-700 font-medium"
                  >
                    Terms of Service
                  </Link>{" "}
                  and{" "}
                  <Link
                    to="/privacy"
                    className="text-primary-600 hover:text-primary-700 font-medium"
                  >
                    Privacy Policy
                  </Link>
                </span>
              </label>
              {errors.terms && (
                <p className="mt-1 text-sm text-danger-600">
                  {errors.terms.message}
                </p>
              )}
            </div>

            <Button
              type="submit"
              variant="primary"
              size="lg"
              fullWidth
              loading={isProcessing}
              loadingText="Creating account..."
            >
              Create account
            </Button>
          </form>

          <div className="mt-6 text-center">
            <p className="text-sm text-neutral-600">
              Already have an account?{" "}
              <Link
                to="/login"
                className="font-medium text-primary-600 hover:text-primary-700"
              >
                Sign in here
              </Link>
            </p>
          </div>
        </CardContent>
      </Card>

      <div className="mt-8 text-center text-xs text-neutral-500">
        <p>
          🔒 Your information is secure and will only be used for contract
          analysis
        </p>
      </div>
    </motion.div>
  );
};

export default RegisterForm;
