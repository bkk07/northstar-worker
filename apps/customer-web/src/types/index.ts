export type Product = {
  id: string;
  name: string;
  slug: string;
  price: number;
  imageUrl?: string;
  category?: string;
  inStock: boolean;
};

export type CartItem = { productId: string; qty: number };

export type OrderStatus =
  | "PROCESSING"
  | "SHIPPED"
  | "DELIVERED";

export type TicketStatus = "OPEN" | "RESOLVED";
