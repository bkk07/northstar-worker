import { Inbox, type LucideIcon } from "lucide-react";

export function EmptyState({
  title,
  desc,
  action,
  icon: Icon = Inbox,
}: {
  title: string;
  desc?: string;
  action?: React.ReactNode;
  icon?: LucideIcon;
}) {
  return (
    <div className="flex flex-col items-center justify-center rounded-2xl border border-dashed border-slate-300 bg-slate-50/60 px-6 py-10 text-center">
      <span className="flex h-10 w-10 items-center justify-center rounded-xl border border-slate-200 bg-white shadow-sm">
        <Icon aria-hidden className="h-5 w-5 text-slate-400" />
      </span>
      <p className="mt-3 text-sm font-semibold tracking-tight text-slate-900">{title}</p>
      {desc && <p className="mt-1 max-w-sm text-[13px] leading-5 text-slate-500">{desc}</p>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}
