import { useQuery } from "@tanstack/react-query";
import { Package, ShieldCheck } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";
import { getProduct, listPolicies, listProducts } from "../api/catalogApi";
import { Badge } from "@/shared/ui/badge";
import { Card, CardBody, CardHeader } from "@/shared/ui/card";
import { EmptyState } from "@/shared/ui/empty-state";
import { ErrorState, LoadingState } from "@/shared/ui/feedback";
import { PageHeader } from "@/shared/ui/page-header";
import { Skeleton } from "@/shared/ui/skeleton";
import { formatINR } from "@/shared/lib/format";
import { cn } from "@/shared/lib/utils";

function ProductPolicies({ sku }: { sku: string }) {
  const detail = useQuery({
    queryKey: ["catalog", "product", sku],
    queryFn: () => getProduct(sku),
    staleTime: 60_000,
  });
  if (detail.isPending) return <Skeleton lines={3} />;
  if (detail.isError || !detail.data)
    return <p className="text-[13px] text-slate-500">Policies unavailable.</p>;
  return (
    <ul className="flex flex-col gap-1.5">
      {detail.data.policies.map((policy) => (
        <li key={policy.rule_key} className="text-[13px] leading-5 text-slate-700">
          <span className="font-mono text-xs text-slate-500">[{policy.rule_key}]</span>{" "}
          {policy.summary}
        </li>
      ))}
    </ul>
  );
}

/**
 * Products + policies: every catalog product with the rules that govern
 * it, plus the full policy table. The bot quotes these same summaries.
 */
export default function ProductsPage() {
  const products = useQuery({
    queryKey: ["catalog", "products"],
    queryFn: listProducts,
    staleTime: 60_000,
  });
  const policies = useQuery({
    queryKey: ["catalog", "policies"],
    queryFn: listPolicies,
    staleTime: 60_000,
  });
  const [openSku, setOpenSku] = useState<string | null>(null);

  return (
    <div className="ns-page flex flex-col gap-4">
      <PageHeader
        title="Products & policies"
        desc="Every product with the refund and replacement rules that apply to it."
      />
      {products.isPending && <LoadingState what="products" />}
      {products.isError && (
        <ErrorState message="Could not load products." onRetry={() => products.refetch()} />
      )}
      {products.data && products.data.length === 0 && (
        <EmptyState title="No products" desc="The catalog is empty." icon={Package} />
      )}
      {products.data && products.data.length > 0 && (
        <div className="grid gap-4 lg:grid-cols-2">
          {products.data.map((item) => {
            const open = openSku === item.sku;
            return (
              <Card key={item.sku} lift={false}>
                <CardBody>
                  <button
                    type="button"
                    onClick={() => setOpenSku(open ? null : item.sku)}
                    aria-expanded={open}
                    className="flex w-full items-center gap-3 text-left"
                  >
                    <span
                      aria-hidden
                      className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-indigo-50"
                    >
                      <Package className="h-5 w-5 text-indigo-600" />
                    </span>
                    <span className="min-w-0 flex-1">
                      <span className="block truncate text-sm font-semibold text-slate-900">
                        {item.title}
                      </span>
                      <span className="block text-xs text-slate-500">
                        {item.sku} · {item.category} · {formatINR(item.unit_paise)}
                      </span>
                    </span>
                    <span className={cn("text-xs font-medium text-indigo-700")}>
                      {open ? "Hide policies" : "Show policies"}
                    </span>
                  </button>
                  {open && (
                    <div className="mt-3 border-t border-slate-100 pt-3">
                      <ProductPolicies sku={item.sku} />
                      <Link
                        to={`/worker/assistant?product=${item.sku}`}
                        className="mt-2 inline-block text-[13px] font-medium text-indigo-700 hover:underline"
                      >
                        Ask the bot about {item.sku} →
                      </Link>
                    </div>
                  )}
                </CardBody>
              </Card>
            );
          })}
        </div>
      )}

      <Card lift={false}>
        <CardHeader
          title="All policies"
          desc="The full rule table the bot and the agent enforce."
          actions={<ShieldCheck aria-hidden className="h-4 w-4 text-slate-400" />}
        />
        <CardBody className="flex flex-col gap-1.5">
          {policies.isPending && <Skeleton lines={4} />}
          {(policies.data ?? []).map((policy) => (
            <p key={policy.rule_key} className="text-[13px] leading-5 text-slate-700">
              <Badge tone="neutral">{policy.rule_key}</Badge> {policy.summary}
            </p>
          ))}
        </CardBody>
      </Card>
    </div>
  );
}
