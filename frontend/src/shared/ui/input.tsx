import { Search, type LucideIcon } from "lucide-react";
import type { InputHTMLAttributes } from "react";
import { cn } from "@/shared/lib/utils";

type InputProps = InputHTMLAttributes<HTMLInputElement> & {
  label?: string;
  hint?: string;
  error?: string;
  icon?: LucideIcon;
};

/** Labelled support-console input. Error path keeps role="alert". */
export function Input({ label, hint, error, icon: Icon = Search, id, className, ...props }: InputProps) {
  const inputId = id ?? props.name ?? "ns-input";
  const showIcon = props.type === "search" || Icon !== Search || props.placeholder;
  return (
    <div className={cn("w-full", className)}>
      {label && (
        <label htmlFor={inputId} className="ns-label">
          {label}
        </label>
      )}
      <div className="relative">
        {showIcon && props.type === "search" && (
          <Icon
            aria-hidden
            className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400"
          />
        )}
        <input
          id={inputId}
          aria-invalid={error ? true : undefined}
          aria-describedby={error ? `${inputId}-error` : hint ? `${inputId}-hint` : undefined}
          className={cn("ns-input", props.type === "search" && "pl-9", error && "border-red-400")}
          {...props}
        />
      </div>
      {hint && !error && (
        <p id={`${inputId}-hint`} className="mt-1 text-xs text-slate-500">
          {hint}
        </p>
      )}
      {error && (
        <p id={`${inputId}-error`} role="alert" className="mt-1 text-xs font-medium text-red-700">
          {error}
        </p>
      )}
    </div>
  );
}

export function Textarea({
  label,
  hint,
  className,
  id,
  ...props
}: React.TextareaHTMLAttributes<HTMLTextAreaElement> & { label?: string; hint?: string }) {
  const areaId = id ?? props.name ?? "ns-textarea";
  return (
    <div className={cn("w-full", className)}>
      {label && (
        <label htmlFor={areaId} className="ns-label">
          {label}
        </label>
      )}
      <textarea id={areaId} className="ns-input resize-y" {...props} />
      {hint && <p className="mt-1 text-xs text-slate-500">{hint}</p>}
    </div>
  );
}

export function Select({
  label,
  className,
  id,
  children,
  ...props
}: React.SelectHTMLAttributes<HTMLSelectElement> & { label?: string }) {
  const selectId = id ?? props.name ?? "ns-select";
  return (
    <div>
      {label && (
        <label htmlFor={selectId} className="ns-label">
          {label}
        </label>
      )}
      <select id={selectId} className={cn("ns-select", className)} {...props}>
        {children}
      </select>
    </div>
  );
}
