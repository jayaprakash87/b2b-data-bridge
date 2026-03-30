"""Shared test fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest

from b2b_data_bridge.config import (
    FileConfig,
    NamingConfig,
    PathsConfig,
    RetryConfig,
    Settings,
    SftpConfig,
)


@pytest.fixture
def tmp_data_dir(tmp_path: Path) -> Path:
    for sub in ("outbound", "inbound", "archive", "failed", "logs"):
        (tmp_path / sub).mkdir()
    return tmp_path


@pytest.fixture
def settings(tmp_data_dir: Path) -> Settings:
    return Settings(
        environment="test",
        sftp=SftpConfig(host="localhost", port=22, username="test"),
        paths=PathsConfig(
            outbound_dir=str(tmp_data_dir / "outbound"),
            inbound_dir=str(tmp_data_dir / "inbound"),
            archive_dir=str(tmp_data_dir / "archive"),
            failed_dir=str(tmp_data_dir / "failed"),
            log_dir=str(tmp_data_dir / "logs"),
        ),
        files=FileConfig(default_format="csv", encoding="utf-8", csv_delimiter=";"),
        naming=NamingConfig(),
        retry=RetryConfig(max_retries=2, base_delay=0, backoff_factor=1.0),
        log_level="DEBUG",
    )
