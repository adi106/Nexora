import { useEffect, useState } from "react";
import { getAnalyticsOverview, getCategoryPerformance, getTopProducts } from "../../api/admin";
import type { AnalyticsOverview, CategoryPerformance, TopProduct } from "../../api/admin";
import { RevenueBarChart } from "../../components/RevenueBarChart";
import { LoadingSpinner } from "../../components/LoadingSpinner";
import { ErrorMessage } from "../../components/ErrorMessage";
import { extractErrorMessage } from "../../api/client";
import { formatPrice } from "../../utils/format";

export function AdminAnalyticsPage() {
  const [overview, setOverview] = useState<AnalyticsOverview | null>(null);
  const [topProducts, setTopProducts] = useState<TopProduct[]>([]);
  const [categories, setCategories] = useState<CategoryPerformance[]>([]);
  const [showTable, setShowTable] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([getAnalyticsOverview(30), getTopProducts(10), getCategoryPerformance()])
      .then(([overviewData, products, categoryData]) => {
        setOverview(overviewData);
        setTopProducts(products);
        setCategories(categoryData);
      })
      .catch((err) => setError(extractErrorMessage(err)));
  }, []);

  if (error) return <ErrorMessage message={error} />;
  if (!overview) return <LoadingSpinner label="Loading analytics..." />;

  return (
    <div className="page">
      <h1>Analytics</h1>
      <p className="hint">Last {overview.period_days} days</p>

      <div className="stats-grid">
        <div className="stat-tile">
          <span className="stat-label">Revenue</span>
          <span className="stat-value">{formatPrice(overview.revenue_in_period)}</span>
        </div>
        <div className="stat-tile">
          <span className="stat-label">Orders</span>
          <span className="stat-value">{overview.orders_in_period}</span>
        </div>
        <div className="stat-tile">
          <span className="stat-label">New users</span>
          <span className="stat-value">{overview.new_users_in_period}</span>
        </div>
        <div className="stat-tile">
          <span className="stat-label">New sellers</span>
          <span className="stat-value">{overview.new_sellers_in_period}</span>
        </div>
      </div>

      <section className="section">
        <div className="page-header-row">
          <h2>Daily revenue</h2>
          <button type="button" className="link-button" onClick={() => setShowTable((v) => !v)}>
            {showTable ? "Show chart" : "Show as table"}
          </button>
        </div>
        {showTable ? (
          <table className="data-table">
            <thead>
              <tr>
                <th>Date</th>
                <th>Orders</th>
                <th>Revenue</th>
              </tr>
            </thead>
            <tbody>
              {overview.daily.map((point) => (
                <tr key={point.date}>
                  <td>{point.date}</td>
                  <td>{point.order_count}</td>
                  <td>{formatPrice(point.revenue)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <RevenueBarChart data={overview.daily} />
        )}
      </section>

      <section className="section">
        <h2>Top products</h2>
        {topProducts.length === 0 ? (
          <p className="empty-state">No sales yet.</p>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th>Product</th>
                <th>Units sold</th>
                <th>Revenue</th>
              </tr>
            </thead>
            <tbody>
              {topProducts.map((product) => (
                <tr key={product.product_id}>
                  <td>{product.name}</td>
                  <td>{product.units_sold}</td>
                  <td>{formatPrice(product.revenue)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      <section className="section">
        <h2>Category performance</h2>
        {categories.length === 0 ? (
          <p className="empty-state">No sales yet.</p>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th>Category</th>
                <th>Orders</th>
                <th>Revenue</th>
              </tr>
            </thead>
            <tbody>
              {categories.map((category) => (
                <tr key={category.category_id}>
                  <td>{category.name}</td>
                  <td>{category.order_count}</td>
                  <td>{formatPrice(category.revenue)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </div>
  );
}
