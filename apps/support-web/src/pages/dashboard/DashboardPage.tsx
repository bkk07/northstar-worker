import { Card, Badge, EmptyState } from "@/components/ui";

// Phase 1 dashboard shell. Real counts/filters arrive Phase 6.
export function DashboardPage() {
  const cards = [
    { label: "Open", value: "—" },
    { label: "In progress", value: "—" },
    { label: "Waiting", value: "—" },
    { label: "Resolved", value: "—" },
  ];
  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <h1 className="sp-title">Dashboard</h1>
        <Badge>Phase 6 wires live data</Badge>
      </div>
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        {cards.map((c) => (
          <Card key={c.label}>
            <p className="sp-muted">{c.label}</p>
            <p className="text-2xl font-bold">{c.value}</p>
          </Card>
        ))}
      </div>
      <Card>
        <EmptyState
          title="No tickets yet"
          hint="Ticket queue, search, filters, and status tabs arrive in Phase 6."
        />
      </Card>
    </div>
  );
}
