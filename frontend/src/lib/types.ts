export type PublishProtocol = "ftp" | "sftp";
export type FtpSecurityMode = "explicit_tls" | "insecure_plaintext";
export type SftpHostKeyPolicy = "strict" | "trust_on_first_use";

export type ProjectSummary = {
  id: string;
  name: string;
  source_path: string;
  workspace_path: string;
  fingerprint: string;
  created_at: string;
  updated_at: string;
  last_status: string | null;
};

export type AnalysisSummary = {
  id: string;
  project_id: string;
  tailwind_detected: boolean;
  strategy_hint: string | null;
  probable_major_version: number | null;
  confidence: number;
  signals: string[];
  warnings: string[];
  framework_hints: string[];
  project_style: string | null;
  created_at: string;
  build_plan: {
    strategy?: string;
    requires_conversion?: boolean;
    ready_for_build?: boolean;
    risk_level?: string;
    execution_mode?: string;
    requires_manual_review?: boolean;
    recommended_action?: string;
    pipeline_steps?: string[];
    compatibility_notes?: string[];
    warnings?: string[];
  };
};

export type BuildSummary = {
  id: string;
  project_id: string;
  analysis_id: string | null;
  strategy_used: string;
  status: string;
  progress_percent: number;
  current_step: string | null;
  current_message: string | null;
  cancel_requested: boolean;
  started_at: string | null;
  finished_at: string | null;
  duration_ms: number | null;
  output_path: string | null;
  report_path: string | null;
  log_path: string | null;
};

export type BuildResult = {
  status: string;
  strategy_used: string;
  outputs: string[];
  warnings: string[];
  errors: string[];
  duration_ms: number;
  dist_path: string | null;
  report_path: string | null;
  log_path: string | null;
};

export type BuildStartResponse = {
  build: BuildSummary;
  result: BuildResult | null;
};

export type BuildProgressEvent = {
  type: "progress";
  build_id: string;
  status: string;
  progress_percent: number;
  step: string | null;
  message: string | null;
  cancel_requested: boolean;
  started_at: string | null;
  finished_at: string | null;
};

export type BuildReport = {
  generated_at: string;
  project_id: string;
  build_id: string;
  strategy_used: string;
  status: string;
  analysis: AnalysisSummary;
  build_plan: AnalysisSummary["build_plan"];
  outputs: string[];
  warnings: string[];
  errors: string[];
  duration_ms: number;
};

export type ExportSummary = {
  id: string;
  build_id: string;
  format: string;
  output_path: string;
  created_at: string;
};

export type PublishProfileSummary = {
  id: string;
  project_id: string;
  name: string;
  protocol: PublishProtocol;
  host: string;
  port: number;
  username: string;
  remote_path: string;
  passive_mode: boolean;
  ftp_security_mode: FtpSecurityMode;
  sftp_host_key_policy: SftpHostKeyPolicy;
  has_password: boolean;
};

export type PublishConnectionResult = {
  protocol: PublishProtocol;
  host: string;
  port: number;
  success: boolean;
  message: string;
};

export type PublishResult = {
  build_id: string;
  protocol: PublishProtocol;
  remote_path: string;
  files_uploaded: number;
  success: boolean;
  message: string;
};

export type HealthStatus = {
  status: string;
  app: string;
  environment: string;
  version: string;
};

export type PublishProfileInput = {
  name: string;
  protocol: PublishProtocol;
  host: string;
  port: number;
  username: string;
  password?: string | null;
  remote_path: string;
  passive_mode: boolean;
  ftp_security_mode: FtpSecurityMode;
  sftp_host_key_policy: SftpHostKeyPolicy;
};

export type AppSettings = {
  language: string;
  theme: string;
  default_workspace_path: string;
  default_exports_path: string;
  backup_before_build: boolean;
  default_minify: boolean;
  detailed_logs: boolean;
  build_timeout_seconds: number;
};

export type AuditLogEntry = {
  id: string;
  event_type: string;
  created_at: string;
  payload: Record<string, unknown>;
};

export type HistoryProjectEntry = {
  project: ProjectSummary;
  latest_build: BuildSummary | null;
  latest_analysis_at: string | null;
  publish_profile_count: number;
  recent_audit_events: AuditLogEntry[];
};

export type ProjectActivity = {
  project: ProjectSummary;
  latest_analysis_at: string | null;
  recent_builds: BuildSummary[];
  publish_profile_count: number;
  recent_audit_events: AuditLogEntry[];
};
