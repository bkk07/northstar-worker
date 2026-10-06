import { type ReactNode } from "react";
import { cn } from "@/lib/cn";

export function Button({
  children, variant = "primary", className, ...rest
}: {
  children: ReactNode; variant?: "primary" | "secondary" | "ghost" | "danger"; className?: string;
} & React.ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      className={cn(
        "sp-btn",
        variant === "primary" && "sp-btn-primary",
        variant === "secondary" && "sp-btn-secondary",
        variant === "ghost" && "sp-btn-ghost",
        variant === "danger" && "sp-btn-danger",
        className,
      )}
      {...rest}
    >
      {children}
    </button>
  );
}

export function Card({ children, className }: { children: ReactNode; className?: string }) {
  return <div className={cn("sp-card sp-card-pad", className)}>{children}</div>;
}

export function Input(props: React.InputHTMLAttributes<HTMLInputElement>) {
  return <input className="sp-input" {...props} />;
}

export function Badge({ children, tone = "info" }: { children: ReactNode; tone?: "info" | "ok" | "warn" | "bad" }) {
  return (
    <span className={cn("sp-badge", tone === "ok" && "sp-badge-ok", tone === "warn" && "sp-badge-warn", tone === "bad" && "sp-badge-bad", tone === "info" && "sp-badge-info")}>
      {children}
    </span>
  );
}

export function Spinner({ label = "Loading…" }: { label?: string }) {
  return (
    <div className="sp-center" role="status" aria-live="polite">
      <div className="sp-spinner" aria-hidden />
      <span className="sp-muted">{label}</span>
    </div>
  );
}

export function EmptyState({ title, hint, action }: { title: string; hint?: string; action?: ReactNode }) {
  return (
    <div className="sp-center">
      <p className="sp-title">{title}</p>
      {hint ? <p className="sp-muted">{hint}</p> : null}
      {action}
    </div>
  );
}

export function ErrorState({ title = "Something went wrong", hint = "Please try again.", onRetry }: { title?: string; hint?: string; onRetry?: () => void }) {
  return (
    <div className="sp-center" role="alert">
      <p className="sp-title">{title}</p>
      <p className="sp-muted">{hint}</p>
      {onRetry ? <Button variant="secondary" onClick={onRetry}>Retry</Button> : null}
    </div>
  );
}
