import { useEffect, useState } from "react";
import { getVariant } from "../api/products";
import type { CartItem, VariantWithProduct } from "../types";

export interface ResolvedCartItem {
  item: CartItem;
  variant: VariantWithProduct;
}

export function useResolvedCartItems(items: CartItem[]) {
  const [variantInfo, setVariantInfo] = useState<Record<string, VariantWithProduct>>({});

  useEffect(() => {
    let cancelled = false;
    const missing = items.filter((item) => !(item.variant_id in variantInfo));
    if (missing.length === 0) return;

    Promise.all(missing.map((item) => getVariant(item.variant_id))).then((results) => {
      if (cancelled) return;
      setVariantInfo((prev) => {
        const next = { ...prev };
        results.forEach((variant) => {
          next[variant.id] = variant;
        });
        return next;
      });
    });

    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [items]);

  const resolved: ResolvedCartItem[] = items
    .filter((item) => item.variant_id in variantInfo)
    .map((item) => ({ item, variant: variantInfo[item.variant_id] }));

  const isResolved = resolved.length === items.length;
  const subtotal = resolved.reduce((sum, r) => sum + r.variant.price * r.item.quantity, 0);

  return { variantInfo, resolved, isResolved, subtotal };
}
