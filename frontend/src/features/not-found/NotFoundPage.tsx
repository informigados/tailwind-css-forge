import { Link } from "react-router-dom";

import { EmptyState } from "components/common/EmptyState";
import { SectionCard } from "components/common/SectionCard";
import { useI18n } from "i18n/useI18n";

export function NotFoundPage() {
  const { t } = useI18n();

  return (
    <SectionCard eyebrow="404" title={t("notFound.title")} subtitle={t("notFound.subtitle")}>
      <div className="space-y-5">
        <EmptyState title={t("notFound.title")} description={t("notFound.description")} />
        <Link
          to="/"
          className="forge-button forge-button-secondary"
        >
          {t("notFound.goHome")}
        </Link>
      </div>
    </SectionCard>
  );
}
