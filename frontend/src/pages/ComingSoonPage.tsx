export function ComingSoonPage({ title, phase }: { title: string; phase: string }) {
  return (
    <div className="page empty-state">
      <h1>{title}</h1>
      <p>This area of NEXORA arrives in {phase}.</p>
    </div>
  );
}
