import { apiClient } from "./client";
import type { Address, AddressInput } from "../types";

export async function listAddresses(): Promise<Address[]> {
  const { data } = await apiClient.get<Address[]>("/addresses");
  return data;
}

export async function createAddress(payload: AddressInput): Promise<Address> {
  const { data } = await apiClient.post<Address>("/addresses", payload);
  return data;
}

export async function updateAddress(addressId: string, payload: Partial<AddressInput>): Promise<Address> {
  const { data } = await apiClient.put<Address>(`/addresses/${addressId}`, payload);
  return data;
}

export async function deleteAddress(addressId: string): Promise<void> {
  await apiClient.delete(`/addresses/${addressId}`);
}
