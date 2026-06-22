from __future__ import annotations

import base64
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from io import BytesIO
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import sqlite3
import tempfile
from typing import Any
from urllib.parse import quote
import zipfile

import requests


DEFAULT_BRANCH = "cloud-data"
DEFAULT_SOURCE_BRANCH = "codex/fashuo-socratic-local-tool"
DEFAULT_SNAPSHOT_PATH = "fashuo-cloud-snapshot.zip"
GITHUB_API_BASE = "https://api.github.com"
SNAPSHOT_DIRS = ("uploads", "documents", "provenance")
EXCLUDED_SUFFIXES = (".db-wal", ".db-shm")


class CloudSyncError(RuntimeError):
    pass


@dataclass(frozen=True)
class CloudSyncConfig:
    enabled: bool = False
    provider: str = "github"
    repo: str = ""
    branch: str = DEFAULT_BRANCH
    source_branch: str = DEFAULT_SOURCE_BRANCH
    snapshot_path: str = DEFAULT_SNAPSHOT_PATH
    github_token: str = ""


@dataclass(frozen=True)
class CloudSyncResult:
    status: str
    message: str = ""
    detail: str = ""


ResponseLike = Any
RequestFunc = Callable[..., ResponseLike]


def load_cloud_sync_config(
    secrets: object | None = None,
    environ: Mapping[str, str] | None = None,
) -> CloudSyncConfig:
    environ = os.environ if environ is None else environ
    secrets = {} if secrets is None else secrets
    persistence = _mapping_get(secrets, "persistence", {})
    enabled = _as_bool(
        _mapping_get(persistence, "enabled", _env_get(environ, "PERSISTENCE_ENABLED", "false"))
    )
    return CloudSyncConfig(
        enabled=enabled,
        provider=str(
            _mapping_get(persistence, "provider", _env_get(environ, "PERSISTENCE_PROVIDER", "github"))
            or "github"
        ),
        repo=str(
            _mapping_get(
                persistence,
                "repo",
                _env_get(environ, "PERSISTENCE_REPO", _env_get(environ, "GITHUB_REPOSITORY", "")),
            )
            or ""
        ),
        branch=str(
            _mapping_get(persistence, "branch", _env_get(environ, "PERSISTENCE_BRANCH", DEFAULT_BRANCH))
            or DEFAULT_BRANCH
        ),
        source_branch=str(
            _mapping_get(
                persistence,
                "source_branch",
                _env_get(environ, "PERSISTENCE_SOURCE_BRANCH", DEFAULT_SOURCE_BRANCH),
            )
            or DEFAULT_SOURCE_BRANCH
        ),
        snapshot_path=str(
            _mapping_get(
                persistence,
                "snapshot_path",
                _env_get(environ, "PERSISTENCE_SNAPSHOT_PATH", DEFAULT_SNAPSHOT_PATH),
            )
            or DEFAULT_SNAPSHOT_PATH
        ),
        github_token=str(
            _mapping_get(
                persistence,
                "github_token",
                _env_get(environ, "GITHUB_SYNC_TOKEN", _env_get(environ, "GITHUB_TOKEN", "")),
            )
            or ""
        ),
    )


def validate_cloud_sync_config(config: CloudSyncConfig) -> None:
    if not config.enabled:
        return
    if config.provider != "github":
        raise CloudSyncError(f"unsupported persistence provider: {config.provider}")
    missing = []
    if not config.repo:
        missing.append("repo")
    if not config.github_token:
        missing.append("github_token")
    if missing:
        raise CloudSyncError("missing persistence config: " + ", ".join(missing))
    if "/" not in config.repo:
        raise CloudSyncError("persistence repo must use owner/repo format")


def get_cloud_sync_status_label(config: CloudSyncConfig) -> str:
    return "GitHub 云端快照" if config.enabled else "本地临时存储"


