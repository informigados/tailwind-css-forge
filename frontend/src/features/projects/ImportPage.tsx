import { startTransition, useState } from "react";
import { useNavigate } from "react-router-dom";

import { SectionCard } from "components/common/SectionCard";
import { MessageBanner } from "components/feedback/MessageBanner";
import { isDesktopShell, pickDirectory } from "desktop/runtime";
import { useI18n } from "i18n/useI18n";
import { api, ApiError } from "services/api";

export function ImportPage() {
  const { t } = useI18n();
  const navigate = useNavigate();
  const [sourcePath, setSourcePath] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isPickingDirectory, setIsPickingDirectory] = useState(false);

  async function handlePickDirectory() {
    setMessage(null);
    setIsPickingDirectory(true);

    try {
      const selection = await pickDirectory(t("import.dialogTitle"));
      if (selection) {
        setSourcePath(selection);
      } else {
        setMessage(t("import.messagePickerUnsupported"));
      }
    } catch {
      setMessage(t("import.messageBrowseFailed"));
    } finally {
      setIsPickingDirectory(false);
    }
  }

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsSubmitting(true);
    setMessage(null);

    try {
      const project = await api.importProject(sourcePath);
      startTransition(() => navigate(`/projects/${project.id}/analysis`));
    } catch (error: unknown) {
      setMessage(error instanceof ApiError ? error.message : t("import.messageFailed"));
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <SectionCard
      eyebrow={t("import.eyebrow")}
      title={t("import.title")}
      subtitle={t("import.subtitle")}
    >
      <form className="space-y-5" onSubmit={handleSubmit}>
        <label className="block space-y-2">
          <span className="forge-meta-label font-semibold">
            {t("import.pathLabel")}
          </span>
          <div className="flex flex-col gap-3 md:flex-row">
            <input
              value={sourcePath}
              onChange={(event) => setSourcePath(event.target.value)}
              placeholder={t("import.pathPlaceholder")}
              className="forge-input px-4 py-4 text-sm"
            />
            <button
              type="button"
              onClick={handlePickDirectory}
              disabled={isPickingDirectory || isSubmitting}
              className="forge-button forge-button-secondary"
            >
              {isPickingDirectory ? t("import.browsing") : t("import.browse")}
            </button>
          </div>
        </label>
        <p className="forge-tertiary text-sm">
          {isDesktopShell() ? t("import.desktopHint") : t("import.browserHint")}
        </p>

        <div className="grid gap-4 md:grid-cols-3">
          <div className="forge-subtle-card rounded-[24px] p-4 text-sm forge-subtitle">
            {t("import.snapshot")}
          </div>
          <div className="forge-subtle-card rounded-[24px] p-4 text-sm forge-subtitle">
            {t("import.workspace")}
          </div>
          <div className="forge-subtle-card rounded-[24px] p-4 text-sm forge-subtitle">
            {t("import.fingerprint")}
          </div>
        </div>

        {message ? <MessageBanner tone="danger" text={message} /> : null}

        <button
          type="submit"
          disabled={!sourcePath || isSubmitting}
          className="forge-button forge-button-primary"
        >
          {isSubmitting ? t("import.submitting") : t("import.submit")}
        </button>
      </form>
    </SectionCard>
  );
}
