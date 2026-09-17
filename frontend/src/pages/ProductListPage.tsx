import { useEffect, useMemo, useState } from "react";
import type { FormEvent } from "react";
import { useSearchParams } from "react-router-dom";
import { listProducts } from "../api/products";
import { listCategories } from "../api/categories";
import { ProductCard } from "../components/ProductCard";
import { LoadingSpinner } from "../components/LoadingSpinner";
import { ErrorMessage } from "../components/ErrorMessage";
import { extractErrorMessage } from "../api/client";
import type { Category, Product, ProductSort } from "../types";

const PAGE_SIZE = 12;

const SORT_OPTIONS: { value: ProductSort; label: string }[] = [
  { value: "newest", label: "Relevance / Newest" },
  { value: "price_asc", label: "Price: Low to High" },
  { value: "price_desc", label: "Price: High to Low" },
];

export function ProductListPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [categories, setCategories] = useState<Category[]>([]);
  const [products, setProducts] = useState<Product[]>([]);
  const [total, setTotal] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const search = searchParams.get("search") ?? "";
  const categoryId = searchParams.get("category_id") ?? "";
  const minPrice = searchParams.get("min_price") ?? "";
  const maxPrice = searchParams.get("max_price") ?? "";
  const inStock = searchParams.get("in_stock") === "true";
  const sort = (searchParams.get("sort") as ProductSort | null) ?? "newest";
  const page = Number(searchParams.get("page") ?? "1");

  const [searchDraft, setSearchDraft] = useState(search);
  const [minPriceDraft, setMinPriceDraft] = useState(minPrice);
  const [maxPriceDraft, setMaxPriceDraft] = useState(maxPrice);

  useEffect(() => {
    setSearchDraft(search);
    setMinPriceDraft(minPrice);
    setMaxPriceDraft(maxPrice);
  }, [search, minPrice, maxPrice]);

  useEffect(() => {
    listCategories().then(setCategories).catch(() => setCategories([]));
  }, []);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setIsLoading(true);
      setError(null);
      try {
        const data = await listProducts({
          page,
          page_size: PAGE_SIZE,
          sort,
          search: search || undefined,
          category_id: categoryId ? Number(categoryId) : undefined,
          min_price: minPrice ? Number(minPrice) : undefined,
          max_price: maxPrice ? Number(maxPrice) : undefined,
          in_stock: inStock || undefined,
        });
        if (cancelled) return;
        setProducts(data.items);
        setTotal(data.total);
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
  }, [page, sort, search, categoryId, minPrice, maxPrice, inStock]);

  const totalPages = useMemo(() => Math.max(1, Math.ceil(total / PAGE_SIZE)), [total]);

  function updateParams(updates: Record<string, string | undefined>) {
    const next = new URLSearchParams(searchParams);
    for (const [key, value] of Object.entries(updates)) {
      if (value) {
        next.set(key, value);
      } else {
        next.delete(key);
      }
    }
    if (!("page" in updates)) {
      next.delete("page");
    }
    setSearchParams(next);
  }

  function handleFilterSubmit(event: FormEvent) {
    event.preventDefault();
    updateParams({ search: searchDraft || undefined, min_price: minPriceDraft || undefined, max_price: maxPriceDraft || undefined });
  }

  return (
    <div className="page product-list-page">
      <aside className="filters">
        <form onSubmit={handleFilterSubmit}>
          <h2>Filters</h2>
          <label>
            Search
            <input
              type="text"
              value={searchDraft}
              onChange={(event) => setSearchDraft(event.target.value)}
              placeholder="Product name or description"
            />
          </label>

          <label>
            Category
            <select
              value={categoryId}
              onChange={(event) => updateParams({ category_id: event.target.value || undefined })}
            >
              <option value="">All categories</option>
              {categories.map((category) => (
                <option key={category.id} value={category.id}>
                  {category.name}
                </option>
              ))}
            </select>
          </label>

          <div className="form-row">
            <label>
              Min price
              <input
                type="number"
                min={0}
                value={minPriceDraft}
                onChange={(event) => setMinPriceDraft(event.target.value)}
              />
            </label>
            <label>
              Max price
              <input
                type="number"
                min={0}
                value={maxPriceDraft}
                onChange={(event) => setMaxPriceDraft(event.target.value)}
              />
            </label>
          </div>

          <label className="checkbox-label">
            <input
              type="checkbox"
              checked={inStock}
              onChange={(event) => updateParams({ in_stock: event.target.checked ? "true" : undefined })}
            />
            In stock only
          </label>

          <button type="submit" className="button primary">
            Apply filters
          </button>
        </form>
      </aside>

      <section className="product-list-results">
        <div className="results-toolbar">
          <p>{total} products found</p>
          <label className="sort-select">
            Sort by
            <select value={sort} onChange={(event) => updateParams({ sort: event.target.value })}>
              {SORT_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
        </div>

        {isLoading && <LoadingSpinner label="Loading products..." />}
        {error && <ErrorMessage message={error} />}

        {!isLoading && !error && products.length === 0 && (
          <p className="empty-state">No products match your filters.</p>
        )}

        {!isLoading && !error && products.length > 0 && (
          <>
            <div className="product-grid">
              {products.map((product) => (
                <ProductCard key={product.id} product={product} />
              ))}
            </div>
            <div className="pagination">
              <button
                type="button"
                disabled={page <= 1}
                onClick={() => updateParams({ page: String(page - 1) })}
              >
                Previous
              </button>
              <span>
                Page {page} of {totalPages}
              </span>
              <button
                type="button"
                disabled={page >= totalPages}
                onClick={() => updateParams({ page: String(page + 1) })}
              >
                Next
              </button>
            </div>
          </>
        )}
      </section>
    </div>
  );
}