def build_snapshot_archive(data_root: Path | str, app_version: str = "", reason: str = "") -> bytes:
    data_root = Path(data_root)
    files: list[str] = []
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        db_path = data_root / "fashuo.db"
        if db_path.exists():
            archive.write(db_path, "fashuo.db")
            files.append("fashuo.db")

        for dirname in SNAPSHOT_DIRS:
            directory = data_root / dirname
            if not directory.exists():
                continue
            for path in sorted(directory.rglob("*")):
                if not path.is_file() or _should_exclude(path):
                    continue
                arcname = path.relative_to(data_root).as_posix()
                _assert_safe_archive_name(arcname)
                archive.write(path, arcname)
                files.append(arcname)

        manifest = {
            "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "app_version": app_version,
            "reason": reason,
            "files": files,
            "snapshot_version": 1,
        }
        archive.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
    return buffer.getvalue()


def restore_snapshot_archive(archive_bytes: bytes, data_root: Path | str) -> None:
    data_root = Path(data_root)
    data_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="fashuo-cloud-restore-") as temp_name:
        temp_root = Path(temp_name)
        with zipfile.ZipFile(BytesIO(archive_bytes), "r") as archive:
            for info in archive.infolist():
                _assert_safe_archive_name(info.filename)
                if info.is_dir():
                    continue
                target = temp_root / info.filename
                target.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(info, "r") as source, target.open("wb") as destination:
                    shutil.copyfileobj(source, destination)

        restored_db = temp_root / "fashuo.db"
        if restored_db.exists():
            shutil.copy2(restored_db, data_root / "fashuo.db")

        for dirname in SNAPSHOT_DIRS:
            source_dir = temp_root / dirname
            target_dir = data_root / dirname
            if target_dir.exists():
                shutil.rmtree(target_dir)
            if source_dir.exists():
                shutil.copytree(source_dir, target_dir)
            else:
                target_dir.mkdir(parents=True, exist_ok=True)


