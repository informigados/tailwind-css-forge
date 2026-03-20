import type {
  AnalysisSummary,
  AppSettings,
  BuildReport,
  BuildStartResponse,
  BuildSummary,
  ExportSummary,
  HealthStatus,
  HistoryProjectEntry,
  ProjectActivity,
  ProjectSummary,
  PublishConnectionResult,
  PublishProfileInput,
  PublishProfileSummary,
  PublishResult,
} from "lib/types";
import { translate } from "i18n/runtime";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL?.toString() ??
  (window.location.port === "5173" ? "http://127.0.0.1:8000/api" : `${window.location.origin}/api`);

class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
    ...init,
  });

  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as { detail?: string } | null;
    throw new ApiError(payload?.detail ?? translate("api.communicationFailed"), response.status);
  }

  return (await response.json()) as T;
}

export const api = {
  async getHealth(): Promise<HealthStatus> {
    return request<HealthStatus>("/health");
  },

  async listProjects(): Promise<ProjectSummary[]> {
    return request<ProjectSummary[]>("/projects");
  },

  async importProject(sourcePath: string): Promise<ProjectSummary> {
    const payload = await request<{ project: ProjectSummary }>("/projects/import", {
      method: "POST",
      body: JSON.stringify({ source_path: sourcePath }),
    });
    return payload.project;
  },

  async getProject(projectId: string): Promise<ProjectSummary> {
    return request<ProjectSummary>(`/projects/${projectId}`);
  },

  async analyzeProject(projectId: string): Promise<AnalysisSummary> {
    const payload = await request<{ analysis: AnalysisSummary }>(`/projects/${projectId}/analyze`, {
      method: "POST",
    });
    return payload.analysis;
  },

  async getLatestAnalysis(projectId: string): Promise<AnalysisSummary> {
    return request<AnalysisSummary>(`/projects/${projectId}/analysis/latest`);
  },

  async buildProject(projectId: string, minify: boolean): Promise<BuildStartResponse> {
    return request<BuildStartResponse>(`/projects/${projectId}/build`, {
      method: "POST",
      body: JSON.stringify({ minify }),
    });
  },

  async cancelBuild(buildId: string): Promise<BuildSummary> {
    const payload = await request<{ build: BuildSummary }>(`/builds/${buildId}/cancel`, {
      method: "POST",
    });
    return payload.build;
  },

  async listBuilds(projectId: string): Promise<BuildSummary[]> {
    return request<BuildSummary[]>(`/projects/${projectId}/builds`);
  },

  async getBuild(buildId: string): Promise<BuildSummary> {
    return request<BuildSummary>(`/builds/${buildId}`);
  },

  async getBuildReport(buildId: string): Promise<BuildReport> {
    return request<BuildReport>(`/builds/${buildId}/report`);
  },

  async getBuildLog(buildId: string): Promise<{ build_id: string; log: string }> {
    return request<{ build_id: string; log: string }>(`/builds/${buildId}/log`);
  },

  async exportZip(buildId: string): Promise<ExportSummary> {
    const payload = await request<{ export: ExportSummary }>(`/builds/${buildId}/export/zip`, {
      method: "POST",
    });
    return payload.export;
  },

  async listPublishProfiles(projectId: string): Promise<PublishProfileSummary[]> {
    return request<PublishProfileSummary[]>(`/projects/${projectId}/publish/profiles`);
  },

  async createPublishProfile(
    projectId: string,
    profile: PublishProfileInput,
  ): Promise<PublishProfileSummary> {
    const payload = await request<{ profile: PublishProfileSummary }>(
      `/projects/${projectId}/publish/profiles`,
      {
        method: "POST",
        body: JSON.stringify(profile),
      },
    );
    return payload.profile;
  },

  async updatePublishProfile(
    projectId: string,
    profileId: string,
    profile: PublishProfileInput,
  ): Promise<PublishProfileSummary> {
    const payload = await request<{ profile: PublishProfileSummary }>(
      `/projects/${projectId}/publish/profiles/${profileId}`,
      {
        method: "PUT",
        body: JSON.stringify(profile),
      },
    );
    return payload.profile;
  },

  async deletePublishProfile(
    projectId: string,
    profileId: string,
  ): Promise<{ deleted_profile_id: string }> {
    return request<{ deleted_profile_id: string }>(
      `/projects/${projectId}/publish/profiles/${profileId}`,
      {
        method: "DELETE",
      },
    );
  },

  async testPublishConnection(
    projectId: string,
    input:
      | { profile_id: string }
      | { profile: PublishProfileInput },
  ): Promise<PublishConnectionResult> {
    return request<PublishConnectionResult>(`/projects/${projectId}/publish/test`, {
      method: "POST",
      body: JSON.stringify(input),
    });
  },

  async publishBuild(
    buildId: string,
    protocol: "ftp" | "sftp",
    input:
      | { profile_id: string }
      | { profile: PublishProfileInput },
  ): Promise<PublishResult> {
    return request<PublishResult>(`/builds/${buildId}/publish/${protocol}`, {
      method: "POST",
      body: JSON.stringify(input),
    });
  },

  async getSettings(): Promise<AppSettings> {
    const payload = await request<{ settings: AppSettings }>("/settings");
    return payload.settings;
  },

  async updateSettings(settings: AppSettings): Promise<AppSettings> {
    const payload = await request<{ settings: AppSettings }>("/settings", {
      method: "PUT",
      body: JSON.stringify(settings),
    });
    return payload.settings;
  },

  async listHistory(): Promise<HistoryProjectEntry[]> {
    return request<HistoryProjectEntry[]>("/history");
  },

  async getProjectActivity(projectId: string): Promise<ProjectActivity> {
    return request<ProjectActivity>(`/history/projects/${projectId}`);
  },
};

export { ApiError };
