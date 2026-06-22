from __future__ import annotations

import base64
from pathlib import Path
import sqlite3
import zipfile

import pytest

from services.cloud_sync import (
    CloudSyncConfig,
    CloudSyncError,
    GitHubSnapshotSync,
    build_snapshot_archive,
    load_cloud_sync_config,
    restore_snapshot_archive,
)


class FakeResponse:
    def __init__(self, status_code: int, payload: dict[str, object] | None = None, content: bytes = b""):
        self.status_code = status_code
        self._payload = payload or {}
        self.content = content
        self.text = str(self._payload)

    def json(self) -> dict[str, object]:
        return self._payload


def test_load_cloud_sync_config_reads_streamlit_secrets_shape():
    config = load_cloud_sync_config(
        {
            "persistence": {
                "enabled": True,
                "provider": "github",
                "repo": "1shuiyihui/fashuocangku1",
                "branch": "cloud-data",
                "source_branch": "codex/fashuo-socratic-local-tool",
                "snapshot_path": "fashuo-cloud-snapshot.zip",
                "github_token": "token",
            }
        }
    )

    assert config.enabled is True
    assert config.provider == "github"
    assert config.repo == "1shuiyihui/fashuocangku1"
    assert config.branch == "cloud-data"
    assert config.source_branch == "codex/fashuo-socratic-local-tool"
    assert config.snapshot_path == "fashuo-cloud-snapshot.zip"
    assert config.github_token == "token"


def test_load_cloud_sync_config_uses_env_fallbacks():
    config = load_cloud_sync_config(
        {},
        {
            "PERSISTENCE_ENABLED": "true",
            "PERSISTENCE_PROVIDER": "github",
            "GITHUB_REPOSITORY": "owner/repo",
            "PERSISTENCE_BRANCH": "cloud-data",
            "PERSISTENCE_SOURCE_BRANCH": "main",
            "PERSISTENCE_SNAPSHOT_PATH": "snapshots/fashuo.zip",
            "GITHUB_SYNC_TOKEN": "env-token",
        },
    )

    assert config.enabled is True
    assert config.repo == "owner/repo"
    assert config.branch == "cloud-data"
    assert config.source_branch == "main"
    assert config.snapshot_path == "snapshots/fashuo.zip"
    assert config.github_token == "env-token"


def test_build_and_restore_snapshot_archive_round_trips_data(tmp_path: Path):
    source = tmp_path / "source"
    (source / "uploads").mkdir(parents=True)
    (source / "documents").mkdir()
    (source / "fashuo.db").write_bytes(b"sqlite-db")
    (source / "fashuo.db-wal").write_bytes(b"ignore-wal")
    (source / "uploads" / "question.png").write_bytes(b"image")
    (source / "documents" / "note.txt").write_text("共同犯罪", encoding="utf-8")

    archive = build_snapshot_archive(source, app_version="test")
    target = tmp_path / "target"

    restore_snapshot_archive(archive, target)

    assert (target / "fashuo.db").read_bytes() == b"sqlite-db"
    assert (target / "uploads" / "question.png").read_bytes() == b"image"
    assert (target / "documents" / "note.txt").read_text(encoding="utf-8") == "共同犯罪"
    assert not (target / "fashuo.db-wal").exists()


def test_restore_rejects_zip_path_traversal(tmp_path: Path):
    archive_path = tmp_path / "bad.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("../outside.txt", "bad")

    with pytest.raises(CloudSyncError, match="unsafe"):
        restore_snapshot_archive(archive_path.read_bytes(), tmp_path / "target")

    assert not (tmp_path / "outside.txt").exists()


def test_github_upload_creates_data_branch_from_source_and_puts_snapshot(tmp_path: Path):
    data_root = tmp_path / "data"
    data_root.mkdir()
    conn = sqlite3.connect(data_root / "fashuo.db")
    conn.execute("CREATE TABLE sample (id INTEGER PRIMARY KEY)")
    conn.commit()
    conn.close()

    calls: list[tuple[str, str, dict[str, object] | None]] = []

    def fake_request(method: str, url: str, **kwargs: object) -> FakeResponse:
        payload = kwargs.get("json") if isinstance(kwargs.get("json"), dict) else None
        calls.append((method, url, payload))
        if method == "GET" and url.endswith("/git/ref/heads/cloud-data"):
            return FakeResponse(404, {"message": "Not Found"})
        if method == "GET" and url.endswith("/git/ref/heads/main"):
            return FakeResponse(200, {"object": {"sha": "source-sha"}})
        if method == "POST" and url.endswith("/git/refs"):
            return FakeResponse(201, {"ref": "refs/heads/cloud-data"})
        if method == "GET" and "/contents/fashuo-cloud-snapshot.zip" in url:
            return FakeResponse(404, {"message": "Not Found"})
        if method == "PUT" and url.endswith("/contents/fashuo-cloud-snapshot.zip"):
            return FakeResponse(201, {"content": {"sha": "new-sha"}})
        raise AssertionError(f"unexpected request: {method} {url}")

    sync = GitHubSnapshotSync(
        CloudSyncConfig(
            enabled=True,
            repo="owner/repo",
            branch="cloud-data",
            source_branch="main",
            snapshot_path="fashuo-cloud-snapshot.zip",
            github_token="token",
        ),
        request_func=fake_request,
    )

    result = sync.upload(data_root, reason="test")

    assert result.status == "uploaded"
    assert ("POST", "https://api.github.com/repos/owner/repo/git/refs", {"ref": "refs/heads/cloud-data", "sha": "source-sha"}) in calls
    put_payload = next(
        payload
        for method, url, payload in calls
        if method == "PUT" and url.endswith("/contents/fashuo-cloud-snapshot.zip")
    )
    assert put_payload is not None
    assert put_payload["branch"] == "cloud-data"
    assert base64.b64decode(str(put_payload["content"]))
