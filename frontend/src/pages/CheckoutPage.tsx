import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { createAddress, listAddresses } from "../api/addresses";
import { createOrder, payForOrder } from "../api/orders";
import { useCart } from "../hooks/useCart";
import { useResolvedCartItems } from "../hooks/useResolvedCartItems";
import { AddressForm } from "../components/AddressForm";
import { LoadingSpinner } from "../components/LoadingSpinner";
import { ErrorMessage } from "../components/ErrorMessage";
import { extractErrorMessage } from "../api/client";
import { formatPrice } from "../utils/format";
import type { Address, AddressInput } from "../types";

export function CheckoutPage() {
  const navigate = useNavigate();
  const { cart, refresh: refreshCart } = useCart();
  const items = cart?.items ?? [];
  const { resolved, isResolved, subtotal } = useResolvedCartItems(items);

  const [addresses, setAddresses] = useState<Address[]>([]);
  const [selectedAddressId, setSelectedAddressId] = useState<string | null>(null);
  const [isAddingAddress, setIsAddingAddress] = useState(false);
  const [isLoadingAddresses, setIsLoadingAddresses] = useState(true);
  const [simulateFailure, setSimulateFailure] = useState(false);
  const [isPlacingOrder, setIsPlacingOrder] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listAddresses()
      .then((data) => {
        setAddresses(data);
        const defaultAddress = data.find((a) => a.is_default) ?? data[0];
        if (defaultAddress) setSelectedAddressId(defaultAddress.id);
        setIsAddingAddress(data.length === 0);
      })
      .catch((err) => setError(extractErrorMessage(err)))
      .finally(() => setIsLoadingAddresses(false));
  }, []);

  async function handleAddAddress(payload: AddressInput) {
    setError(null);
    try {
      const address = await createAddress(payload);
      setAddresses((prev) => [address, ...prev]);
      setSelectedAddressId(address.id);
      setIsAddingAddress(false);
    } catch (err) {
      setError(extractErrorMessage(err));
    }
  }

  async function handlePlaceOrder() {
    if (!selectedAddressId) return;
    setError(null);
    setIsPlacingOrder(true);
    try {
      const order = await createOrder(selectedAddressId);
      const paid = await payForOrder(order.id, !simulateFailure);
      await refreshCart();
      navigate(`/orders/${paid.id}`, { replace: true });
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setIsPlacingOrder(false);
    }
  }

  if (items.length === 0) {
    return (
      <div className="page empty-state">
        <h1>Your cart is empty</h1>
        <p>Add some products before checking out.</p>
      </div>
    );
  }

  return (
    <div className="page checkout-page">
      <h1>Checkout</h1>
      {error && <ErrorMessage message={error} />}

      <section className="section">
        <h2>Shipping address</h2>
        {isLoadingAddresses ? (
          <LoadingSpinner label="Loading addresses..." />
        ) : (
          <>
            {addresses.length > 0 && !isAddingAddress && (
              <ul className="address-list">
                {addresses.map((address) => (
                  <li key={address.id}>
                    <label className="address-option">
                      <input
                        type="radio"
                        name="address"
                        checked={selectedAddressId === address.id}
                        onChange={() => setSelectedAddressId(address.id)}
                      />
                      <span>
                        {address.address_line1}
                        {address.address_line2 ? `, ${address.address_line2}` : ""}, {address.city}
                        {address.region ? `, ${address.region}` : ""} {address.postal_code},{" "}
                        {address.country_code}
                        {address.is_default && <em> (default)</em>}
                      </span>
                    </label>
                  </li>
                ))}
              </ul>
            )}

            {isAddingAddress ? (
              <AddressForm
                onSubmit={handleAddAddress}
                onCancel={addresses.length > 0 ? () => setIsAddingAddress(false) : undefined}
                isSubmitting={false}
              />
            ) : (
              <button type="button" className="button" onClick={() => setIsAddingAddress(true)}>
                + Add a new address
              </button>
            )}
          </>
        )}
      </section>

      <section className="section">
        <h2>Order summary</h2>
        {!isResolved ? (
          <LoadingSpinner label="Loading order summary..." />
        ) : (
          <>
            <ul className="order-items">
              {resolved.map(({ item, variant }) => (
                <li key={item.id}>
                  {variant.product_name} × {item.quantity} — {formatPrice(variant.price * item.quantity)}
                </li>
              ))}
            </ul>
            <p className="cart-subtotal">
              Total: <strong>{formatPrice(subtotal)}</strong>
            </p>
          </>
        )}
      </section>

      <section className="section">
        <h2>Payment</h2>
        <p className="hint">
          NEXORA uses a mock payment provider in this environment — no real charge is made.
        </p>
        <label className="checkbox-label">
          <input
            type="checkbox"
            checked={simulateFailure}
            onChange={(event) => setSimulateFailure(event.target.checked)}
          />
          Simulate a declined payment (demo)
        </label>
      </section>

      <button
        type="button"
        className="button primary"
        disabled={!selectedAddressId || !isResolved || isPlacingOrder}
        onClick={handlePlaceOrder}
      >
        {isPlacingOrder ? "Placing order..." : `Place order — ${formatPrice(subtotal)}`}
      </button>
    </div>
  );
}
