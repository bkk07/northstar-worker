/** Paise (API money unit) → `₹1,299` display. */
export function formatPaise(paise: number): string {
  return `₹${Math.floor(paise / 100).toLocaleString("en-IN")}`;
}
