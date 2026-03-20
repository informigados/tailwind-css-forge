type MessageBannerProps = {
  tone?: "info" | "success" | "warning" | "danger";
  text: string;
};

const bannerClasses: Record<NonNullable<MessageBannerProps["tone"]>, string> = {
  info: "forge-banner-info",
  success: "forge-banner-success",
  warning: "forge-banner-warning",
  danger: "forge-banner-danger",
};

export function MessageBanner({ tone = "info", text }: MessageBannerProps) {
  const role = tone === "danger" ? "alert" : "status";
  return (
    <div
      role={role}
      aria-live={tone === "danger" ? "assertive" : "polite"}
      className={`forge-banner ${bannerClasses[tone]}`}
    >
      {text}
    </div>
  );
}
