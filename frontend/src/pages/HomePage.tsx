import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { listCategories } from "../api/categories";
import { listProducts } from "../api/products";
import { getRecommendations } from "../api/recommendations";
import { ProductCard } from "../components/ProductCard";
import { LoadingSpinner } from "../components/LoadingSpinner";
import { ErrorMessage } from "../components/ErrorMessage";
import { extractErrorMessage } from "../api/client";
import { useAuth } from "../hooks/useAuth";
import type { Category, Product } from "../types";

export function HomePage() {
  const { isAuthenticated } = useAuth();
  const [categories, setCategories] = useState<Category[]>([]);
  const [newArrivals, setNewArrivals] = useState<Product[]>([]);
  const [recommended, setRecommended] = useState<Product[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setIsLoading(true);
      setError(null);
      try {
        const [categoriesData, productsData] = await Promise.all([
          listCategories(),
          listProducts({ sort: "newest", page_size: 8 }),
        ]);
        if (cancelled) return;
        setCategories(categoriesData);
        setNewArrivals(productsData.items);

        if (isAuthenticated) {
          const recommendations = await getRecommendations(8);
          if (!cancelled) setRecommended(recommendations);
        } else {
          setRecommended([]);
        }
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
  }, [isAuthenticated]);

  if (isLoading) return <LoadingSpinner label="Loading storefront..." />;
  if (error) return <ErrorMessage message={error} />;

  return (
    <div className="page home-page">
      <section className="hero-banner">
        <h1>Shop everything on NEXORA</h1>
        <p>Discover products across every category, curated for you.</p>
        <Link to="/products" className="button primary">
          Browse all products
        </Link>
      </section>

      <section className="section">
        <h2>Categories</h2>
        <div className="category-grid">
          {categories.map((category) => (
            <Link key={category.id} to={`/products?category_id=${category.id}`} className="category-chip">
              {category.name}
            </Link>
          ))}
          {categories.length === 0 && <p className="empty-state">No categories yet.</p>}
        </div>
      </section>

      {isAuthenticated && (
        <section className="section">
          <h2>Recommended for you</h2>
          {recommended.length === 0 ? (
            <p className="empty-state">
              Browse a few products and we'll start tailoring recommendations for you.
            </p>
          ) : (
            <div className="product-grid">
              {recommended.map((product) => (
                <ProductCard key={product.id} product={product} />
              ))}
            </div>
          )}
        </section>
      )}

      <section className="section">
        <h2>New arrivals</h2>
        {newArrivals.length === 0 ? (
          <p className="empty-state">No products yet.</p>
        ) : (
          <div className="product-grid">
            {newArrivals.map((product) => (
              <ProductCard key={product.id} product={product} />
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
