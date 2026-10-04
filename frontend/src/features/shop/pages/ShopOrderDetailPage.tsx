import { useNavigate, useParams } from "react-router-dom";
import { TicketForm } from "../components/TicketForm";
import { ErrorState, LoadingState } from "@/shared/ui/feedback";
import { useCustomer, useOrder } from "../hooks/useShop";
import { formatINR } from "@/shared/lib/format";

export default function ShopOrderDetailPage() {
  const { orderCode } = useParams();
  const navigate = useNavigate();
  const order = useOrder(orderCode);
  const customer = useCustomer(order.data?.customer_id);

  if (order.isPending) return <LoadingState what="order" />;
  if (order.isError || !order.data)
    return (
      <main className="mx-auto max-w-3xl p-8">
        <ErrorState message="Could not load the order." />
      </main>
    );

  return (
    <main className="mx-auto max-w-3xl p-8">
      <h1 className="text-2xl font-semibold">Order {order.data.code}</h1>
      <p className="text-sm text-slate-600">
        {order.data.status} · Total {formatINR(order.data.total_paise)} · Paid{" "}
        {formatINR(order.data.paid_paise)}
      </p>
      <table className="mt-4 w-full text-sm">
        <thead>
          <tr className="text-left text-slate-500">
            <th>Item</th>
            <th>Qty</th>
            <th>Price</th>
          </tr>
        </thead>
        <tbody>
          {order.data.items.map((item) => (
            <tr key={item.id} className="border-t">
              <td>
                {item.title} ({item.sku})
              </td>
              <td>{item.qty}</td>
              <td>{formatINR(item.unit_paise)}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {customer.data && (
        <TicketForm
          customerCode={customer.data.code}
          orderCode={order.data.code}
          onCreated={(ticket) => navigate(`/shop/tickets/${ticket.code}`)}
        />
      )}
    </main>
  );
}
