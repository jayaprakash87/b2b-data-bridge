"""Tests for the sFTP / local transport layer."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from b2b_data_bridge.config import RetryConfig, SftpConfig
from b2b_data_bridge.sftp import LocalClient, SftpClient, SftpError


class TestLocalTransport:
    def test_upload_and_download(self, tmp_path: Path) -> None:
        base = str(tmp_path / "remote")
        transport = LocalClient(base)

        # Create a local file
        local_file = tmp_path / "upload.csv"
        local_file.write_text("header\nrow1\n")

        # Upload
        transport.upload(local_file, "/outbound")
        assert (Path(base) / "outbound" / "upload.csv").exists()

        # Download
        download_dir = tmp_path / "downloads"
        result = transport.download("/outbound/upload.csv", download_dir)
        assert result.read_text() == "header\nrow1\n"

    def test_list_files(self, tmp_path: Path) -> None:
        base = tmp_path / "remote"
        (base / "inbound").mkdir(parents=True)
        (base / "inbound" / "file1.csv").write_text("data")
        (base / "inbound" / "file2.csv").write_text("data")

        transport = LocalClient(str(base))
        files = transport.list_files("/inbound")
        assert len(files) == 2
        # Returned paths must be remote-style, not absolute filesystem paths
        for f in files:
            assert f.startswith("/inbound/")
            assert not f.startswith(str(base))

    def test_list_empty_dir(self, tmp_path: Path) -> None:
        base = tmp_path / "remote"
        transport = LocalClient(str(base))
        files = transport.list_files("/nonexistent")
        assert files == []

    def test_remove(self, tmp_path: Path) -> None:
        base = tmp_path / "remote"
        (base / "outbound").mkdir(parents=True)
        target = base / "outbound" / "old.csv"
        target.write_text("data")

        transport = LocalClient(str(base))
        transport.remove("/outbound/old.csv")
        assert not target.exists()

    def test_context_manager(self, tmp_path: Path) -> None:
        with LocalClient(str(tmp_path)) as client:
            local_file = tmp_path / "test.csv"
            local_file.write_text("data")
            client.upload(local_file, "/out")
            assert (tmp_path / "out" / "test.csv").exists()


def _make_sftp_client(max_retries: int = 0) -> SftpClient:
    cfg = SftpConfig(host="test.host", port=22, username="u", password="p")
    retry = RetryConfig(max_retries=max_retries, base_delay=0.0, backoff_factor=1.0)
    return SftpClient(cfg, retry)


class TestSftpClient:
    def test_connect_with_password(self) -> None:
        with patch("b2b_data_bridge.sftp.paramiko") as mock_paramiko:
            mock_ssh = MagicMock()
            mock_paramiko.SSHClient.return_value = mock_ssh
            mock_ssh.open_sftp.return_value = MagicMock()

            client = _make_sftp_client()
            client.connect()

            mock_ssh.set_missing_host_key_policy.assert_called_once()
            mock_ssh.load_system_host_keys.assert_called_once()
            call_kwargs = mock_ssh.connect.call_args[1]
            assert call_kwargs["hostname"] == "test.host"
            assert call_kwargs["password"] == "p"
            assert "key_filename" not in call_kwargs

    def test_connect_with_private_key(self) -> None:
        with patch("b2b_data_bridge.sftp.paramiko") as mock_paramiko:
            mock_ssh = MagicMock()
            mock_paramiko.SSHClient.return_value = mock_ssh
            mock_ssh.open_sftp.return_value = MagicMock()

            cfg = SftpConfig(host="h", port=22, username="u", private_key_path="/path/key")
            retry = RetryConfig(max_retries=0, base_delay=0.0, backoff_factor=1.0)
            client = SftpClient(cfg, retry)
            client.connect()

            call_kwargs = mock_ssh.connect.call_args[1]
            assert call_kwargs["key_filename"] == "/path/key"
            assert "password" not in call_kwargs

    def test_disconnect_clears_references(self) -> None:
        with patch("b2b_data_bridge.sftp.paramiko") as mock_paramiko:
            mock_ssh = MagicMock()
            mock_paramiko.SSHClient.return_value = mock_ssh
            mock_ssh.open_sftp.return_value = MagicMock()

            client = _make_sftp_client()
            client.connect()
            client.disconnect()

            assert client._ssh is None
            assert client._sftp is None

    def test_context_manager_connects_and_disconnects(self) -> None:
        with patch("b2b_data_bridge.sftp.paramiko") as mock_paramiko:
            mock_ssh = MagicMock()
            mock_paramiko.SSHClient.return_value = mock_ssh
            mock_ssh.open_sftp.return_value = MagicMock()

            client = _make_sftp_client()
            with client:
                assert client._ssh is mock_ssh
            assert client._ssh is None

    def test_upload(self, tmp_path: Path) -> None:
        client = _make_sftp_client()
        mock_sftp = MagicMock()
        client._sftp = mock_sftp

        local_file = tmp_path / "data.csv"
        local_file.write_text("col\nval\n")
        result = client.upload(local_file, "/outbound")

        assert result == "/outbound/data.csv"
        mock_sftp.put.assert_called_once_with(str(local_file), "/outbound/data.csv")

    def test_download_success(self, tmp_path: Path) -> None:
        client = _make_sftp_client()
        mock_sftp = MagicMock()
        client._sftp = mock_sftp

        local_dir = tmp_path / "downloads"
        result = client.download("/outbound/data.csv", local_dir)

        assert result == local_dir / "data.csv"
        mock_sftp.get.assert_called_once()

    def test_download_rejects_dotfile(self, tmp_path: Path) -> None:
        client = _make_sftp_client()
        client._sftp = MagicMock()
        with pytest.raises(SftpError, match="Unsafe remote filename"):
            client.download("/outbound/.hidden", tmp_path)

    def test_download_rejects_empty_filename(self, tmp_path: Path) -> None:
        client = _make_sftp_client()
        client._sftp = MagicMock()
        with pytest.raises(SftpError, match="Unsafe remote filename"):
            client.download("/outbound/", tmp_path)

    def test_list_files_excludes_dotfiles(self) -> None:
        client = _make_sftp_client()
        mock_sftp = MagicMock()
        mock_sftp.listdir.return_value = ["file1.csv", ".hidden", "file2.csv"]
        client._sftp = mock_sftp

        result = client.list_files("/outbound")

        assert len(result) == 2
        assert "/outbound/file1.csv" in result
        assert "/outbound/.hidden" not in result

    def test_remove(self) -> None:
        client = _make_sftp_client()
        mock_sftp = MagicMock()
        client._sftp = mock_sftp

        client.remove("/outbound/old.csv")
        mock_sftp.remove.assert_called_once_with("/outbound/old.csv")

    def test_retry_exhausted_raises_sftp_error(self) -> None:
        client = _make_sftp_client(max_retries=1)
        mock_sftp = MagicMock()
        mock_sftp.remove.side_effect = OSError("connection lost")
        client._sftp = mock_sftp

        with pytest.raises(SftpError, match="Failed after 2 attempts"):
            client.remove("/outbound/file.csv")
        assert mock_sftp.remove.call_count == 2

    def test_retry_succeeds_on_second_attempt(self) -> None:
        client = _make_sftp_client(max_retries=1)
        mock_sftp = MagicMock()
        mock_sftp.remove.side_effect = [OSError("first"), None]
        client._sftp = mock_sftp

        client.remove("/outbound/file.csv")  # should not raise
        assert mock_sftp.remove.call_count == 2

