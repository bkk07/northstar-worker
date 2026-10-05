import { motion, useReducedMotion, type HTMLMotionProps } from "framer-motion";
import { cn } from "@/shared/lib/utils";
import { snappyTransition } from "@/shared/ui/motion";

type Variant = "primary" | "secondary" | "ghost" | "danger" | "success";
type Size = "md" | "sm";

const VARIANTS: Record<Variant, string> = {
  primary: "ns-btn ns-btn-primary",
  secondary: "ns-btn ns-btn-secondary",
  ghost: "ns-btn ns-btn-ghost",
  danger: "ns-btn ns-btn-danger",
  success: "ns-btn ns-btn-success",
};

type Props = Omit<HTMLMotionProps<"button">, "children"> & {
  variant?: Variant;
  size?: Size;
};

export function Button({ variant = "primary", size = "md", className, ...props }: Props) {
  const reduce = useReducedMotion();
  return (
    <motion.button
      // Tap: scale 0.97 (disabled when user prefers reduced motion).
      whileTap={reduce ? undefined : { scale: 0.97 }}
      transition={snappyTransition}
      className={cn(VARIANTS[variant], size === "sm" && "ns-btn-sm", className)}
      {...props}
    />
  );
}
