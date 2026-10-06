import { Link } from "react-router-dom";
import { Card, Badge, EmptyState, Skeleton } from "@/components/ui";

// Phase 1: static shell with skeleton/empty states. Real catalog arrives Phase 3.
export function ProductsPage() {
  return (
    <div className="flex flex-col gap-4">
      <div className="ns-row-between">
        <div>
          <h1 className="ns-title">Products</h1>
          <p className="ns-muted">Search, filter, and sort arrive in Phase 3.</p>
        </div>
        <Badge>0 products · seed in Phase 3</Badge>
      </div>
      <div className="ns-grid-products" aria-label="Product skeleton">
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
      <EmptyState
        title="No products yet"
        hint="Seeded catalog lands in Phase 3. Meanwhile, try the orders and support shells."
        action={<Link to="/support" className="ns-btn ns-btn-secondary ns-btn-sm">Go to support</Link>}
      />
    </div>
  );
}

export function ProductDetailPage() {
  return (
    <Card>
      <Badge>Phase 3</Badge>
      <h1 className="ns-title mt-2">Product detail</h1>
      <p className="ns-muted">Images, price, policy summary, Add to cart / Buy now arrive in Phase 3.</p>
    </Card>
  );
}
