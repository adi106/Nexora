import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getAdminStats } from "../../api/admin";
import type { AdminStats } from "../../api/admin";
import { LoadingSpinner } from "../../components/LoadingSpinner";
import { ErrorMessage } from "../../components/ErrorMessage";
import { extractErrorMessage } from "../../api/client";
import { formatPrice } from "../../utils/format";

export function AdminDashboardPage() {
  const [stats, setStats] = useState<AdminStats | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getAdminStats()
      .then(setStats)
      .catch((err) => setError(extractErrorMessage(err)));
  }, []);

  if (error) return <ErrorMessage message={error} />;
  if (!stats) return <LoadingSpinner label="Loading platform stats..." />;

  return (
    <div className="page">
      <h1>Admin Dashboard</h1>

      <div className="stats-grid">
        <div className="stat-tile">
          <span className="stat-label">Platform revenue</span>
          <span className="stat-value">{formatPrice(stats.total_revenue)}</span>
        </div>
        <div className="stat-tile">
          <span className="stat-label">Fulfilled orders</span>
          <span className="stat-value">{stats.order_count}</span>
        </div>
        <div className="stat-tile">
          <span className="stat-label">Users</span>
          <span className="stat-value">{stats.user_count}</span>
        </div>
        <div className="stat-tile">
          <span className="stat-label">Sellers</span>
          <span className="stat-value">{stats.seller_count}</span>
        </div>
        <div className="stat-tile">
          <span className="stat-label">Products</span>
          <span className="stat-value">{stats.product_count}</span>
        </div>
      </div>

      <div className="dashboard-links">
        <Link to="/admin/users" className="button">
          Users
        </Link>
        <Link to="/admin/sellers" className="button">
          Sellers
        </Link>
        <Link to="/admin/products" className="button">
          Products
        </Link>
        <Link to="/admin/categories" className="button">
          Categories
        </Link>
        <Link to="/admin/orders" className="button">
          Orders
        </Link>
      </div>
    </div>
  );
}
