import { createContext, useCallback, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { addToWishlist, listWishlist, removeFromWishlist } from "../api/wishlist";
import { useAuth } from "../hooks/useAuth";

interface WishlistContextValue {
  productIds: Set<string>;
  isLoading: boolean;
  refresh: () => Promise<void>;
  toggle: (productId: string) => Promise<void>;
}

export const WishlistContext = createContext<WishlistContextValue | undefined>(undefined);

export function WishlistProvider({ children }: { children: ReactNode }) {
  const { isAuthenticated } = useAuth();
  const [productIds, setProductIds] = useState<Set<string>>(new Set());
  const [isLoading, setIsLoading] = useState(false);

  const refresh = useCallback(async () => {
    if (!isAuthenticated) {
      setProductIds(new Set());
      return;
    }
    setIsLoading(true);
    try {
      const items = await listWishlist();
      setProductIds(new Set(items.map((item) => item.product_id)));
    } finally {
      setIsLoading(false);
    }
  }, [isAuthenticated]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const toggle = useCallback(
    async (productId: string) => {
      if (productIds.has(productId)) {
        await removeFromWishlist(productId);
      } else {
        await addToWishlist(productId);
      }
      await refresh();
    },
    [productIds, refresh],
  );

  const value = useMemo<WishlistContextValue>(
    () => ({ productIds, isLoading, refresh, toggle }),
    [productIds, isLoading, refresh, toggle],
  );

  return <WishlistContext.Provider value={value}>{children}</WishlistContext.Provider>;
}
