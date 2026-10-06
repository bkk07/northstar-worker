import { useQuery } from "@tanstack/react-query";
import { Package, ShieldCheck } from "lucide-react";
import { axiosClient } from "@/shared/api/axiosClient";
import { useTicket } from "@/features/shop/hooks/useShop";
import type { OrderRead } from "@/features/shop/types";
import { listApprovals } from "@/features/worker/api/workerApi";
import { Badge } from "@/shared/ui/badge";
import { Card, CardBody, CardHeader } from "@/shared/ui/card";
import { EmptyState } from "@/shared/ui/empty-state";
import { Skeleton } from "@/shared/ui/skeleton";
import { formatINR } from "@/shared/lib/format";
import { getProduct, listProducts } from "../api/catalogApi";

async function getOrderById(orderId: string): Promise<OrderRead> {
  const { data } = await axiosClient.get<OrderRead>(`/api/read/orders/${orderId}`);
  return data;
}

/**
 * Context rail: the selected ticket with its order, products, and the
 * policies governing them — plus anything waiting for a decision.
 * Everything here is quotable by the bot; decisions use the buttons.
 */
export function ContextPanel({
  ticketCode,
  deciding,
  onAsk,
  onSolve,
  onDecide,
}: {
  ticketCode: string | null;
  deciding: string | null;
  onAsk: (text: string) => void;
  onSolve: (code: string) => void;
  onDecide: (approvalId: string, decision: "approve" | "reject") => void;
}) {
  const ticket = useTicket(ticketCode ?? undefined);
  const orderId = ticket.data?.order_id ?? null;
  const order = useQuery({
    queryKey: ["read", "order", orderId],
    queryFn: () => getOrderById(orderId ?? ""),
    enabled: !!orderId,
  });
  const firstSku = order.data?.items[0]?.sku;
  const product = useQuery({
    queryKey: ["catalog", "product", firstSku],
    queryFn: () => getProduct(firstSku ?? ""),
    enabled: !!firstSku,
  });
  const catalog = useQuery({
    queryKey: ["catalog", "products"],
    queryFn: listProducts,
    enabled: !ticketCode,
    staleTime: 60_000,
  });
  const approvals = useQuery({
    queryKey: ["worker", "approvals"],
    queryFn: listApprovals,
    refetchInterval: 5000,
  });
  const pending = (approvals.data ?? []).filter((a) => a.status === "pending").slice(0, 3);

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-4 overflow-y-auto pr-0.5">
      {pending.length > 0 && (
        <Card lift={false}>
          <CardHeader title="Needs your decision" desc={`${pending.length} waiting`} />
          <CardBody className="flex flex-col gap-2">
            {pending.map((approval) => (
              <div key={approval.id} className="rounded-xl bg-amber-50 p-2.5">
                <p className="text-[13px] font-medium leading-5 text-slate-900">
                  Task {approval.task_id.slice(0, 8)} · {approval.requested_action}
                </p>
                <p className="mt-0.5 line-clamp-2 text-xs leading-5 text-slate-600">
                  {approval.reason}
                </p>
                <div className="mt-2 flex gap-2">
                  <button
                    type="button"
                    disabled={deciding === approval.id}
                    onClick={() => onDecide(approval.id, "approve")}
                    className="ns-btn ns-btn-primary ns-btn-sm"
                  >
                    {deciding === approval.id ? "Working…" : "Approve"}
                  </button>
                  <button
                    type="button"
                    disabled={deciding === approval.id}
                    onClick={() => onDecide(approval.id, "reject")}
                    className="ns-btn ns-btn-secondary ns-btn-sm"
                  >
                    Reject
                  </button>
                </div>
              </div>
            ))}
          </CardBody>
        </Card>
      )}

      {!ticketCode && (
        <Card lift={false} className="flex min-h-0 flex-1 flex-col">
          <CardHeader title="Catalog" desc="Products and their policies" />
          <CardBody className="flex min-h-0 flex-1 flex-col gap-2 overflow-y-auto">
            {catalog.isPending && <Skeleton lines={4} />}
            {(catalog.data ?? []).slice(0, 8).map((item) => (
              <button
                key={item.sku}
                type="button"
                onClick={() => onAsk(`What is the policy for ${item.sku}?`)}
                className="rounded-xl border border-slate-200 bg-white p-2.5 text-left hover:border-slate-300 hover:bg-slate-50"
              >
                <p className="flex items-center gap-1.5 text-[13px] font-semibold text-slate-900">
                  <Package aria-hidden className="h-3.5 w-3.5 text-slate-400" />
                  {item.title}
                </p>
                <p className="mt-0.5 text-xs text-slate-500">
                  {item.sku} · {item.category} · {formatINR(item.unit_paise)}
                </p>
              </button>
            ))}
          </CardBody>
        </Card>
      )}

      {ticketCode && (
        <Card lift={false}>
          <CardHeader
            title={ticketCode}
            desc="Ticket"
            actions={
              ticket.data ? <Badge tone={ticket.data.status}>{ticket.data.status}</Badge> : undefined
            }
          />
          <CardBody className="flex flex-col gap-3">
            {ticket.isPending && <Skeleton lines={3} />}
            {ticket.data && (
              <>
                <div>
                  <p className="text-sm font-semibold text-slate-900">{ticket.data.subject}</p>
                  <p className="mt-0.5 text-[13px] text-slate-500">
                    {ticket.data.category}
                  </p>
                  <p className="mt-1.5 line-clamp-3 text-[13px] leading-5 text-slate-600">
                    {ticket.data.body}
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => onSolve(ticket.data!.code)}
                  className="ns-btn ns-btn-primary ns-btn-sm self-start"
                >
                  Solve with bot
                </button>
              </>
            )}
          </CardBody>
        </Card>
      )}

      {ticketCode && orderId && (
        <Card lift={false}>
          <CardHeader title="Order" desc={order.data ? order.data.code : "…"} />
          <CardBody className="flex flex-col gap-2">
            {order.isPending && <Skeleton lines={3} />}
            {order.data && (
              <>
                <p className="flex items-center justify-between text-[13px]">
                  <Badge tone={order.data.status === "delivered" ? "resolved" : "open"}>
                    {order.data.status}
                  </Badge>
                  <span className="font-semibold text-slate-900">
                    {formatINR(order.data.total_paise)}
                  </span>
                </p>
                {order.data.items.map((item) => (
                  <div key={item.id} className="rounded-xl border border-slate-200 p-2.5">
                    <p className="text-[13px] font-semibold text-slate-900">{item.title}</p>
                    <p className="mt-0.5 text-xs text-slate-500">
                      {item.sku} · {item.category} · ×{item.qty} · {formatINR(item.unit_paise)}
                    </p>
                    <button
                      type="button"
                      onClick={() => onAsk(`What is the policy for ${item.sku}?`)}
                      className="mt-1 text-xs font-medium text-indigo-700 hover:underline"
                    >
                      Ask bot about policy →
                    </button>
                  </div>
                ))}
              </>
            )}
          </CardBody>
        </Card>
      )}

      {ticketCode && firstSku && (
        <Card lift={false}>
          <CardHeader
            title="Policies"
            desc={firstSku}
            actions={<ShieldCheck aria-hidden className="h-4 w-4 text-slate-400" />}
          />
          <CardBody className="flex flex-col gap-1.5">
            {product.isPending && <Skeleton lines={3} />}
            {(product.data?.policies ?? []).slice(0, 5).map((policy) => (
              <p key={policy.rule_key} className="text-[13px] leading-5 text-slate-700">
                <span className="font-mono text-xs text-slate-500">[{policy.rule_key}]</span>{" "}
                {policy.summary}
              </p>
            ))}
            {!product.isPending && (product.data?.policies.length ?? 0) === 0 && (
              <EmptyState title="No policies" desc="Nothing governs this product yet." />
            )}
          </CardBody>
        </Card>
      )}
    </div>
  );
}
