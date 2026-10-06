import { api } from "@/lib/api-client";
import type { Cart, Order, OrderDetail, Product, ProductDetail } from "@/types";

export type ProductQuery = { q?: string; category?: string; sort?: string };

export async function listProducts(query: ProductQuery = {}): Promise<Product[]> {
  const { data } = await api.get<Product[]>("/products", { params: query });
  return data;
}

export async function getProduct(id: string): Promise<ProductDetail> {
  const { data } = await api.get<ProductDetail>(`/products/${id}`);
  return data;
}

export async function listCategories(): Promise<string[]> {
  const { data } = await api.get<string[]>("/products-meta/categories");
  return data;
}

export async function fetchCart(): Promise<Cart> {
  const { data } = await api.get<Cart>("/cart");
  return data;
}

export async function addCartItem(productId: string, quantity = 1): Promise<Cart> {
  const { data } = await api.post<Cart>("/cart/items", { product_id: productId, quantity });
  return data;
}

export async function updateCartItem(itemId: string, quantity: number): Promise<Cart> {
  const { data } = await api.patch<Cart>(`/cart/items/${itemId}`, { quantity });
  return data;
}

export async function removeCartItem(itemId: string): Promise<Cart> {
  const { data } = await api.delete<Cart>(`/cart/items/${itemId}`);
  return data;
}

export async function checkout(shippingAddress: string): Promise<OrderDetail> {
  const { data } = await api.post<OrderDetail>("/checkout", {
    shipping_address: shippingAddress,
  });
  return data;
}

export async function listOrders(): Promise<Order[]> {
  const { data } = await api.get<Order[]>("/orders");
  return data;
}

export async function getOrder(id: string): Promise<OrderDetail> {
  const { data } = await api.get<OrderDetail>(`/orders/${id}`);
  return data;
}
