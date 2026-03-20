import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { EmptyState } from "components/common/EmptyState";
import { SectionCard } from "components/common/SectionCard";
import { StatusBadge } from "components/common/StatusBadge";
import { MessageBanner } from "components/feedback/MessageBanner";
import { useI18n } from "i18n/useI18n";
import { formatDate, formatDuration, formatPercent } from "lib/format";
import type { BuildReport, BuildSummary } from "lib/types";
import { api, ApiError } from "services/api";

export function ReportPage() {
  const { t } = useI18n();
  const { projectId = "" } = useParams();
  const [builds, setBuilds] = useState<BuildSummary[]>([]);
  const [selectedBuildId, setSelectedBuildId] = useState("");
  const [report, setReport] = useState<BuildReport | null>(null);
  const [log, setLog] = useState("");
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    if (!projectId) {
      return;
    }
    api
      .listBuilds(projectId)
      .then((payload) => {
        setBuilds(payload);
        if (payload.length > 0) {
          setSelectedBuildId((current) => current || payload[0].id);
        }
      })
      .catch((error: unknown) =>
        setMessage(error instanceof ApiError ? error.message : t("report.messageBuildListFailed")),
      );
  }, [projectId, t]);

  useEffect(() => {
    if (!selectedBuildId) {
      setReport(null);
      setLog("");
      return;
    }

    Promise.all([api.getBuildReport(selectedBuildId), api.getBuildLog(selectedBuildId)])
      .then(([reportPayload, logPayload]) => {
        setReport(reportPayload);
        setLog(logPayload.log);
        setMessage(null);
      })
      .catch((error: unknown) =>
        setMessage(error instanceof ApiError ? error.message : t("report.messageLoadFailed")),
      );
  }, [selectedBuildId]);

  const selectedBuild = useMemo(
    () => builds.find((build) => build.id === selectedBuildId) ?? null,
    [builds, selectedBuildId],
  );

  return (
    <div className="space-y-6">
      {message ? <MessageBanner tone="danger" text={message} /> : null}

      <SectionCard
        eyebrow={t("report.eyebrow")}
        title={t("report.title")}
        subtitle={t("report.subtitle")}
      >
        {builds.length === 0 ? (
          <EmptyState
            title={t("report.noBuilds")}
            description={t("report.noBuildsDescription")}
          />
        ) : (
          <div className="space-y-6">
            <label className="space-y-2">
              <span className="forge-meta-label">{t("report.registeredBuild")}</span>
              <select
                value={selectedBuildId}
                onChange={(event) => setSelectedBuildId(event.target.value)}
                className="forge-input px-4 py-3 text-sm"
              >
                {builds.map((build) => (
                  <option key={build.id} value={build.id}>
                    {build.id} • {build.strategy_used} • {build.status}
                  </option>
                ))}
              </select>
            </label>

            {report ? (
              <>
                <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
                  <div className="forge-subtle-card rounded-[24px] p-4">
                    <p className="forge-meta-label">{t("report.status")}</p>
                    <div className="mt-3">
                      <StatusBadge tone={report.status === "success" ? "success" : "danger"} label={report.status} />
                    </div>
                  </div>
                  <div className="forge-subtle-card rounded-[24px] p-4">
                    <p className="forge-meta-label">{t("report.strategy")}</p>
                    <p className="forge-subtitle mt-3 text-sm">{report.strategy_used}</p>
                  </div>
                  <div className="forge-subtle-card rounded-[24px] p-4">
                    <p className="forge-meta-label">{t("report.duration")}</p>
                    <p className="forge-subtitle mt-3 text-sm">{formatDuration(report.duration_ms)}</p>
                  </div>
                  <div className="forge-subtle-card rounded-[24px] p-4">
                    <p className="forge-meta-label">{t("analysis.confidence")}</p>
                    <p className="forge-subtitle mt-3 text-sm">{formatPercent(report.analysis.confidence)}</p>
                  </div>
                </div>

                <div className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
                  <div className="space-y-6">
                    <div className="forge-subtle-card rounded-[24px] p-5">
                      <p className="font-['Space_Grotesk'] text-xl font-semibold">{t("report.summary")}</p>
                      <div className="forge-subtitle mt-4 grid gap-3 text-sm md:grid-cols-2">
                        <p>{t("report.buildId")}: {report.build_id}</p>
                        <p>{t("report.generatedAt")}: {formatDate(report.generated_at)}</p>
                        <p>Tailwind: {report.analysis.tailwind_detected ? t("report.tailwindDetected") : t("report.tailwindMissing")}</p>
                        <p>{t("report.version")}: {report.analysis.probable_major_version ? `${report.analysis.probable_major_version}.x` : "?"}</p>
                        <p>{t("report.projectStyle")}: {report.analysis.project_style ?? t("analysis.notIdentified")}</p>
                        <p>{t("report.execution")}: {report.build_plan.execution_mode ?? t("analysis.notDefined")}</p>
                        <p>{t("report.risk")}: {report.build_plan.risk_level ?? t("analysis.notDefined")}</p>
                        <p>{t("report.action")}: {report.build_plan.recommended_action ?? t("analysis.notDefined")}</p>
                      </div>
                      <div className="mt-4 flex flex-wrap gap-3">
                        {report.analysis.framework_hints.map((framework) => (
                          <StatusBadge key={framework} tone="info" label={framework} />
                        ))}
                      </div>
                    </div>

                    <div className="forge-subtle-card rounded-[24px] p-5">
                      <p className="font-['Space_Grotesk'] text-xl font-semibold">{t("report.artifacts")}</p>
                      <div className="forge-subtitle mt-4 space-y-3 text-sm">
                        {report.outputs.length === 0 ? (
                          <p>{t("report.noArtifacts")}</p>
                        ) : (
                          report.outputs.map((output) => (
                            <div key={output} className="forge-code-surface rounded-2xl p-3">
                              {output}
                            </div>
                          ))
                        )}
                      </div>
                    </div>
                  </div>

                  <div className="space-y-6">
                    <div className="forge-subtle-card rounded-[24px] p-5">
                      <p className="font-['Space_Grotesk'] text-xl font-semibold">{t("report.warnings")}</p>
                      <div className="forge-subtitle mt-4 space-y-3 text-sm">
                        {report.warnings.length === 0 ? (
                          <p>{t("report.noWarnings")}</p>
                        ) : (
                          report.warnings.map((warning) => (
                            <div key={warning} className="forge-banner forge-banner-warning">
                              {warning}
                            </div>
                          ))
                        )}
                      </div>
                    </div>

                    <div className="forge-subtle-card rounded-[24px] p-5">
                      <p className="font-['Space_Grotesk'] text-xl font-semibold">{t("report.errors")}</p>
                      <div className="forge-subtitle mt-4 space-y-3 text-sm">
                        {report.errors.length === 0 ? (
                          <p>{t("report.noErrors")}</p>
                        ) : (
                          report.errors.map((error) => (
                            <div key={error} className="forge-banner forge-banner-danger">
                              {error}
                            </div>
                          ))
                        )}
                      </div>
                    </div>
                  </div>
                </div>

                <div className="forge-subtle-card rounded-[24px] p-5">
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <p className="font-['Space_Grotesk'] text-xl font-semibold">{t("report.technicalLog")}</p>
                    {selectedBuild ? (
                      <Link
                        to={`/projects/${selectedBuild.project_id}/build`}
                        className="forge-button forge-button-secondary"
                      >
                        {t("report.backToBuilds")}
                      </Link>
                    ) : null}
                  </div>
                  <pre className="forge-code-surface forge-subtitle mt-4 max-h-[420px] overflow-auto rounded-2xl p-4 text-xs leading-6">
                    {log || t("report.noLog")}
                  </pre>
                </div>
              </>
            ) : null}
          </div>
        )}
      </SectionCard>
    </div>
  );
}
