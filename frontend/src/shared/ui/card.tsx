import { motion, useReducedMotion } from "framer-motion";
import type { ReactNode } from "react";
import { cn } from "@/shared/lib/utils";
import { snappyTransition } from "@/shared/ui/motion";

type CardProps = {
  className?: string;
  children: ReactNode;
  /** Disable the hover lift (e.g. large tables). Default lifts. */
  lift?: boolean;
};

/**
 * Support-console card: rounded-2xl, border, soft shadow, hover lift y:-2.
 * Motion is skipped when prefers-reduced-motion is set.
 */
export function Card({ className, children, lift = true }: CardProps) {
  const reduce = useReducedMotion();
  return (
    <motion.div
      className={cn("ns-card", className)}
      whileHover={lift && !reduce ? { y: -2 } : undefined}
      transition={snappyTransition}
    >
      {children}
    </motion.div>
  );
}

export function CardHeader({
  title,
  desc,
  actions,
}: {
  title: string;
  desc?: string;
  actions?: ReactNode;
}) {
  return (
    <div className="ns-card-header">
      <div>
        <h3 className="ns-card-title">{title}</h3>
        {desc && <p className="ns-card-sub">{desc}</p>}
      </div>
      {actions && <div className="flex shrink-0 items-center gap-2">{actions}</div>}
    </div>
  );
}

export function CardBody({ className, children }: { className?: string; children: ReactNode }) {
  return <div className={cn("ns-card-pad", className)}>{children}</div>;
}
