import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { ArrowRight, Package, RotateCcw, ShieldCheck } from "lucide-react";
import { Card, Badge } from "@/components/ui";

export function HomePage() {
  return (
    <div className="flex flex-col gap-6">
      <motion.section
        className="ns-card ns-card-pad"
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.25 }}
      >
        <Badge>Phase 1 · storefront shell</Badge>
        <h1 className="mt-3 text-3xl font-bold tracking-tight">Everything you need, delivered fast.</h1>
        <p className="ns-muted mt-2 max-w-xl">
          Browse products, check out with mock payment, track delivery, and raise a support
          ticket — all wired to the backend in Phases 2–5.
        </p>
        <div className="mt-4 flex gap-2">
          <Link to="/products" className="ns-btn ns-btn-primary">
            Shop products <ArrowRight size={16} aria-hidden />
          </Link>
          <Link to="/orders" className="ns-btn ns-btn-secondary">Track orders</Link>
        </div>
      </motion.section>

      <section className="grid gap-4 sm:grid-cols-3">
        {[
          { icon: <Package size={18} aria-hidden />, t: "Fast delivery", d: "Mock lifecycle: Processing → Shipped → Delivered in ~1 min." },
          { icon: <RotateCcw size={18} aria-hidden />, t: "Easy returns", d: "Per-product policy summary on every product page." },
          { icon: <ShieldCheck size={18} aria-hidden />, t: "Human + AI support", d: "Raise a ticket; support solves manually or with AI." },
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
