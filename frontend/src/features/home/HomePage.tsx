import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { MetricCard } from "components/cards/MetricCard";
import { EmptyState } from "components/common/EmptyState";
import { SectionCard } from "components/common/SectionCard";
import { StatusBadge } from "components/common/StatusBadge";
import { MessageBanner } from "components/feedback/MessageBanner";
import { useI18n } from "i18n/useI18n";
import { formatDate } from "lib/format";
import type { HealthStatus, ProjectSummary } from "lib/types";
import { api, ApiError } from "services/api";

export function HomePage() {
  const { t } = useI18n();
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [projects, setProjects] = useState<ProjectSummary[]>([]);
  const [message, setMessage] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let active = true;

    Promise.all([api.getHealth(), api.listProjects()])
      .then(([healthPayload, projectPayload]) => {
        if (!active) {
          return;
        }
        setHealth(healthPayload);
        setProjects(projectPayload);
        setMessage(null);
      })
      .catch((error: unknown) => {
        if (!active) {
          return;
        }
        const nextMessage =
          error instanceof ApiError ? error.message : t("home.messageLoadFailed");
        setMessage(nextMessage);
      })
      .finally(() => {
        if (active) {
          setIsLoading(false);
        }
      });

    return () => {
      active = false;
    };
  }, [t]);

  const readyProjects = projects.filter((project) => project.last_status === "built").length;

  return (
    <div className="space-y-6">
      {message ? <MessageBanner tone="danger" text={message} /> : null}
      <section className="grid gap-4 md:grid-cols-3">
        <MetricCard
          label={t("home.projects")}
          value={String(projects.length)}
          hint={t("home.projectsHint")}
          accent={<StatusBadge tone="info" label={isLoading ? t("home.syncing") : t("home.local")} />}
        />
        <MetricCard
          label={t("home.readyForDeploy")}
          value={String(readyProjects)}
          hint={t("home.readyHint")}
        />
        <MetricCard
          label={t("home.backend")}
          value={health?.status === "ok" ? t("home.backendOnline") : t("home.backendWaiting")}
          hint={health ? `${health.app} ${health.version}` : t("home.backendHint")}
        />
      </section>

      <SectionCard
        eyebrow={t("home.flow")}
        title={t("home.recentProjects")}
        subtitle={t("home.recentSubtitle")}
        actions={
          <Link
            to="/projects/import"
            className="forge-button forge-button-primary"
          >
            {t("home.importProject")}
          </Link>
        }
      >
        {projects.length === 0 ? (
          <EmptyState
            title={t("home.emptyTitle")}
            description={t("home.emptyDescription")}
          />
        ) : (
          <div className="grid gap-4 xl:grid-cols-2">
            {projects.map((project) => (
              <article key={project.id} className="forge-subtle-card rounded-[24px] p-5">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="font-['Space_Grotesk'] text-xl font-semibold">
                      {project.name}
                    </p>
                    <p className="forge-tertiary mt-2 break-all text-sm">{project.source_path}</p>
                  </div>
                  <StatusBadge
                    tone={project.last_status === "built" ? "success" : "warning"}
                    label={project.last_status ?? t("status.new")}
                  />
                </div>
                <div className="forge-subtitle mt-5 grid gap-3 text-sm sm:grid-cols-2">
                  <p>{t("home.created")}: {formatDate(project.created_at)}</p>
                  <p>{t("home.updated")}: {formatDate(project.updated_at)}</p>
                </div>
                <div className="mt-6 flex flex-wrap gap-3">
                  <Link
                    to={`/projects/${project.id}/analysis`}
                    className="forge-button forge-button-secondary"
                  >
                    {t("home.openAnalysis")}
                  </Link>
                  <Link
                    to={`/projects/${project.id}/build`}
                    className="forge-button forge-button-secondary"
                  >
                    {t("home.openBuilds")}
                  </Link>
                  <Link
                    to={`/projects/${project.id}/publish`}
                    className="forge-button forge-button-secondary"
                  >
                    {t("home.publish")}
                  </Link>
                </div>
              </article>
            ))}
          </div>
        )}
      </SectionCard>
    </div>
  );
}
