"""sFTP client — upload / download files over SSH.

One concrete class, no abstract interfaces. Includes retry and an
optional local‑filesystem fallback for development without a real server.
"""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import List, Optional

import paramiko

from b2b_data_bridge.config import SftpConfig, RetryConfig

logger = logging.getLogger(__name__)


class SftpError(Exception):
    """Any sFTP operation failure after retries are exhausted."""


class SftpClient:
    """Connect → upload / download / list → disconnect."""

    def __init__(self, cfg: SftpConfig, retry: RetryConfig) -> None:
        self._cfg = cfg
        self._retry = retry
        self._ssh: Optional[paramiko.SSHClient] = None
        self._sftp: Optional[paramiko.SFTPClient] = None

    # -- connection lifecycle -----------------------------------------------

    def connect(self) -> None:
        self._ssh = paramiko.SSHClient()
        self._ssh.set_missing_host_key_policy(paramiko.RejectPolicy())
        self._ssh.load_system_host_keys()
        connect_kwargs: dict = {
            "hostname": self._cfg.host,
            "port": self._cfg.port,
            "username": self._cfg.username,
            "timeout": self._cfg.timeout,
        }
        if self._cfg.private_key_path:
            connect_kwargs["key_filename"] = self._cfg.private_key_path
        elif self._cfg.password:
            connect_kwargs["password"] = self._cfg.password
        self._ssh.connect(**connect_kwargs)
        self._sftp = self._ssh.open_sftp()
        logger.info("sFTP connected to %s:%s", self._cfg.host, self._cfg.port)

    def disconnect(self) -> None:
        if self._sftp:
            self._sftp.close()
        if self._ssh:
            self._ssh.close()
        self._sftp = None
        self._ssh = None
        logger.info("sFTP disconnected")

    # -- context manager ----------------------------------------------------

    def __enter__(self) -> "SftpClient":
        self.connect()
        return self

    def __exit__(self, *exc) -> None:
        self.disconnect()

    # -- operations (with automatic retry) ----------------------------------

    def upload(self, local: Path, remote_dir: str) -> str:
        remote_path = f"{remote_dir}/{local.name}"
        self._with_retry(lambda: self._sftp.put(str(local), remote_path))  # type: ignore[union-attr]
        logger.info("Uploaded %s → %s", local.name, remote_path)
        return remote_path

    def download(self, remote_path: str, local_dir: Path) -> Path:
        local_dir.mkdir(parents=True, exist_ok=True)
        filename = Path(remote_path.rsplit("/", 1)[-1]).name  # strip any path components
        if not filename or filename.startswith("."):
            raise SftpError(f"Unsafe remote filename: {remote_path}")
        local_path = local_dir / filename
        if not local_path.resolve().is_relative_to(local_dir.resolve()):
            raise SftpError(f"Path traversal detected: {remote_path}")
        self._with_retry(lambda: self._sftp.get(remote_path, str(local_path)))  # type: ignore[union-attr]
        logger.info("Downloaded %s → %s", remote_path, local_path)
        return local_path

    def list_files(self, remote_dir: str) -> List[str]:
        files: List[str] = []
        entries = self._with_retry(lambda: self._sftp.listdir(remote_dir))  # type: ignore[union-attr]
        for name in entries:
            if name.startswith("."):
                continue
            files.append(f"{remote_dir}/{name}")
        return files

    def remove(self, remote_path: str) -> None:
        self._with_retry(lambda: self._sftp.remove(remote_path))  # type: ignore[union-attr]
        logger.debug("Removed remote file %s", remote_path)

    # -- retry helper -------------------------------------------------------

    def _with_retry(self, fn):
        for attempt in range(self._retry.max_retries + 1):
            try:
                return fn()
            except Exception as exc:
                if attempt >= self._retry.max_retries:
                    raise SftpError(f"Failed after {attempt + 1} attempts: {exc}") from exc
                wait = min(
                    self._retry.base_delay * (self._retry.backoff_factor ** attempt),
                    300.0,  # cap at 5 minutes
                )
                logger.warning("sFTP retry %d/%d in %.1fs — %s",
                               attempt + 1, self._retry.max_retries, wait, exc)
                time.sleep(wait)


# ---------------------------------------------------------------------------
# Local filesystem transport (for dev / testing without a real sFTP server)
# ---------------------------------------------------------------------------

class LocalClient:
    """Drop-in replacement that copies files on the local filesystem."""

    def __init__(self, base_dir: str = "/tmp/sftp_local") -> None:
        self._base = Path(base_dir)
        self._base.mkdir(parents=True, exist_ok=True)

    def __enter__(self) -> "LocalClient":
        return self

    def __exit__(self, *exc) -> None:
        pass

    def connect(self) -> None:
        pass

    def disconnect(self) -> None:
        pass

    def upload(self, local: Path, remote_dir: str) -> str:
        import shutil
        dest_dir = self._base / remote_dir.lstrip("/")
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / local.name
        shutil.copy2(str(local), str(dest))
        logger.info("[local] Copied %s → %s", local.name, dest)
        return str(dest)

    def download(self, remote_path: str, local_dir: Path) -> Path:
        import shutil
        local_dir.mkdir(parents=True, exist_ok=True)
        src = (self._base / remote_path.lstrip("/")).resolve()
        if not src.is_relative_to(self._base.resolve()):
            raise OSError(f"Path traversal detected: {remote_path}")
        dest = local_dir / src.name
        shutil.copy2(str(src), str(dest))
        return dest

    def list_files(self, remote_dir: str) -> List[str]:
        d = self._base / remote_dir.lstrip("/")
        if not d.exists():
            return []
        return [
            f"{remote_dir}/{p.name}"
            for p in d.iterdir()
            if p.is_file() and not p.name.startswith(".")
        ]

    def remove(self, remote_path: str) -> None:
        p = self._base / remote_path.lstrip("/")
        p.unlink(missing_ok=True)
