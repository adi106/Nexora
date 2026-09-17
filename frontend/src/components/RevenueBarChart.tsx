import type { DailyMetric } from "../api/admin";
import { formatPrice } from "../utils/format";

const WIDTH = 720;
const HEIGHT = 220;
const PADDING_LEFT = 56;
const PADDING_BOTTOM = 28;
const PADDING_TOP = 12;

export function RevenueBarChart({ data }: { data: DailyMetric[] }) {
  if (data.length === 0) {
    return <p className="empty-state">No revenue in this period yet.</p>;
  }

  const maxRevenue = Math.max(...data.map((d) => d.revenue), 1);
  const plotWidth = WIDTH - PADDING_LEFT - 16;
  const plotHeight = HEIGHT - PADDING_TOP - PADDING_BOTTOM;
  const barWidth = Math.max(4, plotWidth / data.length - 4);

  const yTicks = [0, 0.5, 1].map((fraction) => Math.round(maxRevenue * fraction));

  return (
    <div className="chart-root">
      <svg viewBox={`0 0 ${WIDTH} ${HEIGHT}`} role="img" aria-label="Daily revenue over the selected period">
        {yTicks.map((tick) => {
          const y = PADDING_TOP + plotHeight - (tick / maxRevenue) * plotHeight;
          return (
            <g key={tick}>
              <line
                x1={PADDING_LEFT}
                x2={WIDTH - 8}
                y1={y}
                y2={y}
                stroke="var(--chart-grid)"
                strokeWidth={1}
              />
              <text x={PADDING_LEFT - 8} y={y + 4} textAnchor="end" className="chart-axis-label">
                {formatPrice(tick)}
              </text>
            </g>
          );
        })}

        {data.map((point, index) => {
          const barHeight = (point.revenue / maxRevenue) * plotHeight;
          const x = PADDING_LEFT + index * (plotWidth / data.length) + 2;
          const y = PADDING_TOP + plotHeight - barHeight;
          return (
            <rect
              key={point.date}
              x={x}
              y={y}
              width={barWidth}
              height={Math.max(barHeight, 1)}
              rx={2}
              className="chart-bar"
            >
              <title>
                {point.date}: {formatPrice(point.revenue)} ({point.order_count} orders)
              </title>
            </rect>
          );
        })}

        <line
          x1={PADDING_LEFT}
          x2={PADDING_LEFT}
          y1={PADDING_TOP}
          y2={PADDING_TOP + plotHeight}
          stroke="var(--chart-grid)"
          strokeWidth={1}
        />
      </svg>
    </div>
  );
}
