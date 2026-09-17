import { useState } from "react";
import { Link } from "react-router-dom";
import { useCart } from "../hooks/useCart";
import { useResolvedCartItems } from "../hooks/useResolvedCartItems";
import { LoadingSpinner } from "../components/LoadingSpinner";
import { ErrorMessage } from "../components/ErrorMessage";
import { extractErrorMessage } from "../api/client";
import { formatPrice } from "../utils/format";
import type { CartItem } from "../types";

export function CartPage() {
  const { cart, isLoading, updateItem, removeItem } = useCart();
  const items = cart?.items ?? [];
  const { resolved, subtotal } = useResolvedCartItems(items);
  const [error, setError] = useState<string | null>(null);
  const [busyItemId, setBusyItemId] = useState<string | null>(null);

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
            {resolved.map(({ item, variant: info }) => {
              const isBusy = busyItemId === item.id;
              const overStock = item.quantity > info.available_quantity;
              return (
                <li key={item.id} className="cart-item">
                  <div className="cart-item-info">
                    <p className="cart-item-name">
                      <Link to={`/products/${info.product_id}`}>{info.product_name}</Link>
                    </p>
                    {Object.keys(info.attributes).length > 0 && (
                      <p className="cart-item-attributes">{Object.values(info.attributes).join(" / ")}</p>
                    )}
                    {overStock && (
                      <p className="stock-status out-of-stock">Only {info.available_quantity} left in stock</p>
                    )}
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

                  <p className="cart-item-price">{formatPrice(info.price * item.quantity)}</p>

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
            <Link to="/checkout" className="button primary">
              Proceed to Checkout
            </Link>
          </div>
        </>
      )}
    </div>
  );
}
