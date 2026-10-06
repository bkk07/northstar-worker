import { axiosClient } from "@/shared/api/axiosClient";

// Mirror of backend/app/schemas/commerce/catalog.py (run generate:types
// once the backend serves /api/catalog, then alias generated DTOs here).
export type PolicyRead = {
  rule_key: string;
  summary: string;
  params: Record<string, unknown>;
  version: number;
};

export type ProductRead = {
  sku: string;
  title: string;
  category: string;
  unit_paise: number;
  orders_count: number;
};

export type ProductDetailRead = {
  product: ProductRead;
  policies: PolicyRead[];
};

// Read-only dummy catalog: products are the seeded SKUs, policies are the
// seeded rules with human summaries. The console quotes these everywhere.
export async function listProducts(): Promise<ProductRead[]> {
  const { data } = await axiosClient.get<ProductRead[]>("/api/catalog/products");
  return data;
}

export async function getProduct(sku: string): Promise<ProductDetailRead> {
  const { data } = await axiosClient.get<ProductDetailRead>(
    `/api/catalog/products/${sku}`,
  );
  return data;
}

export async function listPolicies(): Promise<PolicyRead[]> {
  const { data } = await axiosClient.get<PolicyRead[]>("/api/catalog/policies");
  return data;
}
