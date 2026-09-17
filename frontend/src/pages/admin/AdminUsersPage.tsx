import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { listAdminUsers, setUserActive } from "../../api/admin";
import { useAuth } from "../../hooks/useAuth";
import { LoadingSpinner } from "../../components/LoadingSpinner";
import { ErrorMessage } from "../../components/ErrorMessage";
import { extractErrorMessage } from "../../api/client";
import type { User } from "../../types";

export function AdminUsersPage() {
  const { user: currentUser } = useAuth();
  const [users, setUsers] = useState<User[]>([]);
  const [search, setSearch] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);

  function load(searchTerm?: string) {
    setIsLoading(true);
    listAdminUsers(searchTerm)
      .then((data) => setUsers(data.items))
      .catch((err) => setError(extractErrorMessage(err)))
      .finally(() => setIsLoading(false));
  }

  useEffect(() => load(), []);

  function handleSearch(event: FormEvent) {
    event.preventDefault();
    load(search);
  }

  async function toggleActive(user: User) {
    setBusyId(user.id);
    setError(null);
    try {
      await setUserActive(user.id, !user.is_active);
      load(search);
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setBusyId(null);
    }
  }

  return (
    <div className="page">
      <h1>Users</h1>
      {error && <ErrorMessage message={error} />}

      <form className="search-form" style={{ maxWidth: 360, marginBottom: "1.25rem" }} onSubmit={handleSearch}>
        <input
          type="search"
          placeholder="Search by email..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <button type="submit">Search</button>
      </form>

      {isLoading ? (
        <LoadingSpinner label="Loading users..." />
      ) : (
        <table className="data-table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Email</th>
              <th>Roles</th>
              <th>Status</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {users.map((user) => (
              <tr key={user.id}>
                <td>
                  {user.first_name} {user.last_name}
                </td>
                <td>{user.email}</td>
                <td>{user.roles.length > 0 ? user.roles.join(", ") : "customer"}</td>
                <td>
                  <span className={user.is_active ? "badge active" : "badge inactive"}>
                    {user.is_active ? "Active" : "Suspended"}
                  </span>
                </td>
                <td>
                  {user.id !== currentUser?.id && (
                    <button
                      type="button"
                      className="link-button"
                      disabled={busyId === user.id}
                      onClick={() => toggleActive(user)}
                    >
                      {user.is_active ? "Suspend" : "Reactivate"}
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
