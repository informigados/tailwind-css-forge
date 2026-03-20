import type { ReactNode } from "react";

type SectionCardProps = {
  eyebrow?: string;
  title: string;
  subtitle?: string;
  actions?: ReactNode;
  children: ReactNode;
  className?: string;
};

export function SectionCard({
  eyebrow,
  title,
  subtitle,
  actions,
  children,
  className = "",
}: SectionCardProps) {
  return (
    <section
      className={`forge-surface-card rounded-[28px] p-6 backdrop-blur ${className}`}
    >
      <div className="mb-6 flex flex-wrap items-start justify-between gap-4">
        <div className="space-y-2">
          {eyebrow ? (
            <p className="forge-eyebrow text-[0.68rem] font-semibold uppercase tracking-[0.34em]">
              {eyebrow}
            </p>
          ) : null}
          <div>
            <h2 className="font-['Space_Grotesk'] text-2xl font-bold">{title}</h2>
            {subtitle ? <p className="forge-subtitle mt-2 max-w-3xl text-sm">{subtitle}</p> : null}
          </div>
        </div>
        {actions ? <div className="flex flex-wrap gap-3">{actions}</div> : null}
      </div>
      {children}
    </section>
  );
}
