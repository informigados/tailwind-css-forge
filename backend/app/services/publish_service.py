from __future__ import annotations

import json
import uuid
from pathlib import Path

from fastapi import HTTPException, status

from app.db.session import Database
from app.publishers.ftp_publisher import FtpPublisher
from app.publishers.sftp_publisher import SftpPublisher
from app.schemas.publish import (
    PublishBuildRequest,
    PublishConnectionTestRequest,
    PublishConnectionTestResponse,
    PublishProfileDeleteResponse,
    PublishProfileInput,
    PublishProfileSummary,
    PublishResultResponse,
)
from app.services.build_service import BuildService
from app.services.project_service import ProjectService
from app.utils.secrets import SecretManager
from app.utils.time import utc_now_iso


class PublishService:
    def __init__(
        self,
        database: Database,
        project_service: ProjectService,
        build_service: BuildService,
        secret_manager: SecretManager,
        known_hosts_path: Path,
        ftp_publisher: FtpPublisher | None = None,
        sftp_publisher: SftpPublisher | None = None,
    ) -> None:
        self.database = database
        self.project_service = project_service
        self.build_service = build_service
        self.secret_manager = secret_manager
        self.known_hosts_path = known_hosts_path
        self.publishers = {
            "ftp": ftp_publisher or FtpPublisher(),
            "sftp": sftp_publisher or SftpPublisher(),
        }

    def create_profile(self, project_id: str, payload: PublishProfileInput) -> PublishProfileSummary:
        self.project_service.get_project(project_id)
        profile_id = f"profile_{uuid.uuid4().hex[:12]}"
        password_encrypted = self.secret_manager.encrypt(payload.password) if payload.password else None
        self.database.execute(
            """
            INSERT INTO publish_profiles (
                id, project_id, name, protocol, host, port, username, password_encrypted, remote_path,
                passive_mode, ftp_security_mode, sftp_host_key_policy
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                profile_id,
                project_id,
                payload.name,
                payload.protocol,
                payload.host,
                payload.port,
                payload.username,
                password_encrypted,
                payload.remote_path,
                int(payload.passive_mode),
                payload.ftp_security_mode,
                payload.sftp_host_key_policy,
            ),
        )
        self._write_audit_log(
            "publish_profile_created",
            {
                "project_id": project_id,
                "profile_id": profile_id,
                "protocol": payload.protocol,
                "ftp_security_mode": payload.ftp_security_mode,
                "sftp_host_key_policy": payload.sftp_host_key_policy,
            },
        )
        return self.get_profile(project_id, profile_id)

    def update_profile(
        self,
        project_id: str,
        profile_id: str,
        payload: PublishProfileInput,
    ) -> PublishProfileSummary:
        existing = self._get_profile_row(project_id, profile_id)
        password_encrypted = existing["password_encrypted"]
        if payload.password:
            password_encrypted = self.secret_manager.encrypt(payload.password)

        self.database.execute(
            """
            UPDATE publish_profiles
            SET name = ?, protocol = ?, host = ?, port = ?, username = ?, password_encrypted = ?,
                remote_path = ?, passive_mode = ?, ftp_security_mode = ?, sftp_host_key_policy = ?
            WHERE id = ? AND project_id = ?
            """,
            (
                payload.name,
                payload.protocol,
                payload.host,
                payload.port,
                payload.username,
                password_encrypted,
                payload.remote_path,
                int(payload.passive_mode),
                payload.ftp_security_mode,
                payload.sftp_host_key_policy,
                profile_id,
                project_id,
            ),
        )
        self._write_audit_log(
            "publish_profile_updated",
            {
                "project_id": project_id,
                "profile_id": profile_id,
                "protocol": payload.protocol,
                "ftp_security_mode": payload.ftp_security_mode,
                "sftp_host_key_policy": payload.sftp_host_key_policy,
            },
        )
        return self.get_profile(project_id, profile_id)

    def delete_profile(self, project_id: str, profile_id: str) -> PublishProfileDeleteResponse:
        self._get_profile_row(project_id, profile_id)
        self.database.execute(
            "DELETE FROM publish_profiles WHERE id = ? AND project_id = ?",
            (profile_id, project_id),
        )
        self._write_audit_log(
            "publish_profile_deleted",
            {"project_id": project_id, "profile_id": profile_id},
        )
        return PublishProfileDeleteResponse(deleted_profile_id=profile_id)

    def list_profiles(self, project_id: str) -> list[PublishProfileSummary]:
        self.project_service.get_project(project_id)
        rows = self.database.fetch_all(
            """
            SELECT id, project_id, name, protocol, host, port, username, remote_path, passive_mode,
                   ftp_security_mode, sftp_host_key_policy, password_encrypted
            FROM publish_profiles
            WHERE project_id = ?
            ORDER BY name ASC
            """,
            (project_id,),
        )
        return [self._to_profile_summary(row) for row in rows]

    def get_profile(self, project_id: str, profile_id: str) -> PublishProfileSummary:
        return self._to_profile_summary(self._get_profile_row(project_id, profile_id))

    def _get_profile_row(self, project_id: str, profile_id: str) -> dict:
        self.project_service.get_project(project_id)
        row = self.database.fetch_one(
            """
            SELECT id, project_id, name, protocol, host, port, username, remote_path, passive_mode,
                   ftp_security_mode, sftp_host_key_policy, password_encrypted
            FROM publish_profiles
            WHERE id = ? AND project_id = ?
            """,
            (profile_id, project_id),
        )
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Perfil de publicação não encontrado.")
        return row

    def test_connection(
        self,
        project_id: str,
        payload: PublishConnectionTestRequest,
    ) -> PublishConnectionTestResponse:
        config = self._resolve_publish_config(project_id, payload.profile_id, payload.profile)
        response = self.publishers[config["protocol"]].test_connection(config)
        self._write_audit_log(
            "publish_connection_test",
            {
                "project_id": project_id,
                "protocol": config["protocol"],
                "host": config["host"],
                "ftp_security_mode": config.get("ftp_security_mode"),
                "sftp_host_key_policy": config.get("sftp_host_key_policy"),
            },
        )
        return PublishConnectionTestResponse(**response)

    def publish_build(
        self,
        build_id: str,
        protocol: str,
        payload: PublishBuildRequest,
    ) -> PublishResultResponse:
        build = self.build_service.get_build(build_id)
        if build.status != "success" or not build.output_path:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A publicação exige um build concluído com sucesso.",
            )

        config = self._resolve_publish_config(build.project_id, payload.profile_id, payload.profile)
        if config["protocol"] != protocol:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="O protocolo do perfil não corresponde ao endpoint de publicação escolhido.",
            )

        result = self.publishers[protocol].publish_directory(Path(build.output_path), config)
        self._write_audit_log(
            "build_published",
            {
                "build_id": build_id,
                "project_id": build.project_id,
                "protocol": protocol,
                "host": config["host"],
                "remote_path": config["remote_path"],
                "files_uploaded": result["files_uploaded"],
                "ftp_security_mode": config.get("ftp_security_mode"),
                "sftp_host_key_policy": config.get("sftp_host_key_policy"),
            },
        )
        return PublishResultResponse(build_id=build_id, **result)

    def _resolve_publish_config(
        self,
        project_id: str,
        profile_id: str | None,
        profile: PublishProfileInput | None,
    ) -> dict:
        if profile_id:
            row = self._get_profile_row(project_id, profile_id)
            if not row["password_encrypted"]:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="O perfil selecionado não possui senha salva.",
                )
            return {
                "protocol": row["protocol"],
                "host": row["host"],
                "port": row["port"],
                "username": row["username"],
                "password": self.secret_manager.decrypt(row["password_encrypted"]),
                "remote_path": row["remote_path"],
                "passive_mode": bool(row["passive_mode"]),
                "ftp_security_mode": row["ftp_security_mode"],
                "sftp_host_key_policy": row["sftp_host_key_policy"],
                "known_hosts_path": str(self.known_hosts_path),
            }

        if profile is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Informe `profile_id` ou um bloco `profile` para publicar/testar conexão.",
            )
        if not profile.password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Senha obrigatória para conexão sem perfil salvo.",
            )

        return profile.model_dump() | {"known_hosts_path": str(self.known_hosts_path)}

    def _to_profile_summary(self, row: dict) -> PublishProfileSummary:
        return PublishProfileSummary(
            id=row["id"],
            project_id=row["project_id"],
            name=row["name"],
            protocol=row["protocol"],
            host=row["host"],
            port=row["port"],
            username=row["username"],
            remote_path=row["remote_path"],
            passive_mode=bool(row["passive_mode"]),
            ftp_security_mode=row["ftp_security_mode"],
            sftp_host_key_policy=row["sftp_host_key_policy"],
            has_password=bool(row["password_encrypted"]),
        )

    def _write_audit_log(self, event_type: str, payload: dict) -> None:
        self.database.execute(
            """
            INSERT INTO audit_logs (id, event_type, payload_json, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (f"audit_{uuid.uuid4().hex[:12]}", event_type, json.dumps(payload), utc_now_iso()),
        )
