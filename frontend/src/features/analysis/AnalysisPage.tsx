import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { MetricCard } from "components/cards/MetricCard";
import { EmptyState } from "components/common/EmptyState";
import { SectionCard } from "components/common/SectionCard";
import { StatusBadge } from "components/common/StatusBadge";
import { MessageBanner } from "components/feedback/MessageBanner";
import { useI18n } from "i18n/useI18n";
import { formatDate, formatPercent } from "lib/format";
import type { AnalysisSummary, ProjectSummary } from "lib/types";
import { api, ApiError } from "services/api";

export function AnalysisPage() {
  const { t } = useI18n();
  const { projectId = "" } = useParams();
  const [project, setProject] = useState<ProjectSummary | null>(null);
  const [analysis, setAnalysis] = useState<AnalysisSummary | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);

  useEffect(() => {
    if (!projectId) {
      return;
    }

    let active = true;
    setIsLoading(true);

    Promise.allSettled([api.getProject(projectId), api.getLatestAnalysis(projectId)])
      .then(([projectResult, analysisResult]) => {
        if (!active) {
          return;
        }

        if (projectResult.status === "fulfilled") {
          setProject(projectResult.value);
        } else {
          const error = projectResult.reason;
          setMessage(error instanceof ApiError ? error.message : t("analysis.messageProjectFailed"));
        }

        if (analysisResult.status === "fulfilled") {
          setAnalysis(analysisResult.value);
          setMessage(null);
          return;
        }

        const error = analysisResult.reason;
        if (error instanceof ApiError && error.status === 404) {
          setAnalysis(null);
          return;
        }
        setMessage(error instanceof ApiError ? error.message : t("analysis.messageLoadFailed"));
      })
      .finally(() => {
        if (active) {
          setIsLoading(false);
        }
      });

    return () => {
      active = false;
    };
  }, [projectId, t]);

  async function handleAnalyze() {
    if (!projectId) {
      return;
    }

    setIsAnalyzing(true);
    setMessage(null);
    try {
      const payload = await api.analyzeProject(projectId);
      setAnalysis(payload);
    } catch (error: unknown) {
      setMessage(error instanceof ApiError ? error.message : t("analysis.messageRunFailed"));
    } finally {
      setIsAnalyzing(false);
    }
  }

  return (
    <div className="space-y-6">
      {message ? <MessageBanner tone="danger" text={message} /> : null}

      <SectionCard
        eyebrow={t("analysis.eyebrow")}
        title={project ? `${t("analysis.projectLabel")}: ${project.name}` : t("analysis.loadingProject")}
        subtitle={
          project
            ? `${t("analysis.workspaceLabel")}: ${project.workspace_path}`
            : t("analysis.loadingWorkspace")
        }
        actions={
          <button
            type="button"
            onClick={handleAnalyze}
            disabled={!projectId || isAnalyzing}
            className="forge-button forge-button-primary"
          >
            {isAnalyzing ? t("analysis.running") : t("analysis.run")}
          </button>
        }
      >
        {analysis ? (
          <div className="space-y-5">
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
              <MetricCard
                label={t("analysis.tailwind")}
                value={analysis.tailwind_detected ? t("analysis.detected") : t("analysis.absent")}
                hint={`${t("analysis.createdAt")}: ${formatDate(analysis.created_at)}`}
              />
              <MetricCard
                label={t("analysis.strategy")}
                value={analysis.strategy_hint ?? t("analysis.undefined")}
                hint={`${t("analysis.action")}: ${analysis.build_plan.recommended_action ?? t("analysis.reviewBadge")}`}
              />
              <MetricCard
                label={t("analysis.confidence")}
                value={formatPercent(analysis.confidence)}
                hint={`${t("analysis.risk")}: ${analysis.build_plan.risk_level ?? t("analysis.notDefined")}`}
              />
              <MetricCard
                label={t("analysis.version")}
                value={analysis.probable_major_version ? `${analysis.probable_major_version}.x` : t("analysis.unknownVersion")}
                hint={analysis.build_plan.ready_for_build ? t("analysis.buildReady") : t("analysis.needsReview")}
              />
            </div>

            <div className="grid gap-5 xl:grid-cols-[1.3fr_0.7fr]">
              <div className="forge-subtle-card rounded-[24px] p-5">
                <div className="flex items-center justify-between gap-3">
                    <p className="font-['Space_Grotesk'] text-xl font-semibold">
                    {t("analysis.signals")}
                  </p>
                  <StatusBadge
                    tone={analysis.build_plan.ready_for_build ? "success" : "warning"}
                    label={analysis.build_plan.ready_for_build ? t("analysis.readyBadge") : t("analysis.reviewBadge")}
                  />
                </div>
                <div className="mt-5 flex flex-wrap gap-3">
                  {analysis.signals.map((signal) => (
                    <StatusBadge key={signal} tone="info" label={signal} />
                  ))}
                </div>
              </div>

              <div className="forge-subtle-card rounded-[24px] p-5">
                <p className="font-['Space_Grotesk'] text-xl font-semibold">{t("analysis.warnings")}</p>
                <div className="forge-subtitle mt-4 space-y-3 text-sm">
                  {analysis.warnings.length === 0 ? (
                    <p>{t("analysis.noWarnings")}</p>
                  ) : (
                    analysis.warnings.map((warning) => (
                      <div key={warning} className="forge-banner forge-banner-warning">
                        {warning}
                      </div>
                    ))
                  )}
                </div>
              </div>
            </div>

            <div className="grid gap-5 xl:grid-cols-[0.8fr_1.2fr]">
              <div className="forge-subtle-card rounded-[24px] p-5">
                <p className="font-['Space_Grotesk'] text-xl font-semibold">{t("analysis.context")}</p>
                <div className="forge-subtitle mt-4 space-y-3 text-sm">
                  <p>{t("analysis.projectStyle")}: {analysis.project_style ?? t("analysis.notIdentified")}</p>
                  <p>{t("analysis.execution")}: {analysis.build_plan.execution_mode ?? t("analysis.notDefined")}</p>
                  <p>{t("analysis.manualReview")}: {analysis.build_plan.requires_manual_review ? t("analysis.yes") : t("analysis.no")}</p>
                </div>
                <div className="mt-4 flex flex-wrap gap-3">
                  {analysis.framework_hints.length === 0 ? (
                    <StatusBadge tone="info" label={t("analysis.noFramework")} />
                  ) : (
                    analysis.framework_hints.map((framework) => (
                      <StatusBadge key={framework} tone="info" label={framework} />
                    ))
                  )}
                </div>
              </div>

              <div className="forge-subtle-card rounded-[24px] p-5">
                <p className="font-['Space_Grotesk'] text-xl font-semibold">{t("analysis.pipeline")}</p>
                <div className="mt-4 grid gap-3 md:grid-cols-2">
                  {(analysis.build_plan.pipeline_steps ?? []).map((step) => (
                    <div
                      key={step}
                      className="forge-code-surface rounded-2xl p-3 text-sm forge-subtitle"
                    >
                      {step}
                    </div>
                  ))}
                </div>
                <div className="forge-subtitle mt-4 space-y-3 text-sm">
                  {(analysis.build_plan.compatibility_notes ?? []).map((note) => (
                    <div key={note} className="forge-banner forge-banner-info">
                      {note}
                    </div>
                  ))}
                </div>
              </div>
            </div>

            <div className="flex flex-wrap gap-3">
              <Link
                to={`/projects/${projectId}/build`}
                className="forge-button forge-button-secondary"
              >
                {t("analysis.openBuilds")}
              </Link>
              <Link
                to={`/projects/${projectId}/publish`}
                className="forge-button forge-button-secondary"
              >
                {t("analysis.openPublish")}
              </Link>
            </div>
          </div>
        ) : isLoading ? (
          <div className="forge-subtitle text-sm">{t("analysis.loadingLatest")}</div>
        ) : (
          <EmptyState
            title={t("analysis.emptyTitle")}
            description={t("analysis.emptyDescription")}
          />
        )}
      </SectionCard>
    </div>
  );
}
