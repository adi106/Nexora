import { apiClient } from "./client";
import type { Cart, CartItem } from "../types";

export async function getCart(): Promise<Cart> {
  const { data } = await apiClient.get<Cart>("/cart");
  return data;
}

export async function addCartItem(variantId: string, quantity: number): Promise<CartItem> {
  const { data } = await apiClient.post<CartItem>("/cart/items", {
    variant_id: variantId,
    quantity,
  });
  return data;
}

export async function updateCartItem(itemId: string, quantity: number): Promise<CartItem> {
  const { data } = await apiClient.put<CartItem>(`/cart/items/${itemId}`, { quantity });
  return data;
}

export async function removeCartItem(itemId: string): Promise<void> {
  await apiClient.delete(`/cart/items/${itemId}`);
}
