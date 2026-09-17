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
