import { createContext, useCallback, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { addCartItem, getCart, removeCartItem, updateCartItem } from "../api/cart";
import type { Cart } from "../types";
import { useAuth } from "../hooks/useAuth";

interface CartContextValue {
  cart: Cart | null;
  isLoading: boolean;
  itemCount: number;
  refresh: () => Promise<void>;
  addItem: (variantId: string, quantity: number) => Promise<void>;
  updateItem: (itemId: string, quantity: number) => Promise<void>;
  removeItem: (itemId: string) => Promise<void>;
}

export const CartContext = createContext<CartContextValue | undefined>(undefined);

export function CartProvider({ children }: { children: ReactNode }) {
  const { isAuthenticated } = useAuth();
  const [cart, setCart] = useState<Cart | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const refresh = useCallback(async () => {
    if (!isAuthenticated) {
      setCart(null);
      return;
    }
    setIsLoading(true);
    try {
      const data = await getCart();
      setCart(data);
    } finally {
      setIsLoading(false);
    }
  }, [isAuthenticated]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const addItem = useCallback(
    async (variantId: string, quantity: number) => {
      await addCartItem(variantId, quantity);
      await refresh();
    },
    [refresh],
  );

  const updateItem = useCallback(
    async (itemId: string, quantity: number) => {
      await updateCartItem(itemId, quantity);
      await refresh();
    },
    [refresh],
  );

  const removeItem = useCallback(
    async (itemId: string) => {
      await removeCartItem(itemId);
      await refresh();
    },
    [refresh],
  );

  const itemCount = useMemo(
    () => cart?.items.reduce((sum, item) => sum + item.quantity, 0) ?? 0,
    [cart],
  );

  const value = useMemo<CartContextValue>(
    () => ({ cart, isLoading, itemCount, refresh, addItem, updateItem, removeItem }),
    [cart, isLoading, itemCount, refresh, addItem, updateItem, removeItem],
  );

  return <CartContext.Provider value={value}>{children}</CartContext.Provider>;
}
