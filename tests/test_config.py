"""Tests for configuration loading and env-var overrides."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from b2b_data_bridge.config import (
    ConfigError,
    PathsConfig,
    RetryConfig,
    Settings,
    SftpConfig,
    load_settings,
)

_NO_ENV = Path("/dev/null")  # empty file — no dotenv vars loaded


class TestSftpConfigRepr:
    def test_repr_hides_password(self) -> None:
        cfg = SftpConfig(host="sftp.example.com", username="user", password="s3cret")
        r = repr(cfg)
        assert "s3cret" not in r
        assert "***" in r
        assert "sftp.example.com" in r


class TestPathsConfigEnsureDirs:
    def test_creates_all_directories(self, tmp_path: Path) -> None:
        cfg = PathsConfig(
            outbound_dir=str(tmp_path / "out"),
            inbound_dir=str(tmp_path / "in"),
            archive_dir=str(tmp_path / "arc"),
            failed_dir=str(tmp_path / "fail"),
            log_dir=str(tmp_path / "logs"),
        )
        cfg.ensure_dirs()
        for sub in ("out", "in", "arc", "fail", "logs"):
            assert (tmp_path / sub).is_dir()


class TestRetryConfig:
    def test_clamps_at_ceiling(self) -> None:
        rc = RetryConfig(max_retries=999)
        assert rc.max_retries == 10  # _MAX_RETRY_CEILING


class TestEnvOverrides:
    def _clean(self, monkeypatch: pytest.MonkeyPatch) -> None:
        for key in ["SFTP_HOST", "SFTP_USERNAME", "SFTP_PASSWORD", "SFTP_PORT",
                    "SFTP_PRIVATE_KEY_PATH", "LOG_LEVEL", "FILE_FORMAT"]:
            monkeypatch.delenv(key, raising=False)

    def test_sftp_host_and_username(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self._clean(monkeypatch)
        monkeypatch.setenv("SFTP_HOST", "override.host.com")
        monkeypatch.setenv("SFTP_USERNAME", "override_user")
        settings = load_settings(config_path=None, env_file=_NO_ENV)
        assert settings.sftp.host == "override.host.com"
        assert settings.sftp.username == "override_user"

    def test_sftp_port_cast_to_int(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self._clean(monkeypatch)
        monkeypatch.setenv("SFTP_PORT", "2222")
        settings = load_settings(config_path=None, env_file=_NO_ENV)
        assert settings.sftp.port == 2222
        assert isinstance(settings.sftp.port, int)

    def test_log_level_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self._clean(monkeypatch)
        monkeypatch.setenv("LOG_LEVEL", "DEBUG")
        settings = load_settings(config_path=None, env_file=_NO_ENV)
        assert settings.log_level == "DEBUG"

    def test_file_format_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self._clean(monkeypatch)
        monkeypatch.setenv("FILE_FORMAT", "xlsx")
        settings = load_settings(config_path=None, env_file=_NO_ENV)
        assert settings.files.default_format == "xlsx"

    def test_sftp_password_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self._clean(monkeypatch)
        monkeypatch.setenv("SFTP_PASSWORD", "newpass")
        settings = load_settings(config_path=None, env_file=_NO_ENV)
        assert settings.sftp.password == "newpass"


class TestLoadSettings:
    def test_loads_from_yaml(self, tmp_path: Path) -> None:
        cfg_file = tmp_path / "settings.yaml"
        cfg_file.write_text(
            "environment: staging\nsftp:\n  host: yaml.host\n  port: 22\n  username: u\n",
            encoding="utf-8",
        )
        settings = load_settings(config_path=cfg_file, env_file=_NO_ENV)
        assert settings.environment == "staging"
        assert settings.sftp.host == "yaml.host"

    def test_dotenv_file_loaded_when_exists(self, tmp_path: Path) -> None:
        env_file = tmp_path / ".env"
        env_file.write_text("", encoding="utf-8")  # empty — just check it's invoked
        with patch("b2b_data_bridge.config.load_dotenv") as mock_dotenv:
            load_settings(config_path=None, env_file=env_file)
        mock_dotenv.assert_called_once_with(env_file)

    def test_missing_yaml_returns_defaults(self, tmp_path: Path) -> None:
        nonexistent = tmp_path / "nope.yaml"
        settings = load_settings(config_path=nonexistent, env_file=_NO_ENV)
        assert isinstance(settings, Settings)

    def test_invalid_yaml_raises_config_error(self, tmp_path: Path) -> None:
        cfg_file = tmp_path / "bad.yaml"
        cfg_file.write_text("key: [unclosed", encoding="utf-8")
        with pytest.raises(ConfigError, match="Invalid YAML"):
            load_settings(config_path=cfg_file, env_file=_NO_ENV)

    def test_non_dict_yaml_raises_config_error(self, tmp_path: Path) -> None:
        cfg_file = tmp_path / "list.yaml"
        cfg_file.write_text("- item1\n- item2\n", encoding="utf-8")
        with pytest.raises(ConfigError, match="Expected dict"):
            load_settings(config_path=cfg_file, env_file=_NO_ENV)

    def test_unknown_sftp_key_raises_config_error(self, tmp_path: Path) -> None:
        cfg_file = tmp_path / "settings.yaml"
        cfg_file.write_text("sftp:\n  not_a_real_key: value\n", encoding="utf-8")
        with pytest.raises(ConfigError, match="Bad config value"):
            load_settings(config_path=cfg_file, env_file=_NO_ENV)
