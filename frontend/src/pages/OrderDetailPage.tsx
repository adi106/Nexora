import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { getOrder } from "../api/orders";
import { LoadingSpinner } from "../components/LoadingSpinner";
import { ErrorMessage } from "../components/ErrorMessage";
import { extractErrorMessage } from "../api/client";
import { formatDate, formatPrice } from "../utils/format";
import type { Order } from "../types";

export function OrderDetailPage() {
  const { orderId } = useParams<{ orderId: string }>();
  const [order, setOrder] = useState<Order | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!orderId) return;
    getOrder(orderId)
      .then(setOrder)
      .catch((err) => setError(extractErrorMessage(err)))
      .finally(() => setIsLoading(false));
  }, [orderId]);

  if (isLoading) return <LoadingSpinner label="Loading order..." />;
  if (error) return <ErrorMessage message={error} />;
  if (!order) return <ErrorMessage message="Order not found." />;

  return (
    <div className="page order-detail-page">
      {order.status === "paid" && (
        <div className="order-confirmation-banner">✓ Order confirmed — thank you for shopping with NEXORA!</div>
      )}
      {order.status === "cancelled" && (
        <div className="order-confirmation-banner failed">Payment was declined and this order was cancelled.</div>
      )}

      <h1>Order details</h1>
      <p className="hint">Placed {formatDate(order.created_at)}</p>
      <span className={`order-status status-${order.status}`}>{order.status}</span>

      <section className="section">
        <h2>Items</h2>
        <ul className="order-items">
          {order.items.map((item) => (
            <li key={item.id}>
              {item.product_name} ({item.sku}) × {item.quantity} — {formatPrice(item.subtotal)}
            </li>
          ))}
        </ul>
        <p className="order-total">Total: {formatPrice(order.total_amount)}</p>
      </section>

      <section className="section">
        <h2>Shipping to</h2>
        <p>
          {order.shipping_full_name}
          <br />
          {order.shipping_address_line1}
          {order.shipping_address_line2 ? <>, {order.shipping_address_line2}</> : null}
          <br />
          {order.shipping_city}
          {order.shipping_region ? `, ${order.shipping_region}` : ""} {order.shipping_postal_code}
          <br />
          {order.shipping_country_code}
        </p>
      </section>

      <Link to="/orders" className="button">
        View all orders
      </Link>
    </div>
  );
}
