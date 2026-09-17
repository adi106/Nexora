import { apiClient } from "./client";
import type { Product, ProductDetail, ProductListResponse, ProductSearchParams, VariantWithProduct } from "../types";

function normalizeProduct<T extends Product>(product: T): T {
  return { ...product, base_price: Number(product.base_price) };
}

function normalizeProductDetail(product: ProductDetail): ProductDetail {
  return {
    ...normalizeProduct(product),
    variants: product.variants.map((variant) => ({ ...variant, price: Number(variant.price) })),
  };
}

export async function listProducts(params: ProductSearchParams = {}): Promise<ProductListResponse> {
  const { data } = await apiClient.get<ProductListResponse>("/products", { params });
  return { ...data, items: data.items.map(normalizeProduct) };
}

export async function getProduct(productId: string): Promise<ProductDetail> {
  const { data } = await apiClient.get<ProductDetail>(`/products/${productId}`);
  return normalizeProductDetail(data);
}

export async function getVariant(variantId: string): Promise<VariantWithProduct> {
  const { data } = await apiClient.get<VariantWithProduct>(`/products/variants/${variantId}`);
  return { ...data, price: Number(data.price) };
}
