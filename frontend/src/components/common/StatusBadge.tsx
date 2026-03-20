type StatusBadgeProps = {
  tone?: "neutral" | "success" | "warning" | "danger" | "info";
  label: string;
};

const toneClasses: Record<NonNullable<StatusBadgeProps["tone"]>, string> = {
  neutral: "forge-badge-neutral",
  success: "forge-badge-success",
  warning: "forge-badge-warning",
  danger: "forge-badge-danger",
  info: "forge-badge-info",
};

export function StatusBadge({ tone = "neutral", label }: StatusBadgeProps) {
  return (
    <span
      role="status"
      aria-label={label}
      className={`forge-badge ${toneClasses[tone]}`}
    >
      {label}
    </span>
  );
}
