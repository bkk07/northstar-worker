import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";
import { ArrowLeft, Minus, Plus, RotateCcw, ShieldCheck, Truck, X } from "lucide-react";
import { Badge, Button, Card, EmptyState, ErrorState, Input, Skeleton, Spinner } from "@/components/ui";
import { AddToCartButton, ProductCard, ProductImage } from "@/components/product-card";
import { apiErrorMessage } from "@/lib/api-client";
import { formatPaise } from "@/lib/format";
import { getProduct, listCategories, listProducts } from "@/services/shop-api";
import { useAuth } from "@/stores/auth-store";
import { useCart } from "@/stores/cart-store";

export function ProductsPage() {
  const [params, setParams] = useSearchParams();
  const q = params.get("q") ?? "";
  const category = params.get("category") ?? "";
  const sort = params.get("sort") ?? "name";
  const [draft, setDraft] = useState(q);

  const query = useQuery({
    queryKey: ["products", { q, category, sort }],
    queryFn: () =>
      listProducts({
        q: q || undefined,
        category: category || undefined,
        sort,
      }),
  });
  const categories = useQuery({ queryKey: ["categories"], queryFn: listCategories });

  function update(patch: Record<string, string>) {
    const next = new URLSearchParams(params);
    for (const [k, v] of Object.entries(patch)) {
      if (v) next.set(k, v);
      else next.delete(k);
    }
    setParams(next);
  }

  return (
    <div className="flex flex-col gap-4">
      <div>
        <h1 className="ns-title">Products</h1>
        <p className="ns-muted">
          {query.data ? `${query.data.length} product${query.data.length === 1 ? "" : "s"}` : "Browse the catalog"}
        </p>
      </div>

      <div className="flex flex-col gap-2 sm:flex-row">
        <form
          className="flex flex-1 gap-2"
          onSubmit={(e) => {
            e.preventDefault();
            update({ q: draft.trim() });
          }}
        >
          <Input
            placeholder="Search products or brands…"
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            aria-label="Search products"
          />
          <Button type="submit" variant="secondary">Search</Button>
        </form>
        <div className="flex gap-2">
          <select
            className="ns-input sm:w-44"
            value={category}
            onChange={(e) => update({ category: e.target.value })}
            aria-label="Filter by category"
          >
            <option value="">All categories</option>
            {(categories.data ?? []).map((c) => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
          <select
            className="ns-input sm:w-40"
            value={sort}
            onChange={(e) => update({ sort: e.target.value })}
            aria-label="Sort products"
          >
            <option value="name">Name</option>
            <option value="price_asc">Price: low to high</option>
            <option value="price_desc">Price: high to low</option>
          </select>
        </div>
      </div>

      {query.isPending ? (
        <div className="ns-grid-products">
          {Array.from({ length: 8 }).map((_, i) => (
            <Card key={i}>
              <Skeleton className="ns-product-img" />
              <div className="mt-3 flex flex-col gap-2">
                <Skeleton className="h-4 w-3/4" />
                <Skeleton className="h-4 w-1/3" />
              </div>
            </Card>
          ))}
        </div>
      ) : query.isError ? (
        <ErrorState
          title="Could not load products"
          hint="Start the backend and seed the catalog, then retry."
          onRetry={() => void query.refetch()}
        />
      ) : (query.data ?? []).length === 0 ? (
        <EmptyState
          title={q || category ? "No products match" : "No products yet"}
          hint={q || category ? "Try a different search or category." : "Run scripts/seed_products.py."}
          action={
            q || category ? (
              <Button variant="secondary" onClick={() => { setDraft(""); setParams({}); }}>
                Clear filters
              </Button>
            ) : undefined
          }
        />
      ) : (
        <div className="ns-grid-products">
          {(query.data ?? []).map((p, i) => (
            <ProductCard key={p.id} product={p} index={i} />
          ))}
        </div>
      )}
    </div>
  );
}

export function ProductDetailPage() {
  const { id = "" } = useParams();
  const nav = useNavigate();
  const user = useAuth((s) => s.user);
  const add = useCart((s) => s.add);
  const [qty, setQty] = useState(1);
  const [adding, setAdding] = useState(false);
  const [added, setAdded] = useState(false);
  const [cartError, setCartError] = useState<string | null>(null);

  const detail = useQuery({ queryKey: ["product", id], queryFn: () => getProduct(id) });

  async function onAdd(buyNow: boolean) {
    if (!user) {
      nav("/login");
      return;
    }
    setAdding(true);
    setCartError(null);
    try {
      await add(id, qty);
      if (buyNow) nav("/cart");
      else setAdded(true);
    } catch (err) {
      setCartError(apiErrorMessage(err, "Could not add to cart."));
    } finally {
      setAdding(false);
    }
  }

  if (detail.isPending) {
    return (
      <Card>
        <Skeleton className="aspect-[4/3] w-full rounded-2xl" />
        <div className="mt-4 flex flex-col gap-2">
          <Skeleton className="h-6 w-1/2" />
          <Skeleton className="h-4 w-1/4" />
          <Skeleton className="h-4 w-full" />
        </div>
      </Card>
    );
  }
  if (detail.isError) {
    return (
      <Card>
        <ErrorState title="Product not found" hint="It may have been removed." onRetry={() => void detail.refetch()} />
      </Card>
    );
  }

  const p = detail.data;
  return (
    <div className="flex flex-col gap-4">
      <button className="ns-btn ns-btn-ghost self-start" onClick={() => nav(-1)}>
        <ArrowLeft size={16} aria-hidden /> Back
      </button>
      <div className="grid gap-6 md:grid-cols-2">
        <ProductImage product={p} size="lg" />
        <div className="flex flex-col gap-3">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">
              {p.brand} · {p.category}
            </p>
            <h1 className="mt-1 text-2xl font-bold tracking-tight">{p.name}</h1>
            <p className="mt-1 text-xl font-bold">{p.price_display}</p>
          </div>
          <div>{p.in_stock ? <Badge tone="ok">In stock ({p.stock})</Badge> : <Badge tone="bad">Out of stock</Badge>}</div>
          <p className="ns-muted">{p.description}</p>
          <Card>
            <p className="text-sm font-semibold">Policy summary</p>
            <p className="ns-muted mt-1">{p.policy.summary}</p>
            <div className="mt-2 flex flex-wrap gap-1.5 text-xs">
              <span className="ns-badge ns-badge-info flex items-center gap-1"><Truck size={12} aria-hidden /> {p.policy.cancellation_allowed ? "Cancellable" : "Non-cancellable"}</span>
              <span className="ns-badge ns-badge-info flex items-center gap-1"><RotateCcw size={12} aria-hidden /> {p.policy.return_allowed ? `${p.policy.return_window_days}-day returns` : "No returns"}</span>
              <span className="ns-badge ns-badge-info flex items-center gap-1"><ShieldCheck size={12} aria-hidden /> {p.policy.warranty_days ? `${p.policy.warranty_days}-day warranty` : "No warranty"}</span>
            </div>
          </Card>
          <div className="flex items-center gap-2">
            <label className="ns-label !mb-0" htmlFor="qty">Qty</label>
            <button className="ns-iconbtn" aria-label="Decrease quantity" onClick={() => setQty((v) => Math.max(1, v - 1))}>
              <Minus size={14} aria-hidden />
            </button>
            <Input id="qty" className="!w-16 text-center" value={qty} onChange={(e) => setQty(Math.max(1, Math.min(99, Number(e.target.value) || 1)))} />
            <button className="ns-iconbtn" aria-label="Increase quantity" onClick={() => setQty((v) => Math.min(99, v + 1))}>
              <Plus size={14} aria-hidden />
            </button>
          </div>
          <div className="flex flex-wrap gap-2">
            <AddToCartButton onClick={() => void onAdd(false)} disabled={adding || !p.in_stock} label={adding ? "Adding…" : "Add to cart"} />
            <Button variant="secondary" onClick={() => void onAdd(true)} disabled={adding || !p.in_stock}>
              Buy now
            </Button>
          </div>
          {added ? <p className="text-sm text-emerald-700" role="status">Added to cart.</p> : null}
          {cartError ? <p className="text-sm text-red-600" role="alert">{cartError}</p> : null}
          {!user ? <p className="ns-muted">Log in to add items to your cart.</p> : null}
        </div>
      </div>
    </div>
  );
}

export function CartPage() {
  const nav = useNavigate();
  const cart = useCart((s) => s.cart);
  const loading = useCart((s) => s.loading);
  const error = useCart((s) => s.error);
  const refresh = useCart((s) => s.refresh);
  const setQty = useCart((s) => s.setQty);
  const remove = useCart((s) => s.remove);

  useEffect(() => {
    void refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (loading && !cart) return <Spinner label="Loading cart…" />;

  const items = cart?.items ?? [];
  if (items.length === 0) {
    return (
      <Card>
        <h1 className="ns-title">Your cart</h1>
        <EmptyState
          title="Your cart is empty"
          hint="Browse the catalog and add something you like."
          action={<Button onClick={() => nav("/products")}>Browse products</Button>}
        />
        {error ? <p className="ns-muted text-center">{error}</p> : null}
      </Card>
    );
  }

  return (
    <div className="grid gap-6 lg:grid-cols-[1fr_320px]">
      <Card>
        <h1 className="ns-title">Your cart ({cart?.item_count})</h1>
        {error ? <p className="mt-2 text-sm text-red-600" role="alert">{error}</p> : null}
        <ul className="mt-4 flex flex-col gap-3">
          {items.map((line) => (
            <li key={line.id} className="flex items-center justify-between gap-3 border-b border-slate-100 pb-3 last:border-0">
              <div className="min-w-0">
                <p className="truncate text-sm font-semibold">{line.product_name}</p>
                <p className="ns-muted">{formatPaise(line.unit_price_paise)} each</p>
              </div>
              <div className="flex items-center gap-1.5">
                <button className="ns-iconbtn !h-8 !w-8" aria-label="Decrease quantity" onClick={() => void setQty(line.id, Math.max(1, line.quantity - 1))}>
                  <Minus size={13} aria-hidden />
                </button>
                <span className="w-8 text-center text-sm font-semibold">{line.quantity}</span>
                <button className="ns-iconbtn !h-8 !w-8" aria-label="Increase quantity" onClick={() => void setQty(line.id, Math.min(99, line.quantity + 1))}>
                  <Plus size={13} aria-hidden />
                </button>
                <button className="ns-iconbtn !h-8 !w-8" aria-label={`Remove ${line.product_name}`} onClick={() => void remove(line.id)}>
                  <X size={13} aria-hidden />
                </button>
              </div>
              <p className="w-20 text-right text-sm font-bold">{formatPaise(line.line_total_paise)}</p>
            </li>
          ))}
        </ul>
      </Card>
      <Card>
        <h2 className="ns-title">Summary</h2>
        <div className="mt-3 flex flex-col gap-1.5 text-sm">
          <div className="ns-row-between"><span className="ns-muted">Subtotal</span><span className="font-semibold">{formatPaise(cart?.subtotal_paise ?? 0)}</span></div>
          <div className="ns-row-between"><span className="ns-muted">Shipping</span><span className="font-semibold">Free</span></div>
          <div className="ns-row-between border-t border-slate-100 pt-2"><span className="font-semibold">Total</span><span className="font-bold">{formatPaise(cart?.total_paise ?? 0)}</span></div>
        </div>
        <Button className="mt-4 w-full" onClick={() => nav("/checkout")}>
          Proceed to checkout
        </Button>
        <p className="ns-muted mt-2 text-center">Mock payment — no real money moves.</p>
      </Card>
    </div>
  );
}
