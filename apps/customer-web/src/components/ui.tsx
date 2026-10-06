import { type ReactNode } from "react";
import { cn } from "@/lib/cn";

export function Button({
  children,
  variant = "primary",
  className,
  ...rest
}: {
  children: ReactNode;
  variant?: "primary" | "secondary" | "ghost";
  className?: string;
} & React.ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      className={cn(
        "ns-btn",
        variant === "primary" && "ns-btn-primary",
        variant === "secondary" && "ns-btn-secondary",
        variant === "ghost" && "ns-btn-ghost",
        className,
      )}
      {...rest}
    >
      {children}
    </button>
  );
}

export function Card({ children, className }: { children: ReactNode; className?: string }) {
  return <div className={cn("ns-card ns-card-pad", className)}>{children}</div>;
}

export function Input(props: React.InputHTMLAttributes<HTMLInputElement>) {
  return <input className="ns-input" {...props} />;
}

export function Badge({ children, tone = "info" }: { children: ReactNode; tone?: "info" | "ok" | "warn" | "bad" }) {
  return <span className={cn("ns-badge", tone === "ok" && "ns-badge-ok", tone === "warn" && "ns-badge-warn", tone === "bad" && "ns-badge-bad", tone === "info" && "ns-badge-info")}>{children}</span>;
}

export function Spinner({ label = "Loading…" }: { label?: string }) {
  return (
    <div className="ns-center" role="status" aria-live="polite">
      <div className="ns-spinner" aria-hidden />
      <span className="ns-muted">{label}</span>
    </div>
  );
}

export function EmptyState({ title, hint, action }: { title: string; hint?: string; action?: ReactNode }) {
  return (
    <div className="ns-center ns-stack">
      <p className="ns-title">{title}</p>
      {hint ? <p className="ns-muted">{hint}</p> : null}
      {action}
    </div>
  );
}

export function ErrorState({ title = "Something went wrong", hint = "Please try again.", onRetry }: { title?: string; hint?: string; onRetry?: () => void }) {
  return (
    <div className="ns-center ns-stack" role="alert">
      <p className="ns-title">{title}</p>
      <p className="ns-muted">{hint}</p>
      {onRetry ? <Button variant="secondary" onClick={onRetry}>Retry</Button> : null}
    </div>
  );
}

export function Skeleton({ className }: { className?: string }) {
  return <div className={cn("ns-skeleton", className)} aria-hidden />;
}
