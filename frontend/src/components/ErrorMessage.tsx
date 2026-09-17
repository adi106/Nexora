export function ErrorMessage({ message }: { message: string }) {
  return (
    <div className="state-message error" role="alert">
      {message}
    </div>
  );
}
