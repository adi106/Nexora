import { Link, NavLink, Outlet, useNavigate } from "react-router-dom";
import { useState } from "react";
import type { FormEvent } from "react";
import { useAuth } from "../hooks/useAuth";
import { useCart } from "../hooks/useCart";

export function Layout() {
  const { isAuthenticated, user, isSeller, isAdmin, logout } = useAuth();
  const { itemCount } = useCart();
  const navigate = useNavigate();
  const [query, setQuery] = useState("");

  function handleSearch(event: FormEvent) {
    event.preventDefault();
    const trimmed = query.trim();
    navigate(trimmed ? `/products?search=${encodeURIComponent(trimmed)}` : "/products");
  }

  return (
    <div className="app-shell">
      <header className="app-header">
        <div className="app-header-inner">
          <Link to="/" className="brand">
            NEXORA
          </Link>

          <form className="search-form" onSubmit={handleSearch} role="search">
            <input
              type="search"
              placeholder="Search products..."
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              aria-label="Search products"
            />
            <button type="submit">Search</button>
          </form>

          <nav className="app-nav">
            <NavLink to="/products" className="nav-link">
              Shop
            </NavLink>
            {isAuthenticated && (
              <NavLink to="/wishlist" className="nav-link">
                Wishlist
              </NavLink>
            )}
            {isAuthenticated && (
              <NavLink to="/orders" className="nav-link">
                Orders
              </NavLink>
            )}
            {isSeller && (
              <NavLink to="/seller" className="nav-link">
                Seller
              </NavLink>
            )}
            {isAdmin && (
              <NavLink to="/admin" className="nav-link">
                Admin
              </NavLink>
            )}
            <NavLink to="/cart" className="nav-link cart-link">
              Cart{itemCount > 0 && <span className="cart-badge">{itemCount}</span>}
            </NavLink>

            {isAuthenticated ? (
              <div className="nav-user">
                <NavLink to="/profile" className="nav-link">
                  {user?.first_name ?? "Profile"}
                </NavLink>
                <button type="button" className="link-button" onClick={logout}>
                  Log out
                </button>
              </div>
            ) : (
              <div className="nav-user">
                <NavLink to="/login" className="nav-link">
                  Log in
                </NavLink>
                <NavLink to="/register" className="nav-link nav-cta">
                  Sign up
                </NavLink>
              </div>
            )}
          </nav>
        </div>
      </header>

      <main className="app-main">
        <Outlet />
      </main>

      <footer className="app-footer">
        <p>NEXORA — a full-stack commerce platform in progress.</p>
      </footer>
    </div>
  );
}
