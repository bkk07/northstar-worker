import type { ButtonHTMLAttributes } from "react";
import { cn } from "@/shared/lib/utils";

// Minimal shadcn-style Button placeholder (full design system in later phases).
export function Button({ className, ...props }: ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      className={cn(
        "inline-flex items-center justify-center rounded-md px-4 py-2 text-sm font-medium",
        "bg-slate-900 text-white hover:bg-slate-700",
        className,
      )}
      {...props}
    />
  );
}
