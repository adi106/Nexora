import { useEffect, useState } from "react";
import { listAdminSellers, setSellerActive } from "../../api/admin";
import { LoadingSpinner } from "../../components/LoadingSpinner";
import { ErrorMessage } from "../../components/ErrorMessage";
import { extractErrorMessage } from "../../api/client";
import type { Seller } from "../../types";

export function AdminSellersPage() {
  const [sellers, setSellers] = useState<Seller[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<number | null>(null);

  function load() {
    setIsLoading(true);
    listAdminSellers()
      .then((data) => setSellers(data.items))
      .catch((err) => setError(extractErrorMessage(err)))
      .finally(() => setIsLoading(false));
  }

  useEffect(load, []);

  async function toggleActive(seller: Seller) {
    setBusyId(seller.id);
    setError(null);
    try {
      await setSellerActive(seller.id, !seller.is_active);
      load();
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setBusyId(null);
    }
  }

  if (isLoading) return <LoadingSpinner label="Loading sellers..." />;

  return (
    <div className="page">
      <h1>Sellers</h1>
      {error && <ErrorMessage message={error} />}

      <table className="data-table">
        <thead>
          <tr>
            <th>Store</th>
            <th>Slug</th>
            <th>Status</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {sellers.map((seller) => (
            <tr key={seller.id}>
              <td>{seller.store_name}</td>
              <td>{seller.store_slug}</td>
              <td>
                <span className={seller.is_active ? "badge active" : "badge inactive"}>
                  {seller.is_active ? "Active" : "Suspended"}
                </span>
              </td>
              <td>
                <button
                  type="button"
                  className="link-button"
                  disabled={busyId === seller.id}
                  onClick={() => toggleActive(seller)}
                >
                  {seller.is_active ? "Suspend" : "Reactivate"}
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
