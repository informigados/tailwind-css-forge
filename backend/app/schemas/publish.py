from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


PublishProtocol = Literal["ftp", "sftp"]
FtpSecurityMode = Literal["explicit_tls", "insecure_plaintext"]
SftpHostKeyPolicy = Literal["strict", "trust_on_first_use"]


class PublishProfileInput(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    protocol: PublishProtocol
    host: str = Field(min_length=1, max_length=255)
    port: int = Field(gt=0, le=65535)
    username: str = Field(min_length=1, max_length=255)
    password: str | None = Field(default=None, max_length=1024)
    remote_path: str = Field(min_length=1, max_length=1024)
    passive_mode: bool = True
    ftp_security_mode: FtpSecurityMode = "explicit_tls"
    sftp_host_key_policy: SftpHostKeyPolicy = "trust_on_first_use"


class PublishProfileSummary(BaseModel):
    id: str
    project_id: str
    name: str
    protocol: PublishProtocol
    host: str
    port: int
    username: str
    remote_path: str
    passive_mode: bool
    ftp_security_mode: FtpSecurityMode
    sftp_host_key_policy: SftpHostKeyPolicy
    has_password: bool


class PublishProfileResponse(BaseModel):
    profile: PublishProfileSummary


class PublishProfileDeleteResponse(BaseModel):
    deleted_profile_id: str


class PublishConnectionTestRequest(BaseModel):
    profile_id: str | None = None
    profile: PublishProfileInput | None = None


class PublishConnectionTestResponse(BaseModel):
    protocol: PublishProtocol
    host: str
    port: int
    success: bool
    message: str


class PublishBuildRequest(BaseModel):
    profile_id: str | None = None
    profile: PublishProfileInput | None = None


class PublishResultResponse(BaseModel):
    build_id: str
    protocol: PublishProtocol
    remote_path: str
    files_uploaded: int
    success: bool
    message: str
