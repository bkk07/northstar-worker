import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

// shadcn-style `cn` helper shared by all features.
export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}
