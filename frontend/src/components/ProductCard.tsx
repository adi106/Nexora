import { Link } from "react-router-dom";
import type { Product } from "../types";
import { formatPrice } from "../utils/format";
import { useAuth } from "../hooks/useAuth";
import { useWishlist } from "../hooks/useWishlist";

export function ProductCard({ product }: { product: Product }) {
  const { isAuthenticated } = useAuth();
  const { productIds, toggle } = useWishlist();
  const isWishlisted = productIds.has(product.id);

  return (
    <div className="product-card">
      <Link to={`/products/${product.id}`} className="product-card-link">
        <div className="product-card-image" aria-hidden="true">
          {product.name.charAt(0).toUpperCase()}
        </div>
        <h3 className="product-card-name">{product.name}</h3>
        <p className="product-card-price">{formatPrice(product.base_price)}</p>
      </Link>
      {isAuthenticated && (
        <button
          type="button"
          className={isWishlisted ? "wishlist-toggle active" : "wishlist-toggle"}
          aria-label={isWishlisted ? "Remove from wishlist" : "Add to wishlist"}
          onClick={() => toggle(product.id)}
        >
          {isWishlisted ? "♥" : "♡"}
        </button>
      )}
    </div>
  );
}
