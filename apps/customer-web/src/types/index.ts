export type Product = {
  id: string;
  name: string;
  slug: string;
  category: string;
  brand: string;
  price_paise: number;
  price_display: string;
  image_url: string;
  stock: number;
  in_stock: boolean;
};

export type PolicySummary = {
  return_allowed: boolean;
  return_window_days: number;
  refund_allowed: boolean;
  replacement_allowed: boolean;
  replacement_window_days: number;
  cancellation_allowed: boolean;
  warranty_days: number;
  summary: string;
};

export type ProductDetail = Product & {
  description: string;
  policy: PolicySummary;
};

export type CartItem = {
  id: string;
  product_id: string;
  product_name: string;
  quantity: number;
  unit_price_paise: number;
  line_total_paise: number;
};

export type Cart = {
  id: string;
  items: CartItem[];
  subtotal_paise: number;
  total_paise: number;
  item_count: number;
};

export type OrderStatus = "PROCESSING" | "SHIPPED" | "DELIVERED";

export type OrderItem = {
  id: string;
  product_id: string;
  product_name: string;
  quantity: number;
  unit_price_paise: number;
  line_total_paise: number;
};

export type Payment = {
  payment_reference: string;
  amount_paise: number;
  amount_display: string;
  status: string;
  method: string;
  paid_at: string;
};

export type TimelineStep = {
  key: string;
  label: string;
  done: boolean;
  at: string | null;
};

export type Order = {
  id: string;
  order_number: string;
  status: OrderStatus;
  subtotal_paise: number;
  total_paise: number;
  total_display: string;
  payment_status: string;
  item_count: number;
  ordered_at: string;
  estimated_delivery: string;
};

export type OrderDetail = Order & {
  shipping_address: string;
  delivered_at: string | null;
  items: OrderItem[];
  payment: Payment;
  timeline: TimelineStep[];
};

export type TicketStatus = "OPEN" | "RESOLVED";
