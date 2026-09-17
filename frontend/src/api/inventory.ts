import { apiClient } from "./client";

export interface Inventory {
  id: string;
  variant_id: string;
  quantity: number;
  reserved_quantity: number;
  reorder_level: number;
  is_active: boolean;
}

export async function getInventory(variantId: string): Promise<Inventory> {
  const { data } = await apiClient.get<Inventory>(`/inventory/variants/${variantId}`);
  return data;
}
