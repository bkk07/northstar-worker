import { StickyNote } from "lucide-react";
import type { ConsoleMessage } from "@/services/support-api";

function formatDate(iso: string): string {
  return new Date(iso).toLocaleString("en-IN", {
    day: "numeric",
    month: "short",
    hour: "numeric",
    minute: "2-digit",
  });
}

export function ConsoleBubble({ m }: { m: ConsoleMessage }) {
  if (m.sender_type === "SYSTEM") {
    return <p className="sp-muted mx-auto max-w-[90%] text-center text-xs">— {m.message}</p>;
  }
  if (m.is_internal) {
    return (
      <div className="rounded-xl border border-dashed border-amber-300 bg-amber-50 px-3.5 py-2.5 text-sm">
        <p className="mb-0.5 flex items-center gap-1 text-[11px] font-semibold uppercase tracking-wider text-amber-700">
          <StickyNote size={11} aria-hidden /> Internal note · staff only
        </p>
        <p className="whitespace-pre-wrap text-slate-800">{m.message}</p>
        <p className="mt-1 text-[11px] text-slate-400">{formatDate(m.created_at)}</p>
      </div>
    );
  }
  const staff = m.sender_type === "SUPPORT_AGENT";
  return (
    <div className={`flex ${staff ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[85%] rounded-2xl px-3.5 py-2.5 text-sm ${
          staff ? "rounded-br-md bg-indigo-600 text-white" : "rounded-bl-md bg-slate-100 text-slate-800"
        }`}
      >
        {!staff ? (
          <p className="mb-0.5 text-[11px] font-semibold uppercase tracking-wider opacity-70">
            {m.sender_type === "AI_AGENT" ? "AI assistant" : "Customer"}
          </p>
        ) : null}
        <p className="whitespace-pre-wrap">{m.message}</p>
        <p className={`mt-1 text-[11px] ${staff ? "text-indigo-200" : "text-slate-400"}`}>
          {formatDate(m.created_at)}
        </p>
      </div>
    </div>
  );
}
