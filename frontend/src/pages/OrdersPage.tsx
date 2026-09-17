import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { listOrders } from "../api/orders";
import { LoadingSpinner } from "../components/LoadingSpinner";
import { ErrorMessage } from "../components/ErrorMessage";
import { extractErrorMessage } from "../api/client";
import { formatDate, formatPrice } from "../utils/format";
import type { Order } from "../types";

export function OrdersPage() {
  const [orders, setOrders] = useState<Order[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listOrders()
      .then(setOrders)
      .catch((err) => setError(extractErrorMessage(err)))
      .finally(() => setIsLoading(false));
  }, []);

  if (isLoading) return <LoadingSpinner label="Loading orders..." />;
  if (error) return <ErrorMessage message={error} />;

  return (
    <div className="page">
      <h1>My Orders</h1>
      {orders.length === 0 ? (
        <div className="empty-state">
          <p>You haven't placed any orders yet.</p>
          <Link to="/products" className="button primary">
            Start shopping
          </Link>
        </div>
      ) : (
        <ul className="order-list">
          {orders.map((order) => (
            <li key={order.id} className="order-card">
              <div className="order-card-header">
                <span>Order placed {formatDate(order.created_at)}</span>
                <span className={`order-status status-${order.status}`}>{order.status}</span>
              </div>
              <ul className="order-items">
                {order.items.map((item) => (
                  <li key={item.id}>
                    {item.product_name} × {item.quantity} — {formatPrice(item.subtotal)}
                  </li>
                ))}
              </ul>
              <p className="order-total">Total: {formatPrice(order.total_amount)}</p>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
