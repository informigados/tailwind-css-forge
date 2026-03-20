import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { EmptyState } from "components/common/EmptyState";
import { SectionCard } from "components/common/SectionCard";
import { StatusBadge } from "components/common/StatusBadge";
import { MessageBanner } from "components/feedback/MessageBanner";
import { useI18n } from "i18n/useI18n";
import { formatDate } from "lib/format";
import type { HistoryProjectEntry } from "lib/types";
import { api, ApiError } from "services/api";

export function HistoryPage() {
  const { t } = useI18n();
  const [rows, setRows] = useState<HistoryProjectEntry[]>([]);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    api
      .listHistory()
      .then((payload) => {
        if (active) {
          setRows(payload);
        }
      })
      .catch((error: unknown) => {
        if (active) {
          setMessage(error instanceof ApiError ? error.message : t("history.messageLoadFailed"));
        }
      });
    return () => {
      active = false;
    };
  }, [t]);

  return (
    <SectionCard
      eyebrow={t("history.eyebrow")}
      title={t("history.title")}
      subtitle={t("history.subtitle")}
    >
      {message ? <MessageBanner tone="danger" text={message} /> : null}
      {rows.length === 0 ? (
        <EmptyState
          title={t("history.emptyTitle")}
          description={t("history.emptyDescription")}
        />
      ) : (
        <div className="space-y-4">
          {rows.map((row) => (
            <article key={row.project.id} className="forge-subtle-card rounded-[24px] p-5">
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div>
                  <p className="font-['Space_Grotesk'] text-xl font-semibold">{row.project.name}</p>
                  <p className="forge-tertiary mt-2 break-all text-sm">{row.project.source_path}</p>
                </div>
                <StatusBadge
                  tone={row.project.last_status === "built" ? "success" : "warning"}
                  label={row.project.last_status ?? t("status.new")}
                />
              </div>
              <div className="forge-subtitle mt-4 grid gap-3 text-sm md:grid-cols-3">
                <p>{t("history.imported")}: {formatDate(row.project.created_at)}</p>
                <p>{t("history.latestAnalysis")}: {formatDate(row.latest_analysis_at)}</p>
                <p>{t("history.latestBuild")}: {row.latest_build ? row.latest_build.strategy_used : t("history.notExecuted")}</p>
                <p>{t("history.buildStatus")}: {row.latest_build?.status ?? t("common.notAvailable")}</p>
                <p>{t("history.savedProfiles")}: {row.publish_profile_count}</p>
                <p>{t("history.latestEvent")}: {row.recent_audit_events[0]?.event_type ?? t("history.none")}</p>
              </div>
              <div className="mt-4 flex flex-wrap gap-2">
                {row.recent_audit_events.slice(0, 3).map((event) => (
                  <StatusBadge key={event.id} tone="info" label={event.event_type} />
                ))}
              </div>
              <div className="mt-5 flex flex-wrap gap-3">
                <Link
                  to={`/projects/${row.project.id}/analysis`}
                  className="forge-button forge-button-secondary"
                >
                  {t("history.analysis")}
                </Link>
                <Link
                  to={`/projects/${row.project.id}/build`}
                  className="forge-button forge-button-secondary"
                >
                  {t("history.builds")}
                </Link>
                <Link
                  to={`/projects/${row.project.id}/report`}
                  className="forge-button forge-button-secondary"
                >
                  {t("history.report")}
                </Link>
                <Link
                  to={`/projects/${row.project.id}/publish`}
                  className="forge-button forge-button-secondary"
                >
                  {t("history.publish")}
                </Link>
              </div>
            </article>
          ))}
        </div>
      )}
    </SectionCard>
  );
}
