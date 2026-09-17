export function LoadingSpinner({ label = "Loading..." }: { label?: string }) {
  return (
    <div className="state-message" role="status">
      <div className="spinner" aria-hidden="true" />
      <span>{label}</span>
    </div>
  );
}
