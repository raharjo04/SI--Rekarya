import secrets
import threading
import time
from dataclasses import dataclass


@dataclass(frozen=True)
class CachedDownload:
    content: bytes
    expires_at: float


class DownloadStore:
    def __init__(self, ttl_seconds: int = 15 * 60) -> None:
        self._ttl_seconds = ttl_seconds
        self._downloads: dict[str, CachedDownload] = {}
        self._lock = threading.Lock()

    def _remove_expired(self, now: float) -> None:
        expired = [
            token
            for token, download in self._downloads.items()
            if download.expires_at <= now
        ]
        for token in expired:
            del self._downloads[token]

    def create(self, content: bytes) -> str:
        now = time.monotonic()
        token = secrets.token_urlsafe(32)
        with self._lock:
            self._remove_expired(now)
            self._downloads[token] = CachedDownload(
                content=content,
                expires_at=now + self._ttl_seconds,
            )
        return token

    def get(self, token: str) -> bytes | None:
        now = time.monotonic()
        with self._lock:
            self._remove_expired(now)
            download = self._downloads.get(token)
            if download is None:
                return None
            return download.content


download_store = DownloadStore()
