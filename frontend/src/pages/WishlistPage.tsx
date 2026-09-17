import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { listWishlist } from "../api/wishlist";
import { getProduct } from "../api/products";
import { ProductCard } from "../components/ProductCard";
import { LoadingSpinner } from "../components/LoadingSpinner";
import { ErrorMessage } from "../components/ErrorMessage";
import { extractErrorMessage } from "../api/client";
import type { ProductDetail } from "../types";

export function WishlistPage() {
  const [products, setProducts] = useState<ProductDetail[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setIsLoading(true);
      setError(null);
      try {
        const items = await listWishlist();
        const results = await Promise.allSettled(items.map((item) => getProduct(item.product_id)));
        if (cancelled) return;
        setProducts(
          results
            .filter((result): result is PromiseFulfilledResult<ProductDetail> => result.status === "fulfilled")
            .map((result) => result.value),
        );
      } catch (err) {
        if (!cancelled) setError(extractErrorMessage(err));
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, []);

  if (isLoading) return <LoadingSpinner label="Loading wishlist..." />;
  if (error) return <ErrorMessage message={error} />;

  return (
    <div className="page">
      <h1>My Wishlist</h1>
      {products.length === 0 ? (
        <div className="empty-state">
          <p>Your wishlist is empty.</p>
          <Link to="/products" className="button primary">
            Browse products
          </Link>
        </div>
      ) : (
        <div className="product-grid">
          {products.map((product) => (
            <ProductCard key={product.id} product={product} />
          ))}
        </div>
      )}
    </div>
  );
}
