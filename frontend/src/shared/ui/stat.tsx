import { Card, CardBody } from "@/shared/ui/card";

export function Stat({
  label,
  value,
  hint,
  accent,
}: {
  label: string;
  value: string;
  hint?: string;
  accent?: "ok" | "warn" | "bad" | "info";
}) {
  const bar =
    accent === "ok"
      ? "bg-emerald-500"
      : accent === "warn"
        ? "bg-amber-500"
        : accent === "bad"
          ? "bg-red-500"
          : accent === "info"
            ? "bg-brand-500"
            : "bg-slate-300";
  return (
    <Card>
      <CardBody>
        <div className="flex items-center gap-2">
          <span aria-hidden className={`h-1.5 w-1.5 rounded-full ${bar}`} />
          <p className="text-xs font-medium uppercase tracking-wider text-slate-500">{label}</p>
        </div>
        <p className="mt-1.5 truncate text-2xl font-semibold tracking-tight text-slate-900">
          {value}
        </p>
        {hint && <p className="mt-0.5 truncate text-xs text-slate-500">{hint}</p>}
      </CardBody>
    </Card>
  );
}
