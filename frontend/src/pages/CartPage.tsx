import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { useCart } from "../hooks/useCart";
import { getVariant } from "../api/products";
import { LoadingSpinner } from "../components/LoadingSpinner";
import { ErrorMessage } from "../components/ErrorMessage";
import { extractErrorMessage } from "../api/client";
import { formatPrice } from "../utils/format";
import type { CartItem, VariantWithProduct } from "../types";

export function CartPage() {
  const { cart, isLoading, updateItem, removeItem } = useCart();
  const [variantInfo, setVariantInfo] = useState<Record<string, VariantWithProduct>>({});
  const [error, setError] = useState<string | null>(null);
  const [busyItemId, setBusyItemId] = useState<string | null>(null);

  useEffect(() => {
    if (!cart) return;
    let cancelled = false;

    async function loadVariants(items: CartItem[]) {
      const missing = items.filter((item) => !(item.variant_id in variantInfo));
      if (missing.length === 0) return;
      try {
        const results = await Promise.all(missing.map((item) => getVariant(item.variant_id)));
        if (cancelled) return;
        setVariantInfo((prev) => {
          const next = { ...prev };
          results.forEach((variant) => {
            next[variant.id] = variant;
          });
          return next;
        });
      } catch (err) {
        if (!cancelled) setError(extractErrorMessage(err));
      }
    }

    loadVariants(cart.items);
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [cart]);

  const subtotal = useMemo(() => {
    if (!cart) return 0;
    return cart.items.reduce((sum, item) => {
      const info = variantInfo[item.variant_id];
      return sum + (info ? info.price * item.quantity : 0);
    }, 0);
  }, [cart, variantInfo]);

  async function handleQuantityChange(item: CartItem, quantity: number) {
    if (quantity < 1) return;
    setBusyItemId(item.id);
    setError(null);
    try {
      await updateItem(item.id, quantity);
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setBusyItemId(null);
    }
  }

  async function handleRemove(item: CartItem) {
    setBusyItemId(item.id);
    setError(null);
    try {
      await removeItem(item.id);
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setBusyItemId(null);
    }
  }

  if (isLoading && !cart) return <LoadingSpinner label="Loading cart..." />;

  const items = cart?.items ?? [];

  return (
    <div className="page cart-page">
      <h1>Your Cart</h1>
      {error && <ErrorMessage message={error} />}

      {items.length === 0 ? (
        <div className="empty-state">
          <p>Your cart is empty.</p>
          <Link to="/products" className="button primary">
            Continue shopping
          </Link>
        </div>
      ) : (
        <>
          <ul className="cart-items">
            {items.map((item) => {
              const info = variantInfo[item.variant_id];
              const isBusy = busyItemId === item.id;
              const overStock = info ? item.quantity > info.available_quantity : false;
              return (
                <li key={item.id} className="cart-item">
                  <div className="cart-item-info">
                    <p className="cart-item-name">
                      {info ? (
                        <Link to={`/products/${info.product_id}`}>{info.product_name}</Link>
                      ) : (
                        "Loading item..."
                      )}
                    </p>
                    {info && Object.keys(info.attributes).length > 0 && (
                      <p className="cart-item-attributes">{Object.values(info.attributes).join(" / ")}</p>
                    )}
                    {overStock && <p className="stock-status out-of-stock">Only {info?.available_quantity} left in stock</p>}
                  </div>

                  <div className="cart-item-quantity">
                    <button
                      type="button"
                      disabled={isBusy || item.quantity <= 1}
                      onClick={() => handleQuantityChange(item, item.quantity - 1)}
                    >
                      -
                    </button>
                    <span>{item.quantity}</span>
                    <button
                      type="button"
                      disabled={isBusy}
                      onClick={() => handleQuantityChange(item, item.quantity + 1)}
                    >
                      +
                    </button>
                  </div>

                  <p className="cart-item-price">{info ? formatPrice(info.price * item.quantity) : "—"}</p>

                  <button
                    type="button"
                    className="link-button"
                    disabled={isBusy}
                    onClick={() => handleRemove(item)}
                  >
                    Remove
                  </button>
                </li>
              );
            })}
          </ul>

          <div className="cart-summary">
            <p className="cart-subtotal">
              Subtotal: <strong>{formatPrice(subtotal)}</strong>
            </p>
            <button type="button" className="button primary" title="Checkout arrives in Phase 7" disabled>
              Proceed to Checkout
            </button>
            <p className="hint">Checkout &amp; payments are coming in Phase 7.</p>
          </div>
        </>
      )}
    </div>
  );
}
