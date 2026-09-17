export function StarRating({ value, count }: { value: number; count?: number }) {
  const rounded = Math.round(value);
  return (
    <span className="star-rating" aria-label={`Rated ${value.toFixed(1)} out of 5`}>
      {[1, 2, 3, 4, 5].map((star) => (
        <span key={star} className={star <= rounded ? "star filled" : "star"}>
          ★
        </span>
      ))}
      <span className="star-rating-value">{value.toFixed(1)}</span>
      {count !== undefined && <span className="star-rating-count">({count})</span>}
    </span>
  );
}
