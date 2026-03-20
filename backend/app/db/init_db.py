from __future__ import annotations

from app.db.session import Database


SCHEMA = """
CREATE TABLE IF NOT EXISTS projects (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    source_path TEXT NOT NULL,
    workspace_path TEXT NOT NULL,
    fingerprint TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    last_status TEXT
);

CREATE TABLE IF NOT EXISTS analyses (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    tailwind_detected INTEGER NOT NULL,
    strategy_hint TEXT,
    probable_major_version INTEGER,
    confidence REAL,
    signals_json TEXT NOT NULL,
    warnings_json TEXT NOT NULL,
    framework_hints_json TEXT NOT NULL DEFAULT '[]',
    project_style TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY(project_id) REFERENCES projects(id)
);

CREATE TABLE IF NOT EXISTS builds (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    analysis_id TEXT,
    strategy_used TEXT NOT NULL,
    status TEXT NOT NULL,
    progress_percent INTEGER NOT NULL DEFAULT 0,
    current_step TEXT,
    current_message TEXT,
    cancel_requested INTEGER NOT NULL DEFAULT 0,
    started_at TEXT,
    finished_at TEXT,
    duration_ms INTEGER,
    output_path TEXT,
    report_path TEXT,
    log_path TEXT
);

CREATE TABLE IF NOT EXISTS exports (
    id TEXT PRIMARY KEY,
    build_id TEXT NOT NULL,
    format TEXT NOT NULL,
    output_path TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS publish_profiles (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    name TEXT NOT NULL,
    protocol TEXT NOT NULL,
    host TEXT NOT NULL,
    port INTEGER NOT NULL,
    username TEXT NOT NULL,
    password_encrypted TEXT,
    remote_path TEXT,
    passive_mode INTEGER NOT NULL DEFAULT 1,
    ftp_security_mode TEXT NOT NULL DEFAULT 'explicit_tls',
    sftp_host_key_policy TEXT NOT NULL DEFAULT 'trust_on_first_use'
);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS audit_logs (
    id TEXT PRIMARY KEY,
    event_type TEXT NOT NULL,
    payload_json TEXT,
    created_at TEXT NOT NULL
);
"""


def init_db(database: Database) -> None:
    _configure_database(database)
    statements = [statement.strip() for statement in SCHEMA.split(";") if statement.strip()]
    for statement in statements:
        database.execute(statement)
    _ensure_analysis_columns(database)
    _ensure_build_columns(database)
    _ensure_publish_profile_columns(database)


def _configure_database(database: Database) -> None:
    with database.connect() as connection:
        connection.execute("PRAGMA journal_mode = WAL")
        connection.execute("PRAGMA synchronous = NORMAL")
        connection.commit()


def _ensure_analysis_columns(database: Database) -> None:
    columns = database.fetch_all("PRAGMA table_info(analyses)")
    column_names = {column["name"] for column in columns}
    if "framework_hints_json" not in column_names:
        database.execute("ALTER TABLE analyses ADD COLUMN framework_hints_json TEXT NOT NULL DEFAULT '[]'")
    if "project_style" not in column_names:
        database.execute("ALTER TABLE analyses ADD COLUMN project_style TEXT")


def _ensure_build_columns(database: Database) -> None:
    columns = database.fetch_all("PRAGMA table_info(builds)")
    column_names = {column["name"] for column in columns}
    if "progress_percent" not in column_names:
        database.execute("ALTER TABLE builds ADD COLUMN progress_percent INTEGER NOT NULL DEFAULT 0")
    if "current_step" not in column_names:
        database.execute("ALTER TABLE builds ADD COLUMN current_step TEXT")
    if "current_message" not in column_names:
        database.execute("ALTER TABLE builds ADD COLUMN current_message TEXT")
    if "cancel_requested" not in column_names:
        database.execute("ALTER TABLE builds ADD COLUMN cancel_requested INTEGER NOT NULL DEFAULT 0")


def _ensure_publish_profile_columns(database: Database) -> None:
    columns = database.fetch_all("PRAGMA table_info(publish_profiles)")
    column_names = {column["name"] for column in columns}
    if "passive_mode" not in column_names:
        database.execute(
            "ALTER TABLE publish_profiles ADD COLUMN passive_mode INTEGER NOT NULL DEFAULT 1",
        )
    if "ftp_security_mode" not in column_names:
        database.execute(
            "ALTER TABLE publish_profiles ADD COLUMN ftp_security_mode TEXT NOT NULL DEFAULT 'explicit_tls'",
        )
    if "sftp_host_key_policy" not in column_names:
        database.execute(
            "ALTER TABLE publish_profiles ADD COLUMN sftp_host_key_policy TEXT NOT NULL DEFAULT 'trust_on_first_use'",
        )
