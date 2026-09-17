import { apiClient } from "./client";
import type { ProductRating, Review } from "../types";

export async function listProductReviews(productId: string): Promise<Review[]> {
  const { data } = await apiClient.get<Review[]>(`/reviews/products/${productId}`);
  return data;
}

export async function getProductRating(productId: string): Promise<ProductRating> {
  const { data } = await apiClient.get<ProductRating>(`/reviews/products/${productId}/rating`);
  return data;
}

export async function createReview(
  productId: string,
  rating: number,
  comment: string | null,
): Promise<Review> {
  const { data } = await apiClient.post<Review>(`/reviews/products/${productId}`, {
    rating,
    comment,
  });
  return data;
}

export async function updateReview(
  reviewId: string,
  rating: number,
  comment: string | null,
): Promise<Review> {
  const { data } = await apiClient.put<Review>(`/reviews/${reviewId}`, { rating, comment });
  return data;
}

export async function deleteReview(reviewId: string): Promise<void> {
  await apiClient.delete(`/reviews/${reviewId}`);
}
