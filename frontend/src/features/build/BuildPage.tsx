import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { EmptyState } from "components/common/EmptyState";
import { SectionCard } from "components/common/SectionCard";
import { StatusBadge } from "components/common/StatusBadge";
import { MessageBanner } from "components/feedback/MessageBanner";
import { useI18n } from "i18n/useI18n";
import { formatDate, formatDuration } from "lib/format";
import type { BuildProgressEvent, BuildSummary } from "lib/types";
import { api, ApiError } from "services/api";

function isTerminalStatus(status: string) {
  return ["success", "failed", "cancelled"].includes(status);
}

function resolveWebSocketUrl(buildId: string) {
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const host = window.location.port === "5173" ? "127.0.0.1:8000" : window.location.host;
  return `${protocol}//${host}/ws/builds/${buildId}`;
}

export function BuildPage() {
  const { t } = useI18n();
  const { projectId = "" } = useParams();
  const [builds, setBuilds] = useState<BuildSummary[]>([]);
  const [activeBuildId, setActiveBuildId] = useState<string | null>(null);
  const [focusedBuildId, setFocusedBuildId] = useState<string | null>(null);
  const [liveProgress, setLiveProgress] = useState<BuildProgressEvent | null>(null);
  const [focusedLog, setFocusedLog] = useState<string>("");
  const [message, setMessage] = useState<string | null>(null);
  const [isBuilding, setIsBuilding] = useState(false);
  const [isCancelling, setIsCancelling] = useState(false);
  const [isExporting, setIsExporting] = useState<string | null>(null);
  const [minify, setMinify] = useState(true);

  async function refreshBuilds() {
    if (!projectId) {
      return [];
    }
    const nextBuilds = await api.listBuilds(projectId);
    setBuilds(nextBuilds);
    return nextBuilds;
  }

  useEffect(() => {
    if (!projectId) {
      return;
    }
    refreshBuilds()
      .then((payload) => {
        const running = payload.find((build) => !isTerminalStatus(build.status));
        if (running) {
          setActiveBuildId(running.id);
          setFocusedBuildId(running.id);
          return;
        }
        const latestFinished = payload.find((build) => isTerminalStatus(build.status));
        if (latestFinished) {
          setFocusedBuildId(latestFinished.id);
        }
      })
      .catch((error: unknown) =>
        setMessage(error instanceof ApiError ? error.message : t("build.messageLoadFailed")),
      );
  }, [projectId, t]);

  useEffect(() => {
    if (!activeBuildId) {
      return;
    }

    let disposed = false;
    const socket = new WebSocket(resolveWebSocketUrl(activeBuildId));
    const poller = window.setInterval(async () => {
      try {
        const build = await api.getBuild(activeBuildId);
        if (disposed) {
          return;
        }
        setLiveProgress({
          type: "progress",
          build_id: build.id,
          status: build.status,
          progress_percent: build.progress_percent,
          step: build.current_step,
          message: build.current_message,
          cancel_requested: build.cancel_requested,
          started_at: build.started_at,
          finished_at: build.finished_at,
        });
        if (isTerminalStatus(build.status)) {
          window.clearInterval(poller);
          setActiveBuildId(null);
          setFocusedBuildId(build.id);
          await refreshBuilds();
        }
      } catch {
        window.clearInterval(poller);
      }
    }, 1500);

    socket.onmessage = async (event) => {
      const payload = JSON.parse(event.data) as BuildProgressEvent;
      if (disposed) {
        return;
      }
      setLiveProgress(payload);
      if (isTerminalStatus(payload.status)) {
        window.clearInterval(poller);
        setActiveBuildId(null);
        setFocusedBuildId(payload.build_id);
        await refreshBuilds();
      }
    };

    socket.onerror = () => {
      // Polling remains active as fallback.
    };

    return () => {
      disposed = true;
      window.clearInterval(poller);
      socket.close();
    };
  }, [activeBuildId]);

  useEffect(() => {
    if (!focusedBuildId) {
      setFocusedLog("");
      return;
    }

    api
      .getBuildLog(focusedBuildId)
      .then((payload) => setFocusedLog(payload.log))
      .catch(() => setFocusedLog(t("build.messageLogUnavailable")));
  }, [focusedBuildId, t]);

  const focusedBuild = useMemo(
    () => builds.find((build) => build.id === focusedBuildId) ?? null,
    [builds, focusedBuildId],
  );

  async function handleBuild() {
    if (!projectId) {
      return;
    }
    setIsBuilding(true);
    setMessage(null);

    try {
      const payload = await api.buildProject(projectId, minify);
      setActiveBuildId(payload.build.id);
      setFocusedBuildId(payload.build.id);
      setLiveProgress({
        type: "progress",
        build_id: payload.build.id,
        status: payload.build.status,
        progress_percent: payload.build.progress_percent,
        step: payload.build.current_step,
        message: payload.build.current_message,
        cancel_requested: payload.build.cancel_requested,
        started_at: payload.build.started_at,
        finished_at: payload.build.finished_at,
      });
      await refreshBuilds();
    } catch (error: unknown) {
      setMessage(error instanceof ApiError ? error.message : t("build.messageRunFailed"));
    } finally {
      setIsBuilding(false);
    }
  }

  async function handleCancel() {
    if (!activeBuildId) {
      return;
    }
    setIsCancelling(true);
    setMessage(null);
    try {
      const build = await api.cancelBuild(activeBuildId);
      setLiveProgress({
        type: "progress",
        build_id: build.id,
        status: build.status,
        progress_percent: build.progress_percent,
        step: build.current_step,
        message: build.current_message,
        cancel_requested: build.cancel_requested,
        started_at: build.started_at,
        finished_at: build.finished_at,
      });
      setMessage(t("build.messageCancelSent"));
      await refreshBuilds();
    } catch (error: unknown) {
      setMessage(error instanceof ApiError ? error.message : t("build.messageCancelFailed"));
    } finally {
      setIsCancelling(false);
    }
  }

  async function handleExport(buildId: string) {
    setIsExporting(buildId);
    setMessage(null);
    try {
      const payload = await api.exportZip(buildId);
      setMessage(t("build.messageExported", { path: payload.output_path }));
    } catch (error: unknown) {
      setMessage(error instanceof ApiError ? error.message : t("build.messageExportFailed"));
    } finally {
      setIsExporting(null);
    }
  }

  const visibleProgress = liveProgress && !isTerminalStatus(liveProgress.status) ? liveProgress : null;

  return (
    <div className="space-y-6">
      {message ? <MessageBanner tone="info" text={message} /> : null}

      <SectionCard
        eyebrow={t("build.eyebrow")}
        title={t("build.title")}
        subtitle={t("build.subtitle")}
        actions={
          <div className="flex flex-wrap gap-3">
            {visibleProgress ? (
              <button
                type="button"
                onClick={handleCancel}
                disabled={isCancelling || visibleProgress.cancel_requested}
                className="forge-button forge-button-danger"
              >
                {visibleProgress.cancel_requested ? t("build.cancelRequested") : isCancelling ? t("build.cancelling") : t("build.cancel")}
              </button>
            ) : null}
            <button
              type="button"
              onClick={handleBuild}
              disabled={!projectId || isBuilding || Boolean(visibleProgress)}
              className="forge-button forge-button-primary"
            >
              {isBuilding ? t("build.starting") : t("build.run")}
            </button>
          </div>
        }
      >
        <label className="forge-subtitle flex items-center gap-3 text-sm">
          <input
            checked={minify}
            onChange={(event) => setMinify(event.target.checked)}
            type="checkbox"
            className="forge-checkbox h-4 w-4 rounded"
          />
          {t("build.enableMinify")}
        </label>

        {visibleProgress ? (
          <div className="forge-subtle-card mt-6 rounded-[24px] p-5">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div>
                <p className="font-['Space_Grotesk'] text-xl font-semibold">{t("build.runningTitle")}</p>
                <p className="forge-subtitle mt-2 text-sm">{visibleProgress.step ?? t("build.processing")}</p>
              </div>
              <StatusBadge tone="warning" label={visibleProgress.status} />
            </div>
            <div className="forge-progress-track mt-5 h-3 overflow-hidden rounded-full">
              <div
                className="h-full rounded-full bg-[linear-gradient(90deg,#f59e0b,#38bdf8)] transition-all"
                style={{ width: `${Math.max(6, visibleProgress.progress_percent)}%` }}
              />
            </div>
            <div className="forge-subtitle mt-4 grid gap-3 text-sm md:grid-cols-3">
              <p>{t("build.progressLabel")}: {visibleProgress.progress_percent}%</p>
              <p>{t("build.startedLabel")}: {formatDate(visibleProgress.started_at)}</p>
              <p>{t("build.messageLabel")}: {visibleProgress.message ?? t("build.noExtraDetail")}</p>
            </div>
          </div>
        ) : focusedBuild ? (
          <div className="mt-6 grid gap-5 xl:grid-cols-[0.9fr_1.1fr]">
            <div className="forge-subtle-card rounded-[24px] p-5">
              <div className="flex items-start justify-between gap-3">
                <p className="font-['Space_Grotesk'] text-xl font-semibold">{t("build.focusedBuild")}</p>
                <StatusBadge tone={focusedBuild.status === "success" ? "success" : focusedBuild.status === "cancelled" ? "warning" : "danger"} label={focusedBuild.status} />
              </div>
              <div className="forge-subtitle mt-4 space-y-3 text-sm">
                <p>{t("build.strategyLabel")}: {focusedBuild.strategy_used}</p>
                <p>{t("build.durationLabel")}: {formatDuration(focusedBuild.duration_ms)}</p>
                <p>{t("build.stepLabel")}: {focusedBuild.current_step ?? t("common.notAvailable")}</p>
                <p>{t("build.outputLabel")}: {focusedBuild.output_path ?? t("common.notAvailable")}</p>
              </div>
            </div>

            <div className="forge-subtle-card rounded-[24px] p-5">
              <p className="font-['Space_Grotesk'] text-xl font-semibold">{t("build.technicalLog")}</p>
              <pre className="forge-code-surface forge-subtitle mt-4 max-h-[360px] overflow-auto rounded-2xl p-4 text-xs leading-6">
                {focusedLog || t("build.selectBuildForLog")}
              </pre>
            </div>
          </div>
        ) : null}
      </SectionCard>

      <SectionCard
        eyebrow={t("nav.history")}
        title={t("build.registeredTitle")}
        subtitle={t("build.registeredSubtitle")}
      >
        {builds.length === 0 ? (
          <EmptyState
            title={t("build.emptyTitle")}
            description={t("build.emptyDescription")}
          />
        ) : (
          <div className="space-y-4">
            {builds.map((build) => (
              <article key={build.id} className="forge-subtle-card rounded-[24px] p-5">
                <div className="flex flex-wrap items-start justify-between gap-4">
                  <div>
                    <p className="font-['Space_Grotesk'] text-xl font-semibold">{build.id}</p>
                    <p className="forge-tertiary mt-2 text-sm">
                      {build.strategy_used} • {formatDate(build.started_at)}
                    </p>
                  </div>
                  <StatusBadge
                    tone={build.status === "success" ? "success" : build.status === "cancelled" ? "warning" : build.status === "failed" ? "danger" : "info"}
                    label={build.status}
                  />
                </div>
                <div className="forge-subtitle mt-4 grid gap-3 text-sm md:grid-cols-4">
                  <p>{t("build.durationLabel")}: {formatDuration(build.duration_ms)}</p>
                  <p>{t("build.progressLabel")}: {build.progress_percent}%</p>
                  <p>{t("build.stepLabel")}: {build.current_step ?? t("common.notAvailable")}</p>
                  <p>{t("build.cancelStateLabel")}: {build.cancel_requested ? t("build.cancelStateRequested") : t("build.cancelStateNo")}</p>
                </div>
                <div className="mt-5 flex flex-wrap gap-3">
                  <button
                    type="button"
                    onClick={() => setFocusedBuildId(build.id)}
                    className="forge-button forge-button-secondary"
                  >
                    {t("build.focusLog")}
                  </button>
                  <Link
                    to={`/projects/${build.project_id}/report`}
                    className="forge-button forge-button-secondary"
                  >
                    {t("build.viewReport")}
                  </Link>
                  <button
                    type="button"
                    onClick={() => handleExport(build.id)}
                    disabled={isExporting === build.id || build.status !== "success"}
                    className="forge-button forge-button-secondary"
                  >
                    {isExporting === build.id ? t("build.exporting") : t("build.exportZip")}
                  </button>
                </div>
              </article>
            ))}
          </div>
        )}
      </SectionCard>
    </div>
  );
}
