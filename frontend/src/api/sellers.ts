import { apiClient } from "./client";
import type { Order, ProductDetail, ProductListResponse, Seller, SellerStats } from "../types";

export interface SellerSignupInput {
  store_name: string;
  store_slug: string;
  description?: string | null;
}

export async function becomeSeller(payload: SellerSignupInput): Promise<Seller> {
  const { data } = await apiClient.post<Seller>("/sellers", payload);
  return data;
}

export async function getMySeller(): Promise<Seller | null> {
  try {
    const { data } = await apiClient.get<Seller>("/sellers/me");
    return data;
  } catch (err: unknown) {
    if (typeof err === "object" && err !== null && "response" in err) {
      const response = (err as { response?: { status?: number } }).response;
      if (response?.status === 404) return null;
    }
    throw err;
  }
}

export async function getMySellerStats(): Promise<SellerStats> {
  const { data } = await apiClient.get<SellerStats>("/sellers/me/stats");
  return { ...data, total_revenue: Number(data.total_revenue) };
}

export async function listMyProducts(page = 1, pageSize = 50): Promise<ProductListResponse> {
  const { data } = await apiClient.get<ProductListResponse>("/sellers/me/products", {
    params: { page, page_size: pageSize },
  });
  return {
    ...data,
    items: data.items.map((product) => ({ ...product, base_price: Number(product.base_price) })),
  };
}

export async function getMyProduct(productId: string): Promise<ProductDetail> {
  const { data } = await apiClient.get<ProductDetail>(`/sellers/me/products/${productId}`);
  return {
    ...data,
    base_price: Number(data.base_price),
    variants: data.variants.map((variant) => ({ ...variant, price: Number(variant.price) })),
  };
}

export async function listMySellerOrders(): Promise<Order[]> {
  const { data } = await apiClient.get<Order[]>("/sellers/me/orders");
  return data.map((order) => ({
    ...order,
    total_amount: Number(order.total_amount),
    items: order.items.map((item) => ({
      ...item,
      unit_price: Number(item.unit_price),
      subtotal: Number(item.subtotal),
    })),
  }));
}
