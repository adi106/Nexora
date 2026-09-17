import { apiClient } from "./client";
import type { Product, ProductInput, ProductVariant, VariantInput } from "../types";

function normalizeProduct(product: Product): Product {
  return { ...product, base_price: Number(product.base_price) };
}

function normalizeVariant(variant: ProductVariant): ProductVariant {
  return { ...variant, price: Number(variant.price) };
}

export async function createProduct(payload: ProductInput): Promise<Product> {
  const { data } = await apiClient.post<Product>("/products", payload);
  return normalizeProduct(data);
}

export async function updateProductDetails(
  productId: string,
  payload: Partial<ProductInput>,
): Promise<Product> {
  const { data } = await apiClient.put<Product>(`/products/${productId}/details`, payload);
  return normalizeProduct(data);
}

export async function setProductActive(productId: string, isActive: boolean): Promise<Product> {
  const { data } = await apiClient.patch<Product>(`/products/${productId}`, { is_active: isActive });
  return normalizeProduct(data);
}

export async function createVariant(productId: string, payload: VariantInput): Promise<ProductVariant> {
  const { data } = await apiClient.post<ProductVariant>(`/products/${productId}/variants`, payload);
  return normalizeVariant(data);
}

export async function updateVariantDetails(
  productId: string,
  variantId: string,
  payload: Partial<VariantInput>,
): Promise<ProductVariant> {
  const { data } = await apiClient.put<ProductVariant>(
    `/products/${productId}/variants/${variantId}/details`,
    payload,
  );
  return normalizeVariant(data);
}

export async function setVariantActive(
  productId: string,
  variantId: string,
  isActive: boolean,
): Promise<ProductVariant> {
  const { data } = await apiClient.patch<ProductVariant>(
    `/products/${productId}/variants/${variantId}`,
    { is_active: isActive },
  );
  return normalizeVariant(data);
}

export async function updateInventory(
  variantId: string,
  quantity: number,
  reorderLevel: number,
): Promise<void> {
  await apiClient.put(`/inventory/variants/${variantId}`, {
    quantity,
    reorder_level: reorderLevel,
  });
}

export async function updateOrderStatus(orderId: string, statusValue: string): Promise<void> {
  await apiClient.patch(`/orders/${orderId}/status`, { status: statusValue });
}
