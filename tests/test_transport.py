"""Tests for the sFTP / local transport layer."""

from __future__ import annotations

from pathlib import Path


from b2b_data_bridge.sftp import LocalClient


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
