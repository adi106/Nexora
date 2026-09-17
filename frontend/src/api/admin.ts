import { apiClient } from "./client";
import type { Category, Order, Product, ProductListResponse, Seller, User } from "../types";

export interface AdminStats {
  user_count: number;
  seller_count: number;
  product_count: number;
  order_count: number;
  total_revenue: number;
}

export interface Paginated<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

export async function getAdminStats(): Promise<AdminStats> {
  const { data } = await apiClient.get<AdminStats>("/admin/stats");
  return { ...data, total_revenue: Number(data.total_revenue) };
}

export async function listAdminUsers(search?: string): Promise<Paginated<User>> {
  const { data } = await apiClient.get<Paginated<User>>("/admin/users", {
    params: { page_size: 100, search: search || undefined },
  });
  return data;
}

export async function setUserActive(userId: string, isActive: boolean): Promise<User> {
  const { data } = await apiClient.patch<User>(`/admin/users/${userId}/status`, {
    is_active: isActive,
  });
  return data;
}

export async function listAdminSellers(): Promise<Paginated<Seller>> {
  const { data } = await apiClient.get<Paginated<Seller>>("/admin/sellers", {
    params: { page_size: 100 },
  });
  return data;
}

export async function setSellerActive(sellerId: number, isActive: boolean): Promise<Seller> {
  const { data } = await apiClient.patch<Seller>(`/admin/sellers/${sellerId}/status`, {
    is_active: isActive,
  });
  return data;
}

export async function listAdminProducts(): Promise<ProductListResponse> {
  const { data } = await apiClient.get<ProductListResponse>("/admin/products", {
    params: { page_size: 100 },
  });
  return {
    ...data,
    items: data.items.map((product) => ({ ...product, base_price: Number(product.base_price) })),
  };
}

export async function setProductActiveAdmin(productId: string, isActive: boolean): Promise<Product> {
  const { data } = await apiClient.patch<Product>(`/admin/products/${productId}/status`, {
    is_active: isActive,
  });
  return { ...data, base_price: Number(data.base_price) };
}

export async function listAdminCategories(): Promise<Category[]> {
  const { data } = await apiClient.get<Category[]>("/admin/categories");
  return data;
}

export async function listAdminOrders(): Promise<Order[]> {
  const { data } = await apiClient.get<Order[]>("/admin/orders", { params: { page_size: 100 } });
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
