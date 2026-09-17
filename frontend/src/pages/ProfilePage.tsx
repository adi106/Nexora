import { useAuth } from "../hooks/useAuth";
import { formatDate } from "../utils/format";

export function ProfilePage() {
  const { user } = useAuth();

  if (!user) return null;

  return (
    <div className="page">
      <h1>My profile</h1>
      <div className="profile-card">
        <p>
          <strong>Name:</strong> {user.first_name} {user.last_name}
        </p>
        <p>
          <strong>Email:</strong> {user.email}
        </p>
        <p>
          <strong>Roles:</strong> {user.roles.length > 0 ? user.roles.join(", ") : "customer"}
        </p>
        <p>
          <strong>Member since:</strong> {formatDate(user.created_at)}
        </p>
      </div>
    </div>
  );
}
