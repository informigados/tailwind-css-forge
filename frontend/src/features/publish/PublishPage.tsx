import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";

import { EmptyState } from "components/common/EmptyState";
import { SectionCard } from "components/common/SectionCard";
import { StatusBadge } from "components/common/StatusBadge";
import { MessageBanner } from "components/feedback/MessageBanner";
import { useI18n } from "i18n/useI18n";
import { formatDate } from "lib/format";
import type {
  BuildSummary,
  ProjectActivity,
  PublishProfileInput,
  PublishProtocol,
  PublishProfileSummary,
} from "lib/types";
import { api, ApiError } from "services/api";

const initialProfile: PublishProfileInput = {
  name: "",
  protocol: "ftp",
  host: "",
  port: 21,
  username: "",
  password: "",
  remote_path: "/",
  passive_mode: true,
  ftp_security_mode: "explicit_tls",
  sftp_host_key_policy: "trust_on_first_use",
};

export function PublishPage() {
  const { t } = useI18n();
  const { projectId = "" } = useParams();
  const [profiles, setProfiles] = useState<PublishProfileSummary[]>([]);
  const [builds, setBuilds] = useState<BuildSummary[]>([]);
  const [activity, setActivity] = useState<ProjectActivity | null>(null);
  const [profileForm, setProfileForm] = useState<PublishProfileInput>(initialProfile);
  const [selectedBuildId, setSelectedBuildId] = useState("");
  const [selectedProfileId, setSelectedProfileId] = useState("");
  const [editingProfileId, setEditingProfileId] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [messageTone, setMessageTone] = useState<"info" | "success" | "danger">("info");
  const [isSaving, setIsSaving] = useState(false);
  const [isTesting, setIsTesting] = useState(false);
  const [isPublishing, setIsPublishing] = useState(false);
  const [confirmingDeleteId, setConfirmingDeleteId] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    refreshData().catch((error: unknown) => {
      if (active) {
        setMessageTone("danger");
        setMessage(
          error instanceof ApiError ? error.message : t("publish.messageLoadFailed"),
        );
      }
    });
    return () => {
      active = false;
    };
  }, [projectId, t]);

  async function refreshData() {
    if (!projectId) {
      return;
    }
    const [profilePayload, buildPayload, activityPayload] = await Promise.all([
      api.listPublishProfiles(projectId),
      api.listBuilds(projectId),
      api.getProjectActivity(projectId),
    ]);

    setProfiles(profilePayload);
    setBuilds(buildPayload.filter((build) => build.status === "success"));
    setActivity(activityPayload);
    setSelectedBuildId((current) => {
      if (current) {
        return current;
      }
      const latestSuccess = buildPayload.find((build) => build.status === "success");
      return latestSuccess?.id ?? "";
    });
  }

  function updateField<K extends keyof PublishProfileInput>(field: K, value: PublishProfileInput[K]) {
    setProfileForm((current) => ({ ...current, [field]: value }));
  }

  function resetForm(protocol: PublishProtocol = "ftp") {
    setProfileForm({
      ...initialProfile,
      protocol,
      port: protocol === "ftp" ? 21 : 22,
    });
    setEditingProfileId(null);
  }

  function startEditing(profile: PublishProfileSummary) {
    setEditingProfileId(profile.id);
    setSelectedProfileId(profile.id);
    setProfileForm({
      name: profile.name,
      protocol: profile.protocol,
      host: profile.host,
      port: profile.port,
      username: profile.username,
      password: "",
      remote_path: profile.remote_path,
      passive_mode: profile.passive_mode,
      ftp_security_mode: profile.ftp_security_mode,
      sftp_host_key_policy: profile.sftp_host_key_policy,
    });
  }

  async function handleSaveProfile(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!projectId) {
      return;
    }

    setIsSaving(true);
    setMessage(null);
    try {
      const profile = editingProfileId
        ? await api.updatePublishProfile(projectId, editingProfileId, profileForm)
        : await api.createPublishProfile(projectId, profileForm);
      await refreshData();
      setSelectedProfileId(profile.id);
      resetForm(profileForm.protocol);
      setMessageTone("success");
      setMessage(editingProfileId ? t("publish.messageUpdated") : t("publish.messageSaved"));
    } catch (error: unknown) {
      setMessageTone("danger");
      setMessage(error instanceof ApiError ? error.message : t("publish.messageSaveFailed"));
    } finally {
      setIsSaving(false);
    }
  }

  async function handleDeleteProfile(profileId: string) {
    if (!projectId) {
      return;
    }
    if (confirmingDeleteId != profileId) {
      setConfirmingDeleteId(profileId);
      return;
    }

    setMessage(null);
    try {
      await api.deletePublishProfile(projectId, profileId);
      setConfirmingDeleteId(null);
      if (selectedProfileId === profileId) {
        setSelectedProfileId("");
      }
      if (editingProfileId === profileId) {
        resetForm(profileForm.protocol);
      }
      await refreshData();
      setMessageTone("success");
      setMessage(t("publish.messageRemoved"));
    } catch (error: unknown) {
      setMessageTone("danger");
      setMessage(error instanceof ApiError ? error.message : t("publish.messageRemoveFailed"));
    }
  }

  async function handleTestConnection() {
    if (!projectId) {
      return;
    }
    setIsTesting(true);
    setMessage(null);
    try {
      const payload = selectedProfileId
        ? await api.testPublishConnection(projectId, { profile_id: selectedProfileId })
        : await api.testPublishConnection(projectId, { profile: profileForm });
      setMessageTone(payload.success ? "success" : "info");
      setMessage(payload.message);
      await refreshData();
    } catch (error: unknown) {
      setMessageTone("danger");
      setMessage(error instanceof ApiError ? error.message : t("publish.messageTestFailed"));
    } finally {
      setIsTesting(false);
    }
  }

  async function handlePublish() {
    if (!selectedBuildId) {
      setMessageTone("danger");
      setMessage(t("publish.messageInvalidBuild"));
      return;
    }

    setIsPublishing(true);
    setMessage(null);
    try {
      const payload = selectedProfileId
        ? await api.publishBuild(selectedBuildId, currentProtocol(), { profile_id: selectedProfileId })
        : await api.publishBuild(selectedBuildId, profileForm.protocol, { profile: profileForm });
      await refreshData();
      setMessageTone("success");
      setMessage(`${payload.message} (${payload.files_uploaded})`);
    } catch (error: unknown) {
      setMessageTone("danger");
      setMessage(error instanceof ApiError ? error.message : t("publish.messagePublishFailed"));
    } finally {
      setIsPublishing(false);
    }
  }

  function currentProtocol(): PublishProtocol {
    const savedProfile = profiles.find((profile) => profile.id === selectedProfileId);
    return savedProfile?.protocol ?? profileForm.protocol;
  }

  return (
    <div className="space-y-6">
      {message ? <MessageBanner tone={messageTone} text={message} /> : null}

      <div className="grid gap-6 lg:grid-cols-[1.05fr_0.95fr]">
        <SectionCard
          eyebrow={t("publish.eyebrow")}
          title={t("publish.title")}
          subtitle={t("publish.subtitle")}
        >
          <form className="grid gap-4 md:grid-cols-2" onSubmit={handleSaveProfile}>
            <label className="space-y-2 md:col-span-2">
              <span className="forge-meta-label">{t("publish.profileName")}</span>
              <input
                value={profileForm.name}
                onChange={(event) => updateField("name", event.target.value)}
                className="forge-input px-4 py-3 text-sm"
              />
            </label>

            <label className="space-y-2">
              <span className="forge-meta-label">{t("publish.protocol")}</span>
              <select
                value={profileForm.protocol}
                onChange={(event) => {
                  const protocol = event.target.value as PublishProtocol;
                  updateField("protocol", protocol);
                  updateField("port", protocol === "ftp" ? 21 : 22);
                }}
                className="forge-input px-4 py-3 text-sm"
              >
                <option value="ftp">FTP</option>
                <option value="sftp">SFTP</option>
              </select>
            </label>

            {profileForm.protocol === "ftp" ? (
              <label className="space-y-2">
                <span className="forge-meta-label">{t("publish.ftpSecurityMode")}</span>
                <select
                  value={profileForm.ftp_security_mode}
                  onChange={(event) => updateField("ftp_security_mode", event.target.value as PublishProfileInput["ftp_security_mode"])}
                  className="forge-input px-4 py-3 text-sm"
                >
                  <option value="explicit_tls">{t("publish.ftpSecurity.explicit_tls")}</option>
                  <option value="insecure_plaintext">{t("publish.ftpSecurity.insecure_plaintext")}</option>
                </select>
              </label>
            ) : (
              <label className="space-y-2">
                <span className="forge-meta-label">{t("publish.sftpHostKeyPolicy")}</span>
                <select
                  value={profileForm.sftp_host_key_policy}
                  onChange={(event) => updateField("sftp_host_key_policy", event.target.value as PublishProfileInput["sftp_host_key_policy"])}
                  className="forge-input px-4 py-3 text-sm"
                >
                  <option value="trust_on_first_use">{t("publish.sftpPolicy.trust_on_first_use")}</option>
                  <option value="strict">{t("publish.sftpPolicy.strict")}</option>
                </select>
              </label>
            )}

            <label className="space-y-2">
              <span className="forge-meta-label">{t("publish.port")}</span>
              <input
                type="number"
                value={profileForm.port}
                onChange={(event) => updateField("port", Number(event.target.value))}
                className="forge-input px-4 py-3 text-sm"
              />
            </label>

            <label className="space-y-2 md:col-span-2">
              <span className="forge-meta-label">{t("publish.host")}</span>
              <input
                value={profileForm.host}
                onChange={(event) => updateField("host", event.target.value)}
                className="forge-input px-4 py-3 text-sm"
              />
            </label>

            <label className="space-y-2">
              <span className="forge-meta-label">{t("publish.username")}</span>
              <input
                value={profileForm.username}
                onChange={(event) => updateField("username", event.target.value)}
                className="forge-input px-4 py-3 text-sm"
              />
            </label>

            <label className="space-y-2">
              <span className="forge-meta-label">
                {t("publish.password")} {editingProfileId ? `(${t("publish.passwordHint")})` : ""}
              </span>
              <input
                type="password"
                value={profileForm.password ?? ""}
                onChange={(event) => updateField("password", event.target.value)}
                className="forge-input px-4 py-3 text-sm"
              />
            </label>

            <label className="space-y-2 md:col-span-2">
              <span className="forge-meta-label">{t("publish.remoteDirectory")}</span>
              <input
                value={profileForm.remote_path}
                onChange={(event) => updateField("remote_path", event.target.value)}
                className="forge-input px-4 py-3 text-sm"
              />
            </label>

            {profileForm.protocol === "ftp" ? (
              <label className="forge-subtitle flex items-center gap-3 text-sm md:col-span-2">
                <input
                  type="checkbox"
                  checked={profileForm.passive_mode}
                  onChange={(event) => updateField("passive_mode", event.target.checked)}
                  className="forge-checkbox h-4 w-4 rounded"
                />
                {t("publish.passiveMode")}
              </label>
            ) : (
              <div className="forge-guideline-panel rounded-2xl p-4 text-sm md:col-span-2">
                <p className="font-semibold">{t("publish.sftpPolicyNoticeTitle")}</p>
                <p className="mt-2">{t("publish.sftpPolicyNoticeBody")}</p>
              </div>
            )}

            <div className="flex flex-wrap gap-3 md:col-span-2">
              <button
                type="submit"
                disabled={isSaving}
                className="forge-button forge-button-primary"
              >
                {isSaving ? t("publish.saving") : editingProfileId ? t("publish.updateProfile") : t("publish.saveProfile")}
              </button>
              {editingProfileId ? (
                <button
                  type="button"
                  onClick={() => resetForm(profileForm.protocol)}
                  className="forge-button forge-button-secondary"
                >
                  {t("publish.cancelEdit")}
                </button>
              ) : null}
              <button
                type="button"
                onClick={handleTestConnection}
                disabled={isTesting}
                className="forge-button forge-button-secondary"
              >
                {isTesting ? t("publish.testing") : t("publish.testConnection")}
              </button>
            </div>
          </form>
        </SectionCard>

        <SectionCard
          eyebrow={t("publish.deployEyebrow")}
          title={t("publish.deployTitle")}
          subtitle={t("publish.deploySubtitle")}
        >
          {profiles.length === 0 ? (
            <EmptyState
              title={t("publish.emptyProfilesTitle")}
              description={t("publish.emptyProfilesDescription")}
            />
          ) : (
            <div className="space-y-4">
              <label className="space-y-2">
                <span className="forge-meta-label">{t("publish.savedProfile")}</span>
                <select
                  value={selectedProfileId}
                  onChange={(event) => setSelectedProfileId(event.target.value)}
                  className="forge-input px-4 py-3 text-sm"
                >
                  <option value="">{t("publish.useCurrentForm")}</option>
                  {profiles.map((profile) => (
                    <option key={profile.id} value={profile.id}>
                      {profile.name} • {profile.protocol.toUpperCase()} • {profile.host}
                    </option>
                  ))}
                </select>
              </label>

              <div className="space-y-3">
                {profiles.map((profile) => (
                  <div key={profile.id} className="forge-subtle-card rounded-[24px] p-4">
                    <div className="flex items-center justify-between gap-3">
                      <p className="font-['Space_Grotesk'] text-lg font-semibold">{profile.name}</p>
                      <StatusBadge tone={profile.protocol === "ftp" ? "warning" : "info"} label={profile.protocol} />
                    </div>
                    <p className="forge-subtitle mt-3 text-sm">
                      {profile.host}:{profile.port} • {profile.remote_path}
                    </p>
                    <p className="forge-tertiary mt-2 text-sm">
                      {profile.protocol === "ftp"
                        ? t(`publish.ftpSecurity.${profile.ftp_security_mode}`)
                        : t(`publish.sftpPolicy.${profile.sftp_host_key_policy}`)}
                    </p>
                    <div className="mt-4 flex flex-wrap gap-3">
                      <button
                        type="button"
                        onClick={() => startEditing(profile)}
                        className="forge-button forge-button-secondary"
                      >
                        {t("publish.edit")}
                      </button>
                      <button
                        type="button"
                        onClick={() => handleDeleteProfile(profile.id)}
                        className="forge-button forge-button-danger"
                      >
                        {confirmingDeleteId === profile.id ? t("publish.confirmRemove") : t("publish.remove")}
                      </button>
                      {confirmingDeleteId === profile.id ? (
                        <button
                          type="button"
                          onClick={() => setConfirmingDeleteId(null)}
                          className="forge-button forge-button-secondary"
                        >
                          {t("publish.cancelEdit")}
                        </button>
                      ) : null}
                    </div>
                    {confirmingDeleteId === profile.id ? (
                      <div className="forge-banner forge-banner-danger mt-4">
                        <p className="font-semibold">{t("publish.removeConfirmTitle")}</p>
                        <p className="mt-1">{t("publish.removeConfirmDescription")}</p>
                      </div>
                    ) : null}
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="mt-6 space-y-4">
            <label className="space-y-2">
              <span className="forge-meta-label">{t("publish.readyBuild")}</span>
              <select
                value={selectedBuildId}
                onChange={(event) => setSelectedBuildId(event.target.value)}
                className="forge-input px-4 py-3 text-sm"
              >
                <option value="">{t("publish.selectSuccessfulBuild")}</option>
                {builds.map((build) => (
                  <option key={build.id} value={build.id}>
                    {build.id} • {build.strategy_used}
                  </option>
                ))}
              </select>
            </label>

            <button
              type="button"
              onClick={handlePublish}
              disabled={isPublishing || !selectedBuildId}
              className="forge-button forge-button-success"
            >
              {isPublishing ? t("publish.publishing") : t("publish.publishBuild")}
            </button>
          </div>
        </SectionCard>
      </div>

      <SectionCard
        eyebrow={t("publish.auditEyebrow")}
        title={t("publish.auditTitle")}
        subtitle={t("publish.auditSubtitle")}
      >
        {!activity || activity.recent_audit_events.length === 0 ? (
          <EmptyState
            title={t("publish.noAuditTitle")}
            description={t("publish.noAuditDescription")}
          />
        ) : (
          <div className="space-y-3">
            {activity.recent_audit_events.map((event) => (
              <div key={event.id} className="forge-subtle-card rounded-[24px] p-4">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <p className="font-['Space_Grotesk'] text-lg font-semibold">{event.event_type}</p>
                  <p className="forge-meta-label">{formatDate(event.created_at)}</p>
                </div>
                <div className="forge-subtitle mt-3 grid gap-2 text-sm md:grid-cols-2">
                  <p>{t("publish.auditHost")}: {String(event.payload.host ?? t("publish.auditNotProvided"))}</p>
                  <p>{t("publish.auditBuild")}: {String(event.payload.build_id ?? t("publish.auditNotApplicable"))}</p>
                  <p>{t("publish.auditProfile")}: {String(event.payload.profile_id ?? t("publish.auditInline"))}</p>
                  <p>{t("publish.auditDestination")}: {String(event.payload.remote_path ?? t("publish.auditNotProvided"))}</p>
                </div>
              </div>
            ))}
          </div>
        )}
      </SectionCard>
    </div>
  );
}
