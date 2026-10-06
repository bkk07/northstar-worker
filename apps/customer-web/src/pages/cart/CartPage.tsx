import { Link } from "react-router-dom";
import { Card, EmptyState } from "@/components/ui";

// Phase 1: cart shell. Real cart APIs arrive Phase 3.
export function CartPage() {
  return (
    <Card>
      <h1 className="ns-title">Your cart</h1>
      <EmptyState
        title="Your cart is empty"
        hint="Add products in Phase 3. Checkout + mock payment arrive in Phase 4."
        action={<Link to="/products" className="ns-btn ns-btn-primary ns-btn-sm">Browse products</Link>}
      />
    </Card>
  );
}
