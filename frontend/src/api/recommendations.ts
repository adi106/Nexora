import { apiClient } from "./client";
import type { Product } from "../types";

export async function getRecommendations(limit = 10): Promise<Product[]> {
  const { data } = await apiClient.get<Product[]>("/recommendations", { params: { limit } });
  return data.map((product) => ({ ...product, base_price: Number(product.base_price) }));
}

export async function recordProductView(productId: string): Promise<void> {
  await apiClient.post("/recommendations/interactions", {
    product_id: productId,
    interaction_type: "view",
  });
}
