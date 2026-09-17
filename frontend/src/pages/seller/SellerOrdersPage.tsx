import { useEffect, useState } from "react";
import { listMySellerOrders } from "../../api/sellers";
import { updateOrderStatus } from "../../api/sellerCatalog";
import { LoadingSpinner } from "../../components/LoadingSpinner";
import { ErrorMessage } from "../../components/ErrorMessage";
import { extractErrorMessage } from "../../api/client";
import { formatDate, formatPrice } from "../../utils/format";
import type { Order, OrderStatus } from "../../types";

const NEXT_STATUSES: Partial<Record<OrderStatus, OrderStatus[]>> = {
  paid: ["shipped", "cancelled"],
  shipped: ["delivered"],
};

export function SellerOrdersPage() {
  const [orders, setOrders] = useState<Order[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busyOrderId, setBusyOrderId] = useState<string | null>(null);

  function load() {
    setIsLoading(true);
    listMySellerOrders()
      .then(setOrders)
      .catch((err) => setError(extractErrorMessage(err)))
      .finally(() => setIsLoading(false));
  }

  useEffect(load, []);

  async function handleTransition(order: Order, newStatus: OrderStatus) {
    setBusyOrderId(order.id);
    setError(null);
    try {
      await updateOrderStatus(order.id, newStatus);
      load();
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setBusyOrderId(null);
    }
  }

  if (isLoading) return <LoadingSpinner label="Loading orders..." />;

  return (
    <div className="page">
      <h1>Orders</h1>
      {error && <ErrorMessage message={error} />}

      {orders.length === 0 ? (
        <p className="empty-state">No orders yet.</p>
      ) : (
        <ul className="order-list">
          {orders.map((order) => {
            const nextStatuses = NEXT_STATUSES[order.status] ?? [];
            return (
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
                {nextStatuses.length > 0 && (
                  <div className="table-actions">
                    {nextStatuses.map((next) => (
                      <button
                        key={next}
                        type="button"
                        className="button"
                        disabled={busyOrderId === order.id}
                        onClick={() => handleTransition(order, next)}
                      >
                        Mark as {next}
                      </button>
                    ))}
                  </div>
                )}
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
