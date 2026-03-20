type EmptyStateProps = {
  title: string;
  description: string;
};

export function EmptyState({ title, description }: EmptyStateProps) {
  return (
    <div className="forge-empty-state rounded-[24px] border-dashed p-8 text-center">
      <p className="font-['Space_Grotesk'] text-xl font-semibold">{title}</p>
      <p className="forge-subtitle mx-auto mt-3 max-w-2xl text-sm">{description}</p>
    </div>
  );
}
