import { apiClient } from "./client";
import type { WishlistItem } from "../types";

export async function listWishlist(): Promise<WishlistItem[]> {
  const { data } = await apiClient.get<WishlistItem[]>("/wishlist");
  return data;
}

export async function addToWishlist(productId: string): Promise<WishlistItem> {
  const { data } = await apiClient.post<WishlistItem>(`/wishlist/products/${productId}`);
  return data;
}

export async function removeFromWishlist(productId: string): Promise<void> {
  await apiClient.delete(`/wishlist/products/${productId}`);
}
