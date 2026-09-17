import { useCallback, useEffect, useState } from "react";
import type { FormEvent } from "react";
import { useParams } from "react-router-dom";
import { getProduct } from "../api/products";
import { getRecommendations, recordProductView } from "../api/recommendations";
import {
  createReview,
  deleteReview,
  getProductRating,
  listProductReviews,
  updateReview,
} from "../api/reviews";
import { ProductCard } from "../components/ProductCard";
import { LoadingSpinner } from "../components/LoadingSpinner";
import { ErrorMessage } from "../components/ErrorMessage";
import { StarRating } from "../components/StarRating";
import { extractErrorMessage } from "../api/client";
import { formatDate, formatPrice } from "../utils/format";
import { useAuth } from "../hooks/useAuth";
import { useCart } from "../hooks/useCart";
import { useWishlist } from "../hooks/useWishlist";
import type { Product, ProductDetail, ProductRating, ProductVariant, Review } from "../types";

export function ProductDetailPage() {
  const { productId } = useParams<{ productId: string }>();
  const { isAuthenticated, user } = useAuth();
  const { addItem } = useCart();
  const { productIds, toggle } = useWishlist();

  const [product, setProduct] = useState<ProductDetail | null>(null);
  const [selectedVariant, setSelectedVariant] = useState<ProductVariant | null>(null);
  const [reviews, setReviews] = useState<Review[]>([]);
  const [rating, setRating] = useState<ProductRating | null>(null);
  const [related, setRelated] = useState<Product[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [addToCartMessage, setAddToCartMessage] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!productId) return;
    setIsLoading(true);
    setError(null);
    try {
      const [productData, reviewsData, ratingData] = await Promise.all([
        getProduct(productId),
        listProductReviews(productId),
        getProductRating(productId),
      ]);
      setProduct(productData);
      setSelectedVariant(productData.variants.find((v) => v.is_active) ?? productData.variants[0] ?? null);
      setReviews(reviewsData);
      setRating(ratingData);

      if (isAuthenticated) {
        recordProductView(productId).catch(() => {});
        const recommendations = await getRecommendations(8);
        setRelated(recommendations.filter((p) => p.id !== productId));
      } else {
        setRelated([]);
      }
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setIsLoading(false);
    }
  }, [productId, isAuthenticated]);

  useEffect(() => {
    load();
  }, [load]);

  async function handleAddToCart() {
    if (!selectedVariant) return;
    setAddToCartMessage(null);
    try {
      await addItem(selectedVariant.id, 1);
      setAddToCartMessage("Added to cart.");
    } catch (err) {
      setAddToCartMessage(extractErrorMessage(err));
    }
  }

  if (isLoading) return <LoadingSpinner label="Loading product..." />;
  if (error) return <ErrorMessage message={error} />;
  if (!product) return <ErrorMessage message="Product not found." />;

  const isWishlisted = productIds.has(product.id);
  const inStock = (selectedVariant?.available_quantity ?? 0) > 0;
  const myReview = user ? reviews.find((r) => r.user_id === user.id) ?? null : null;

  return (
    <div className="page product-detail-page">
      <div className="product-detail-main">
        <div className="product-detail-image" aria-hidden="true">
          {product.name.charAt(0).toUpperCase()}
        </div>

        <div className="product-detail-info">
          <h1>{product.name}</h1>

          {rating && rating.review_count > 0 && (
            <StarRating value={rating.average_rating} count={rating.review_count} />
          )}

          <p className="product-detail-price">
            {formatPrice(selectedVariant?.price ?? product.base_price)}
          </p>

          {product.description && <p className="product-detail-description">{product.description}</p>}

          {product.variants.length > 0 && (
            <div className="variant-picker">
              <span>Variant:</span>
              <div className="variant-options">
                {product.variants
                  .filter((variant) => variant.is_active)
                  .map((variant) => (
                    <button
                      key={variant.id}
                      type="button"
                      className={selectedVariant?.id === variant.id ? "variant-chip selected" : "variant-chip"}
                      onClick={() => setSelectedVariant(variant)}
                    >
                      {Object.values(variant.attributes).join(" / ") || variant.sku}
                    </button>
                  ))}
              </div>
            </div>
          )}

          <p className={inStock ? "stock-status in-stock" : "stock-status out-of-stock"}>
            {inStock ? `✓ In stock (${selectedVariant?.available_quantity})` : "Out of stock"}
          </p>

          <div className="product-actions">
            <button
              type="button"
              className="button primary"
              disabled={!isAuthenticated || !selectedVariant || !inStock}
              onClick={handleAddToCart}
            >
              Add to Cart
            </button>
            {isAuthenticated && (
              <button
                type="button"
                className={isWishlisted ? "button wishlist active" : "button wishlist"}
                onClick={() => toggle(product.id)}
              >
                {isWishlisted ? "♥ In Wishlist" : "♡ Add to Wishlist"}
              </button>
            )}
          </div>

          {!isAuthenticated && <p className="hint">Log in to add items to your cart or wishlist.</p>}
          {addToCartMessage && <p className="hint">{addToCartMessage}</p>}
        </div>
      </div>

      <ReviewsSection
        productId={product.id}
        reviews={reviews}
        myReview={myReview}
        isAuthenticated={isAuthenticated}
        onChanged={load}
      />

      {related.length > 0 && (
        <section className="section">
          <h2>You may also like</h2>
          <div className="product-grid">
            {related.slice(0, 4).map((item) => (
              <ProductCard key={item.id} product={item} />
            ))}
          </div>
        </section>
      )}
    </div>
  );
}