class GitHubSnapshotSync:
    def __init__(
        self,
        config: CloudSyncConfig,
        request_func: RequestFunc | None = None,
        app_version: str = "",
    ):
        self.config = config
        self.request_func = request_func or requests.request
        self.app_version = app_version

    def restore(self, data_root: Path | str) -> CloudSyncResult:
        if not self.config.enabled:
            return CloudSyncResult(status="disabled", message="persistence disabled")
        validate_cloud_sync_config(self.config)

        response = self._request(
            "GET",
            self._contents_url() + f"?ref={quote(self.config.branch, safe='')}",
        )
        if response.status_code == 404:
            return CloudSyncResult(status="missing", message="remote snapshot missing")
        self._raise_for_status(response, "download snapshot metadata")
        payload = response.json()
        archive_bytes = self._decode_content_payload(payload)
        restore_snapshot_archive(archive_bytes, data_root)
        return CloudSyncResult(status="restored", message="remote snapshot restored")

    def upload(self, data_root: Path | str, reason: str = "sqlite_commit") -> CloudSyncResult:
        if not self.config.enabled:
            return CloudSyncResult(status="disabled", message="persistence disabled")
        validate_cloud_sync_config(self.config)

        data_root = Path(data_root)
        _checkpoint_sqlite(data_root / "fashuo.db")
        self._ensure_branch()
        current_sha = self._get_existing_snapshot_sha()
        archive = build_snapshot_archive(data_root, app_version=self.app_version, reason=reason)
        payload: dict[str, object] = {
            "message": f"chore(data): update fashuo cloud snapshot ({reason})",
            "content": base64.b64encode(archive).decode("ascii"),
            "branch": self.config.branch,
        }
        if current_sha:
            payload["sha"] = current_sha

        response = self._request("PUT", self._contents_url(), json=payload)
        if response.status_code not in (200, 201):
            self._raise_for_status(response, "upload snapshot")
        return CloudSyncResult(status="uploaded", message="remote snapshot uploaded")

    def _decode_content_payload(self, payload: dict[str, object]) -> bytes:
        encoded = payload.get("content")
        if isinstance(encoded, str) and encoded.strip():
            return base64.b64decode(encoded.replace("\n", ""))

        download_url = payload.get("download_url")
        if isinstance(download_url, str) and download_url:
            response = self._request("GET", download_url)
            self._raise_for_status(response, "download snapshot archive")
            return bytes(response.content)

        raise CloudSyncError("GitHub snapshot response did not include content")

    def _ensure_branch(self) -> None:
        response = self._request("GET", self._ref_url(self.config.branch))
        if response.status_code == 200:
            return
        if response.status_code != 404:
            self._raise_for_status(response, "check snapshot branch")
        if self.config.branch == self.config.source_branch:
            raise CloudSyncError(f"snapshot branch does not exist: {self.config.branch}")

        source_response = self._request("GET", self._ref_url(self.config.source_branch))
        self._raise_for_status(source_response, "read source branch")
        source_payload = source_response.json()
        source_sha = _nested_get(source_payload, ("object", "sha"))
        if not isinstance(source_sha, str) or not source_sha:
            raise CloudSyncError("GitHub source branch response did not include sha")

        create_response = self._request(
            "POST",
            self._repo_url("/git/refs"),
            json={"ref": f"refs/heads/{self.config.branch}", "sha": source_sha},
        )
        if create_response.status_code not in (200, 201):
            self._raise_for_status(create_response, "create snapshot branch")

    def _get_existing_snapshot_sha(self) -> str:
        response = self._request(
            "GET",
            self._contents_url() + f"?ref={quote(self.config.branch, safe='')}",
        )
        if response.status_code == 404:
            return ""
        self._raise_for_status(response, "read existing snapshot")
        sha = response.json().get("sha")
        return sha if isinstance(sha, str) else ""

    def _request(self, method: str, url: str, **kwargs: object) -> ResponseLike:
        headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {self.config.github_token}",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        extra_headers = kwargs.pop("headers", None)
        if isinstance(extra_headers, dict):
            headers.update(extra_headers)
        return self.request_func(method, url, headers=headers, timeout=20, **kwargs)

    def _raise_for_status(self, response: ResponseLike, action: str) -> None:
        if 200 <= int(response.status_code) < 300:
            return
        message = getattr(response, "text", "") or ""
        raise CloudSyncError(f"GitHub {action} failed: HTTP {response.status_code} {message}")

    def _repo_url(self, path: str) -> str:
        return f"{GITHUB_API_BASE}/repos/{self.config.repo}{path}"

    def _contents_url(self) -> str:
        snapshot_path = quote(self.config.snapshot_path.strip("/"), safe="/")
        return self._repo_url(f"/contents/{snapshot_path}")

    def _ref_url(self, branch: str) -> str:
        return self._repo_url(f"/git/ref/heads/{quote(branch, safe='/')}")


def _checkpoint_sqlite(db_path: Path) -> None:
    if not db_path.exists():
        return
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    finally:
        conn.close()


def _assert_safe_archive_name(name: str) -> None:
    normalized = name.replace("\\", "/")
    path = PurePosixPath(normalized)
    if path.is_absolute() or normalized.startswith("../") or normalized == "..":
        raise CloudSyncError(f"unsafe snapshot path: {name}")
    if any(part in ("", ".", "..") for part in path.parts):
        raise CloudSyncError(f"unsafe snapshot path: {name}")
    if path.parts and ":" in path.parts[0]:
        raise CloudSyncError(f"unsafe snapshot path: {name}")


def _should_exclude(path: Path) -> bool:
    return any(path.name.endswith(suffix) for suffix in EXCLUDED_SUFFIXES)


def _as_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _env_get(environ: Mapping[str, str], key: str, default: str = "") -> str:
    return environ.get(key, default)


def _mapping_get(mapping: object, key: str, default: object = "") -> object:
    if not hasattr(mapping, "get"):
        return default
    try:
        return mapping.get(key, default)  # type: ignore[attr-defined]
    except Exception:
        return default


def _nested_get(mapping: object, keys: tuple[str, ...]) -> object:
    current = mapping
    for key in keys:
        current = _mapping_get(current, key, None)
        if current is None:
            return None
    return current
