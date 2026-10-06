import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { ArrowRight, Package, RotateCcw, ShieldCheck } from "lucide-react";
import { Badge, Card, EmptyState, ErrorState, Skeleton } from "@/components/ui";
import { ProductCard } from "@/components/product-card";
import { listCategories, listProducts } from "@/services/shop-api";

export function HomePage() {
  const featured = useQuery({ queryKey: ["products", "featured"], queryFn: () => listProducts({}) });
  const categories = useQuery({ queryKey: ["categories"], queryFn: listCategories });

  const top = (featured.data ?? []).slice(0, 4);

  return (
    <div className="flex flex-col gap-8">
      <motion.section
        className="ns-card ns-card-pad"
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.25 }}
      >
        <Badge>New season · free 7-day returns</Badge>
        <h1 className="mt-3 text-3xl font-bold tracking-tight">Everything you need, delivered fast.</h1>
        <p className="ns-muted mt-2 max-w-xl">
          Shop audio, wearables, home, and more. Mock checkout takes about a minute
          from payment to delivery.
        </p>
        <div className="mt-4 flex gap-2">
          <Link to="/products" className="ns-btn ns-btn-primary">
            Shop products <ArrowRight size={16} aria-hidden />
          </Link>
          <Link to="/orders" className="ns-btn ns-btn-secondary">Track orders</Link>
        </div>
      </motion.section>

      <section>
        <div className="ns-row-between mb-3">
          <h2 className="ns-title">Shop by category</h2>
          <Link to="/products" className="text-sm font-medium text-indigo-700 hover:underline">
            View all
          </Link>
        </div>
        {categories.isPending ? (
          <div className="flex gap-2">{[0, 1, 2, 3].map((i) => <Skeleton key={i} className="h-9 w-28" />)}</div>
        ) : categories.isError ? (
          <p className="ns-muted">Categories unavailable offline.</p>
        ) : (categories.data ?? []).length === 0 ? (
          <p className="ns-muted">Categories land with the Phase 3 seed.</p>
        ) : (
          <div className="flex flex-wrap gap-2">
            {(categories.data ?? []).map((c) => (
              <Link key={c} to={`/products?category=${encodeURIComponent(c)}`} className="ns-btn ns-btn-secondary ns-btn-sm">
                {c}
              </Link>
            ))}
          </div>
        )}
      </section>

      <section>
        <div className="ns-row-between mb-3">
          <h2 className="ns-title">Featured products</h2>
          <Link to="/products" className="text-sm font-medium text-indigo-700 hover:underline">
            View all
          </Link>
        </div>
        {featured.isPending ? (
          <div className="ns-grid-products">
            {Array.from({ length: 4 }).map((_, i) => (
              <Card key={i}>
                <Skeleton className="ns-product-img" />
                <div className="mt-3 flex flex-col gap-2">
                  <Skeleton className="h-4 w-3/4" />
                  <Skeleton className="h-4 w-1/3" />
                </div>
              </Card>
            ))}
          </div>
        ) : featured.isError ? (
          <ErrorState
            title="Could not load products"
            hint="Start the backend, then run the Phase 3 seed."
            onRetry={() => void featured.refetch()}
          />
        ) : top.length === 0 ? (
          <EmptyState title="No products yet" hint="Run scripts/seed_products.py to load the catalog." />
        ) : (
          <div className="ns-grid-products">
            {top.map((p, i) => (
              <ProductCard key={p.id} product={p} index={i} />
            ))}
          </div>
        )}
      </section>

      <section className="grid gap-4 sm:grid-cols-3">
        {[
          { icon: <Package size={18} aria-hidden />, t: "Fast delivery", d: "Processing → Shipped → Delivered in ~1 min." },
          { icon: <RotateCcw size={18} aria-hidden />, t: "Easy returns", d: "Per-product policy summary on every page." },
          { icon: <ShieldCheck size={18} aria-hidden />, t: "Human + AI support", d: "Raise a ticket; support solves it manually or with AI." },
        ].map((f) => (
          <Card key={f.t}>
            <div className="flex items-center gap-2 font-semibold">{f.icon}{f.t}</div>
            <p className="ns-muted mt-1">{f.d}</p>
          </Card>
        ))}
      </section>
    </div>
  );
}
