import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { ShoppingCart } from "lucide-react";
import { Badge, Card } from "@/components/ui";
import type { Product } from "@/types";

const tileColors = [
  "from-indigo-100 to-indigo-50",
  "from-amber-100 to-amber-50",
  "from-emerald-100 to-emerald-50",
  "from-rose-100 to-rose-50",
];

export function ProductImage({ product, size = "md" }: { product: Product; size?: "md" | "lg" }) {
  const tone = tileColors[product.name.length % tileColors.length];
  return (
    <div
      className={`flex items-center justify-center bg-gradient-to-br ${tone} ${
        size === "lg" ? "aspect-[4/3] rounded-2xl text-6xl" : "ns-product-img text-4xl"
      } font-bold text-indigo-900/30`}
      role="img"
      aria-label={product.name}
    >
      {product.name.charAt(0)}
    </div>
  );
}

export function ProductCard({ product, index = 0 }: { product: Product; index?: number }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2, delay: Math.min(index * 0.03, 0.3) }}
    >
      <Link to={`/products/${product.id}`} className="group block">
        <Card className="overflow-hidden !p-0 transition-shadow group-hover:shadow-lg">
          <ProductImage product={product} />
          <div className="p-3">
            <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">
              {product.brand || product.category}
            </p>
            <p className="mt-0.5 truncate text-sm font-semibold group-hover:text-indigo-700">
              {product.name}
            </p>
            <div className="mt-1.5 flex items-center justify-between">
              <span className="text-sm font-bold">{product.price_display}</span>
              {product.in_stock ? (
                <Badge tone="ok">In stock</Badge>
              ) : (
                <Badge tone="bad">Out of stock</Badge>
              )}
            </div>
          </div>
        </Card>
      </Link>
    </motion.div>
  );
}

export function AddToCartButton({
  onClick,
  disabled,
  label = "Add to cart",
}: {
  onClick: () => void;
  disabled?: boolean;
  label?: string;
}) {
  return (
    <button className="ns-btn ns-btn-primary" onClick={onClick} disabled={disabled}>
      <ShoppingCart size={16} aria-hidden /> {label}
    </button>
  );
}
