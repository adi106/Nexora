export interface User {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  roles: string[];
}

export interface Category {
  id: number;
  name: string;
  slug: string;
  description: string | null;
  parent_id: number | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface Product {
  id: string;
  seller_id: number;
  category_id: number;
  name: string;
  slug: string;
  description: string | null;
  base_price: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface ProductVariant {
  id: string;
  product_id: string;
  sku: string;
  price: number;
  attributes: Record<string, string>;
  is_active: boolean;
  available_quantity: number;
}

export interface ProductDetail extends Product {
  variants: ProductVariant[];
}

export interface VariantWithProduct {
  id: string;
  product_id: string;
  product_name: string;
  product_slug: string;
  sku: string;
  price: number;
  attributes: Record<string, string>;
  is_active: boolean;
  available_quantity: number;
}

export interface ProductListResponse {
  items: Product[];
  total: number;
  page: number;
  page_size: number;
}

export type ProductSort = "newest" | "price_asc" | "price_desc";

export interface ProductSearchParams {
  page?: number;
  page_size?: number;
  sort?: ProductSort;
  category_id?: number;
  seller_id?: number;
  min_price?: number;
  max_price?: number;
  in_stock?: boolean;
  search?: string;
}

export type CartStatus = "active" | "converted" | "abandoned";

export interface CartItem {
  id: string;
  cart_id: string;
  variant_id: string;
  quantity: number;
  created_at: string;
  updated_at: string;
}

export interface Cart {
  id: string;
  user_id: string;
  status: CartStatus;
  created_at: string;
  updated_at: string;
  items: CartItem[];
}

export type OrderStatus = "pending" | "paid" | "shipped" | "delivered" | "cancelled";

export interface OrderItem {
  id: string;
  variant_id: string | null;
  product_name: string;
  sku: string;
  unit_price: number;
  quantity: number;
  subtotal: number;
}

export interface Order {
  id: string;
  user_id: string;
  status: OrderStatus;
  total_amount: number;
  shipping_full_name: string;
  shipping_address_line1: string;
  shipping_address_line2: string | null;
  shipping_city: string;
  shipping_region: string | null;
  shipping_postal_code: string;
  shipping_country_code: string;
  created_at: string;
  updated_at: string;
  reservation_expires_at: string | null;
  items: OrderItem[];
}

export interface Review {
  id: string;
  user_id: string;
  product_id: string;
  rating: number;
  comment: string | null;
  created_at: string;
  updated_at: string;
}

export interface ProductRating {
  average_rating: number;
  review_count: number;
}

export interface WishlistItem {
  id: string;
  user_id: string;
  product_id: string;
  created_at: string;
}

export interface ApiError {
  detail: string | { msg: string; loc: (string | number)[] }[];
}
