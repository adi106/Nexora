import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { Link } from "react-router-dom";
import { becomeSeller, getMySeller, getMySellerStats } from "../../api/sellers";
import { LoadingSpinner } from "../../components/LoadingSpinner";
import { ErrorMessage } from "../../components/ErrorMessage";
import { extractErrorMessage } from "../../api/client";
import { formatPrice } from "../../utils/format";
import { useAuth } from "../../hooks/useAuth";
import type { Seller, SellerStats } from "../../types";

export function SellerDashboardPage() {
  const { refreshUser } = useAuth();
  const [seller, setSeller] = useState<Seller | null | undefined>(undefined);
  const [stats, setStats] = useState<SellerStats | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getMySeller()
      .then(setSeller)
      .catch((err) => setError(extractErrorMessage(err)));
  }, []);

  useEffect(() => {
    if (seller) {
      getMySellerStats().then(setStats).catch(() => setStats(null));
    }
  }, [seller]);

  async function handleOnboarded(newSeller: Seller) {
    setSeller(newSeller);
    await refreshUser();
  }

  if (seller === undefined) return <LoadingSpinner label="Loading seller dashboard..." />;
  if (error) return <ErrorMessage message={error} />;

  if (seller === null) {
    return <SellerOnboardingForm onCreated={handleOnboarded} />;
  }

  return (
    <div className="page seller-dashboard">
      <h1>{seller.store_name}</h1>
      <p className="hint">Seller dashboard</p>

      <div className="stats-grid">
        <div className="stat-tile">
          <span className="stat-label">Revenue</span>
          <span className="stat-value">{stats ? formatPrice(stats.total_revenue) : "—"}</span>
        </div>
        <div className="stat-tile">
          <span className="stat-label">Orders</span>
          <span className="stat-value">{stats?.order_count ?? "—"}</span>
        </div>
        <div className="stat-tile">
          <span className="stat-label">Products</span>
          <span className="stat-value">{stats?.product_count ?? "—"}</span>
        </div>
        <div className="stat-tile">
          <span className="stat-label">Customers</span>
          <span className="stat-value">{stats?.customer_count ?? "—"}</span>
        </div>
      </div>

      <div className="dashboard-links">
        <Link to="/seller/products" className="button primary">
          Manage products
        </Link>
        <Link to="/seller/orders" className="button">
          View orders
        </Link>
      </div>
    </div>
  );
}

function SellerOnboardingForm({ onCreated }: { onCreated: (seller: Seller) => void }) {
  const [storeName, setStoreName] = useState("");
  const [storeSlug, setStoreSlug] = useState("");
  const [description, setDescription] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);
    try {
      const seller = await becomeSeller({
        store_name: storeName,
        store_slug: storeSlug,
        description: description || null,
      });
      onCreated(seller);
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="page auth-page">
      <form className="auth-form" onSubmit={handleSubmit}>
        <h1>Become a seller</h1>
        <p className="hint">Set up your store to start listing products on NEXORA.</p>
        {error && <ErrorMessage message={error} />}
        <label>
          Store name
          <input required value={storeName} onChange={(e) => setStoreName(e.target.value)} />
        </label>
        <label>
          Store URL slug
          <input
            required
            value={storeSlug}
            onChange={(e) => setStoreSlug(e.target.value.toLowerCase().replace(/\s+/g, "-"))}
          />
        </label>
        <label>
          Description (optional)
          <textarea rows={3} value={description} onChange={(e) => setDescription(e.target.value)} />
        </label>
        <button type="submit" className="button primary" disabled={isSubmitting}>
          {isSubmitting ? "Creating store..." : "Create store"}
        </button>
      </form>
    </div>
  );
}
