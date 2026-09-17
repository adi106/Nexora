import { useEffect, useState } from "react";
import { listAdminOrders } from "../../api/admin";
import { LoadingSpinner } from "../../components/LoadingSpinner";
import { ErrorMessage } from "../../components/ErrorMessage";
import { extractErrorMessage } from "../../api/client";
import { formatDate, formatPrice } from "../../utils/format";
import type { Order } from "../../types";

export function AdminOrdersPage() {
  const [orders, setOrders] = useState<Order[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listAdminOrders()
      .then(setOrders)
      .catch((err) => setError(extractErrorMessage(err)))
      .finally(() => setIsLoading(false));
  }, []);

  if (isLoading) return <LoadingSpinner label="Loading orders..." />;
  if (error) return <ErrorMessage message={error} />;

  return (
    <div className="page">
      <h1>All Orders</h1>

      {orders.length === 0 ? (
        <p className="empty-state">No orders yet.</p>
      ) : (
        <table className="data-table">
          <thead>
            <tr>
              <th>Placed</th>
              <th>Customer</th>
              <th>Total</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {orders.map((order) => (
              <tr key={order.id}>
                <td>{formatDate(order.created_at)}</td>
                <td>{order.shipping_full_name}</td>
                <td>{formatPrice(order.total_amount)}</td>
                <td>
                  <span className={`order-status status-${order.status}`}>{order.status}</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
