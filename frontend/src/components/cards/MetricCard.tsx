import type { ReactNode } from "react";

type MetricCardProps = {
  label: string;
  value: string;
  hint?: string;
  accent?: ReactNode;
};

export function MetricCard({ label, value, hint, accent }: MetricCardProps) {
  return (
    <div className="forge-metric-card rounded-[24px] p-5">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="forge-label text-xs font-semibold uppercase tracking-[0.28em]">{label}</p>
          <p className="mt-3 font-['Space_Grotesk'] text-3xl font-bold">{value}</p>
        </div>
        {accent ? <div className="pt-1">{accent}</div> : null}
      </div>
      {hint ? <p className="forge-subtitle mt-3 text-sm">{hint}</p> : null}
    </div>
  );
}