function ReviewsSection({
  productId,
  reviews,
  myReview,
  isAuthenticated,
  onChanged,
}: {
  productId: string;
  reviews: Review[];
  myReview: Review | null;
  isAuthenticated: boolean;
  onChanged: () => void;
}) {
  const [ratingInput, setRatingInput] = useState(myReview?.rating ?? 5);
  const [commentInput, setCommentInput] = useState(myReview?.comment ?? "");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  useEffect(() => {
    setRatingInput(myReview?.rating ?? 5);
    setCommentInput(myReview?.comment ?? "");
  }, [myReview]);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setFormError(null);
    setIsSubmitting(true);
    try {
      if (myReview) {
        await updateReview(myReview.id, ratingInput, commentInput || null);
      } else {
        await createReview(productId, ratingInput, commentInput || null);
      }
      onChanged();
    } catch (err) {
      setFormError(extractErrorMessage(err));
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleDelete() {
    if (!myReview) return;
    setIsSubmitting(true);
    try {
      await deleteReview(myReview.id);
      onChanged();
    } catch (err) {
      setFormError(extractErrorMessage(err));
    } finally {
      setIsSubmitting(false);
    }
  }

  const otherReviews = reviews.filter((r) => r.id !== myReview?.id);

  return (
    <section className="section reviews-section">
      <h2>Reviews ({reviews.length})</h2>

      {isAuthenticated && (
        <form className="review-form" onSubmit={handleSubmit}>
          <h3>{myReview ? "Edit your review" : "Write a review"}</h3>
          {formError && <ErrorMessage message={formError} />}
          <label>
            Rating
            <select value={ratingInput} onChange={(event) => setRatingInput(Number(event.target.value))}>
              {[5, 4, 3, 2, 1].map((value) => (
                <option key={value} value={value}>
                  {value} star{value > 1 ? "s" : ""}
                </option>
              ))}
            </select>
          </label>
          <label>
            Comment
            <textarea
              value={commentInput}
              onChange={(event) => setCommentInput(event.target.value)}
              rows={3}
              placeholder="Share your thoughts on this product..."
            />
          </label>
          <div className="form-row">
            <button type="submit" className="button primary" disabled={isSubmitting}>
              {myReview ? "Update review" : "Submit review"}
            </button>
            {myReview && (
              <button type="button" className="button" onClick={handleDelete} disabled={isSubmitting}>
                Delete review
              </button>
            )}
          </div>
        </form>
      )}

      {reviews.length === 0 ? (
        <p className="empty-state">No reviews yet. Be the first to review this product.</p>
      ) : (
        <ul className="review-list">
          {myReview && (
            <li className="review-item mine">
              <StarRating value={myReview.rating} />
              <span className="review-meta">You · {formatDate(myReview.created_at)}</span>
              {myReview.comment && <p>{myReview.comment}</p>}
            </li>
          )}
          {otherReviews.map((review) => (
            <li key={review.id} className="review-item">
              <StarRating value={review.rating} />
              <span className="review-meta">{formatDate(review.created_at)}</span>
              {review.comment && <p>{review.comment}</p>}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
