import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { createCategory, setCategoryActive } from "../../api/categories";
import { listAdminCategories } from "../../api/admin";
import { LoadingSpinner } from "../../components/LoadingSpinner";
import { ErrorMessage } from "../../components/ErrorMessage";
import { extractErrorMessage } from "../../api/client";
import type { Category } from "../../types";

export function AdminCategoriesPage() {
  const [categories, setCategories] = useState<Category[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [name, setName] = useState("");
  const [slug, setSlug] = useState("");
  const [isCreating, setIsCreating] = useState(false);

  function load() {
    setIsLoading(true);
    listAdminCategories()
      .then(setCategories)
      .catch((err) => setError(extractErrorMessage(err)))
      .finally(() => setIsLoading(false));
  }

  useEffect(load, []);

  async function toggleActive(category: Category) {
    setBusyId(category.id);
    setError(null);
    try {
      await setCategoryActive(category.id, !category.is_active);
      load();
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setBusyId(null);
    }
  }

  async function handleCreate(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setIsCreating(true);
    try {
      await createCategory({ name, slug, is_active: true });
      setName("");
      setSlug("");
      load();
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setIsCreating(false);
    }
  }

  if (isLoading) return <LoadingSpinner label="Loading categories..." />;

  return (
    <div className="page">
      <h1>Categories</h1>
      {error && <ErrorMessage message={error} />}

      <form className="address-form" onSubmit={handleCreate} style={{ marginBottom: "2rem" }}>
        <h3>New category</h3>
        <div className="form-row">
          <label>
            Name
            <input required value={name} onChange={(e) => setName(e.target.value)} />
          </label>
          <label>
            Slug
            <input required value={slug} onChange={(e) => setSlug(e.target.value)} />
          </label>
        </div>
        <button type="submit" className="button primary" disabled={isCreating}>
          {isCreating ? "Creating..." : "Create category"}
        </button>
      </form>

      <table className="data-table">
        <thead>
          <tr>
            <th>Name</th>
            <th>Slug</th>
            <th>Status</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {categories.map((category) => (
            <tr key={category.id}>
              <td>{category.name}</td>
              <td>{category.slug}</td>
              <td>
                <span className={category.is_active ? "badge active" : "badge inactive"}>
                  {category.is_active ? "Active" : "Inactive"}
                </span>
              </td>
              <td>
                <button
                  type="button"
                  className="link-button"
                  disabled={busyId === category.id}
                  onClick={() => toggleActive(category)}
                >
                  {category.is_active ? "Deactivate" : "Activate"}
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
