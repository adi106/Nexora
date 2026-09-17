import { apiClient } from "./client";
import type { Order } from "../types";

function normalizeOrder(order: Order): Order {
  return {
    ...order,
    total_amount: Number(order.total_amount),
    items: order.items.map((item) => ({
      ...item,
      unit_price: Number(item.unit_price),
      subtotal: Number(item.subtotal),
    })),
  };
}

export async function listOrders(): Promise<Order[]> {
  const { data } = await apiClient.get<Order[]>("/orders");
  return data.map(normalizeOrder);
}

export async function getOrder(orderId: string): Promise<Order> {
  const { data } = await apiClient.get<Order>(`/orders/${orderId}`);
  return normalizeOrder(data);
}
