import { useEffect, useState } from "react";
import { listAdminProducts, setProductActiveAdmin } from "../../api/admin";
import { LoadingSpinner } from "../../components/LoadingSpinner";
import { ErrorMessage } from "../../components/ErrorMessage";
import { extractErrorMessage } from "../../api/client";
import { formatPrice } from "../../utils/format";
import type { Product } from "../../types";

export function AdminProductsPage() {
  const [products, setProducts] = useState<Product[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);

  function load() {
    setIsLoading(true);
    listAdminProducts()
      .then((data) => setProducts(data.items))
      .catch((err) => setError(extractErrorMessage(err)))
      .finally(() => setIsLoading(false));
  }

  useEffect(load, []);

  async function toggleActive(product: Product) {
    setBusyId(product.id);
    setError(null);
    try {
      await setProductActiveAdmin(product.id, !product.is_active);
      load();
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setBusyId(null);
    }
  }

  if (isLoading) return <LoadingSpinner label="Loading products..." />;

  return (
    <div className="page">
      <h1>All Products</h1>
      <p className="hint">Moderate any product on the platform, regardless of seller.</p>
      {error && <ErrorMessage message={error} />}

      <table className="data-table">
        <thead>
          <tr>
            <th>Name</th>
            <th>Seller ID</th>
            <th>Price</th>
            <th>Status</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {products.map((product) => (
            <tr key={product.id}>
              <td>{product.name}</td>
              <td>{product.seller_id}</td>
              <td>{formatPrice(product.base_price)}</td>
              <td>
                <span className={product.is_active ? "badge active" : "badge inactive"}>
                  {product.is_active ? "Active" : "Inactive"}
                </span>
              </td>
              <td>
                <button
                  type="button"
                  className="link-button"
                  disabled={busyId === product.id}
                  onClick={() => toggleActive(product)}
                >
                  {product.is_active ? "Deactivate" : "Activate"}
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
