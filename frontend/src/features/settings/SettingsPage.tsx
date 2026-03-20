import { useEffect, useState } from "react";

import { SectionCard } from "components/common/SectionCard";
import { MessageBanner } from "components/feedback/MessageBanner";
import { pickDirectory } from "desktop/runtime";
import { useI18n } from "i18n/useI18n";
import type { AppSettings } from "lib/types";
import { api, ApiError } from "services/api";

const initialSettings: AppSettings = {
  language: "pt-BR",
  theme: "system",
  default_workspace_path: "",
  default_exports_path: "",
  backup_before_build: true,
  default_minify: true,
  detailed_logs: true,
  build_timeout_seconds: 600,
};

export function SettingsPage() {
  const { setLocale, setTheme, t } = useI18n();
  const [settings, setSettings] = useState<AppSettings>(initialSettings);
  const [message, setMessage] = useState<string | null>(null);
  const [messageTone, setMessageTone] = useState<"success" | "danger" | "info">("info");
  const [isSaving, setIsSaving] = useState(false);
  const [pickingField, setPickingField] = useState<"workspace" | "exports" | null>(null);

  useEffect(() => {
    let active = true;
    api
      .getSettings()
      .then((payload) => {
        if (active) {
          setSettings(payload);
        }
      })
      .catch((error: unknown) => {
        if (active) {
          setMessageTone("danger");
          setMessage(error instanceof ApiError ? error.message : t("settings.messageLoadFailed"));
        }
      });
    return () => {
      active = false;
    };
  }, [t]);

  function updateField<K extends keyof AppSettings>(field: K, value: AppSettings[K]) {
    setSettings((current) => ({ ...current, [field]: value }));
  }

  async function handlePickDirectory(field: "default_workspace_path" | "default_exports_path", title: string) {
    setMessage(null);
    setPickingField(field === "default_workspace_path" ? "workspace" : "exports");
    try {
      const selection = await pickDirectory(title);
      if (selection) {
        updateField(field, selection);
      } else {
        setMessageTone("info");
        setMessage(t("settings.messagePickerUnsupported"));
      }
    } catch {
      setMessageTone("danger");
      setMessage(t("settings.messageBrowseFailed"));
    } finally {
      setPickingField(null);
    }
  }

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsSaving(true);
    setMessage(null);
    try {
      const updated = await api.updateSettings(settings);
      setSettings(updated);
      setLocale(updated.language);
      setTheme(updated.theme);
      setMessageTone("success");
      setMessage(t("settings.messageSaved"));
    } catch (error: unknown) {
      setMessageTone("danger");
      setMessage(error instanceof ApiError ? error.message : t("settings.messageSaveFailed"));
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <div className="space-y-6">
      {message ? <MessageBanner tone={messageTone} text={message} /> : null}

      <SectionCard
        eyebrow={t("settings.eyebrow")}
        title={t("settings.title")}
        subtitle={t("settings.subtitle")}
      >
        <form className="grid gap-4 md:grid-cols-2" onSubmit={handleSubmit}>
          <label className="space-y-2">
            <span className="forge-meta-label">{t("settings.language")}</span>
            <select
              value={settings.language}
              onChange={(event) => updateField("language", event.target.value)}
              className="forge-input px-4 py-3 text-sm"
            >
              <option value="pt-BR">pt-BR</option>
              <option value="en-US">en-US</option>
            </select>
          </label>

          <label className="space-y-2">
            <span className="forge-meta-label">{t("settings.theme")}</span>
            <select
              value={settings.theme}
              onChange={(event) => updateField("theme", event.target.value)}
              className="forge-input px-4 py-3 text-sm"
            >
              <option value="system">{t("settings.theme.system")}</option>
              <option value="dark">{t("settings.theme.dark")}</option>
              <option value="light">{t("settings.theme.light")}</option>
            </select>
          </label>

          <label className="space-y-2 md:col-span-2">
            <span className="forge-meta-label">{t("settings.workspace")}</span>
            <div className="flex flex-col gap-3 md:flex-row">
              <input
                value={settings.default_workspace_path}
                onChange={(event) => updateField("default_workspace_path", event.target.value)}
                className="forge-input px-4 py-3 text-sm"
              />
              <button
                type="button"
                onClick={() => handlePickDirectory("default_workspace_path", t("settings.workspacePickerTitle"))}
                disabled={pickingField !== null}
                className="forge-button forge-button-secondary"
              >
                {pickingField === "workspace" ? t("settings.browsing") : t("settings.browse")}
              </button>
            </div>
          </label>

          <label className="space-y-2 md:col-span-2">
            <span className="forge-meta-label">{t("settings.exports")}</span>
            <div className="flex flex-col gap-3 md:flex-row">
              <input
                value={settings.default_exports_path}
                onChange={(event) => updateField("default_exports_path", event.target.value)}
                className="forge-input px-4 py-3 text-sm"
              />
              <button
                type="button"
                onClick={() => handlePickDirectory("default_exports_path", t("settings.exportsPickerTitle"))}
                disabled={pickingField !== null}
                className="forge-button forge-button-secondary"
              >
                {pickingField === "exports" ? t("settings.browsing") : t("settings.browse")}
              </button>
            </div>
          </label>

          <label className="space-y-2">
            <span className="forge-meta-label">{t("settings.timeout")}</span>
            <input
              type="number"
              min={30}
              max={3600}
              value={settings.build_timeout_seconds}
              onChange={(event) => updateField("build_timeout_seconds", Number(event.target.value))}
              className="forge-input px-4 py-3 text-sm"
            />
          </label>

          <div className="forge-subtle-card rounded-[24px] p-4 text-sm forge-subtitle">
            {t("settings.phaseNote")}
          </div>

          <label className="forge-subtitle flex items-center gap-3 text-sm md:col-span-2">
            <input
              type="checkbox"
              checked={settings.backup_before_build}
              onChange={(event) => updateField("backup_before_build", event.target.checked)}
              className="forge-checkbox h-4 w-4 rounded"
            />
            {t("settings.backup")}
          </label>

          <label className="forge-subtitle flex items-center gap-3 text-sm md:col-span-2">
            <input
              type="checkbox"
              checked={settings.default_minify}
              onChange={(event) => updateField("default_minify", event.target.checked)}
              className="forge-checkbox h-4 w-4 rounded"
            />
            {t("settings.minify")}
          </label>

          <label className="forge-subtitle flex items-center gap-3 text-sm md:col-span-2">
            <input
              type="checkbox"
              checked={settings.detailed_logs}
              onChange={(event) => updateField("detailed_logs", event.target.checked)}
              className="forge-checkbox h-4 w-4 rounded"
            />
            {t("settings.logs")}
          </label>

          <div className="md:col-span-2">
            <button
              type="submit"
              disabled={isSaving}
              className="forge-button forge-button-primary"
            >
              {isSaving ? t("settings.saving") : t("settings.save")}
            </button>
          </div>
        </form>
      </SectionCard>
    </div>
  );
}
