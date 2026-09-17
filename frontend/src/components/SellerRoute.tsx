import type { ReactNode } from "react";
import { Navigate } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";
import { LoadingSpinner } from "./LoadingSpinner";

export function SellerRoute({ children }: { children: ReactNode }) {
  const { isAuthenticated, isSeller, isLoading } = useAuth();

  if (isLoading) return <LoadingSpinner label="Checking session..." />;
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  if (!isSeller) return <Navigate to="/seller" replace />;

  return <>{children}</>;
}
