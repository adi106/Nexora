import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { listMyProducts } from "../../api/sellers";
import { setProductActive } from "../../api/sellerCatalog";
import { LoadingSpinner } from "../../components/LoadingSpinner";
import { ErrorMessage } from "../../components/ErrorMessage";
import { extractErrorMessage } from "../../api/client";
import { formatPrice } from "../../utils/format";
import type { Product } from "../../types";

export function SellerProductsPage() {
  const [products, setProducts] = useState<Product[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);

  function load() {
    setIsLoading(true);
    listMyProducts()
      .then((data) => setProducts(data.items))
      .catch((err) => setError(extractErrorMessage(err)))
      .finally(() => setIsLoading(false));
  }

  useEffect(load, []);

  async function toggleActive(product: Product) {
    setBusyId(product.id);
    try {
      await setProductActive(product.id, !product.is_active);
      load();
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setBusyId(null);
    }
  }

  if (isLoading) return <LoadingSpinner label="Loading your products..." />;

  return (
    <div className="page">
      <div className="page-header-row">
        <h1>My Products</h1>
        <Link to="/seller/products/new" className="button primary">
          + New product
        </Link>
      </div>
      {error && <ErrorMessage message={error} />}

      {products.length === 0 ? (
        <p className="empty-state">You haven't listed any products yet.</p>
      ) : (
        <table className="data-table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Price</th>
              <th>Status</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {products.map((product) => (
              <tr key={product.id}>
                <td>{product.name}</td>
                <td>{formatPrice(product.base_price)}</td>
                <td>
                  <span className={product.is_active ? "badge active" : "badge inactive"}>
                    {product.is_active ? "Active" : "Inactive"}
                  </span>
                </td>
                <td className="table-actions">
                  <Link to={`/seller/products/${product.id}`}>Edit</Link>
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
      )}
    </div>
  );
}
