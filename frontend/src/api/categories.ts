import { apiClient } from "./client";
import type { Category, ProductListResponse } from "../types";

export async function listCategories(): Promise<Category[]> {
  const { data } = await apiClient.get<Category[]>("/categories");
  return data;
}

export async function getCategoryProducts(
  slug: string,
  page = 1,
  pageSize = 20,
): Promise<ProductListResponse> {
  const { data } = await apiClient.get<ProductListResponse>(`/categories/${slug}/products`, {
    params: { page, page_size: pageSize },
  });
  return { ...data, items: data.items.map((product) => ({ ...product, base_price: Number(product.base_price) })) };
}

export interface CategoryInput {
  name: string;
  slug: string;
  description?: string | null;
  parent_id?: number | null;
  is_active: boolean;
}

export async function createCategory(payload: CategoryInput): Promise<Category> {
  const { data } = await apiClient.post<Category>("/categories", payload);
  return data;
}

export async function setCategoryActive(categoryId: number, isActive: boolean): Promise<Category> {
  const { data } = await apiClient.patch<Category>(`/categories/${categoryId}`, { is_active: isActive });
  return data;
}
