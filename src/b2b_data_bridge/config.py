"""Configuration — loads settings from YAML with optional .env overrides."""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from pathlib import Path

import yaml
from dotenv import load_dotenv


class ConfigError(Exception):
    """Raised when configuration cannot be loaded or is invalid."""


def _detect_project_root() -> Path:
    """Find the project root — works both as Python package and as frozen binary."""
    if getattr(sys, "frozen", False):
        # Running as PyInstaller bundle: config lives next to the executable
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[2]


_PROJECT_ROOT = _detect_project_root()


@dataclass(frozen=True)
class SftpConfig:
    host: str = "localhost"
    port: int = 22
    username: str = ""
    password: str = ""
    private_key_path: str = ""
    remote_outbound_dir: str = "/outbound"
    remote_inbound_dir: str = "/inbound"
    timeout: int = 30

    def __repr__(self) -> str:
        return (
            f"SftpConfig(host={self.host!r}, port={self.port}, "
            f"username={self.username!r}, password='***', "
            f"remote_outbound_dir={self.remote_outbound_dir!r}, "
            f"remote_inbound_dir={self.remote_inbound_dir!r})"
        )


@dataclass(frozen=True)
class PathsConfig:
    outbound_dir: str = "./data/outbound"
    inbound_dir: str = "./data/inbound"
    archive_dir: str = "./data/archive"
    failed_dir: str = "./data/failed"
    log_dir: str = "./logs"

    def ensure_dirs(self) -> None:
        for d in (self.outbound_dir, self.inbound_dir, self.archive_dir, self.failed_dir, self.log_dir):
            Path(d).mkdir(parents=True, exist_ok=True)


@dataclass(frozen=True)
class FileConfig:
    default_format: str = "csv"    # csv | xlsx
    encoding: str = "utf-8"
    csv_delimiter: str = ";"
    csv_quotechar: str = '"'


@dataclass(frozen=True)
class NamingConfig:
    product_prefix: str = "PRODUCTS"
    pricing_prefix: str = "PRICING"
    stock_prefix: str = "STOCK"
    order_prefix: str = "ORDERS"
    timestamp_format: str = "%Y%m%d_%H%M%S"


_MAX_RETRY_CEILING = 10


@dataclass(frozen=True)
class RetryConfig:
    max_retries: int = 3
    base_delay: float = 2.0
    backoff_factor: float = 2.0

    def __post_init__(self) -> None:
        if self.max_retries > _MAX_RETRY_CEILING:
            object.__setattr__(self, "max_retries", _MAX_RETRY_CEILING)


@dataclass(frozen=True)
class Settings:
    environment: str = "development"
    sftp: SftpConfig = field(default_factory=SftpConfig)
    paths: PathsConfig = field(default_factory=PathsConfig)
    files: FileConfig = field(default_factory=FileConfig)
    naming: NamingConfig = field(default_factory=NamingConfig)
    retry: RetryConfig = field(default_factory=RetryConfig)
    log_level: str = "INFO"


def _apply_env_overrides(raw: dict) -> dict:
    """Override YAML values with environment variables where set."""
    mapping = {
        "SFTP_HOST":     ("sftp", "host"),
        "SFTP_PORT":     ("sftp", "port"),
        "SFTP_USERNAME": ("sftp", "username"),
        "SFTP_PASSWORD": ("sftp", "password"),
        "SFTP_PRIVATE_KEY_PATH": ("sftp", "private_key_path"),
        "LOG_LEVEL":     ("log_level",),
        "FILE_FORMAT":   ("files", "default_format"),
    }
    for env_key, path in mapping.items():
        value = os.environ.get(env_key)
        if value is not None:
            node = raw
            for part in path[:-1]:
                node = node.setdefault(part, {})
            node[path[-1]] = int(value) if path[-1] == "port" else value
    return raw


def load_settings(config_path: str | Path | None = None, env_file: str | Path | None = None) -> Settings:
    """Load settings from YAML config, with .env overrides."""
    env_path = Path(env_file) if env_file else _PROJECT_ROOT / ".env"
    if env_path.exists():
        load_dotenv(env_path)

    yaml_path = Path(config_path) if config_path else _PROJECT_ROOT / "config" / "settings.yaml"
    raw: dict = {}
    if yaml_path.exists():
        try:
            with open(yaml_path, encoding="utf-8") as f:
                raw = yaml.safe_load(f) or {}
        except yaml.YAMLError as e:
            raise ConfigError(f"Invalid YAML in {yaml_path}: {e}") from e

    if not isinstance(raw, dict):
        raise ConfigError(f"Expected dict in {yaml_path}, got {type(raw).__name__}")

    raw = _apply_env_overrides(raw)

    try:
        return Settings(
            environment=raw.get("environment", "development"),
            sftp=SftpConfig(**raw.get("sftp", {})),
            paths=PathsConfig(**raw.get("paths", {})),
            files=FileConfig(**raw.get("files", {})),
            naming=NamingConfig(**raw.get("naming", {})),
            retry=RetryConfig(**raw.get("retry", {})),
            log_level=raw.get("log_level", "INFO"),
        )
    except TypeError as e:
        raise ConfigError(f"Bad config value: {e}") from e
