"""Storage adapter: LocalStorage now, S3-compatible interface stub for prod.

Same interface either way — swap by env STORAGE_BACKEND=local|s3.
"""
import os
import shutil
from pathlib import Path

from app.core.config import settings


class LocalStorage:
    def __init__(self, base_dir: str | Path | None = None):
        self.base = Path(base_dir or settings.storage_dir)
        for sub in ("videos", "clips", "covers"):
            (self.base / sub).mkdir(parents=True, exist_ok=True)

    def save(self, src_path: str, subdir: str, filename: str) -> str:
        dest = self.base / subdir / filename
        dest.parent.mkdir(parents=True, exist_ok=True)
        if os.path.abspath(src_path) != os.path.abspath(dest):
            shutil.copyfile(src_path, dest)
        return str(dest)

    def path(self, subdir: str, filename: str) -> str:
        return str(self.base / subdir / filename)

    def exists(self, path: str) -> bool:
        return os.path.exists(path)

    def delete(self, path: str) -> None:
        try:
            os.remove(path)
        except OSError:
            pass


class S3Storage:
    """S3-compatible stub — same interface as LocalStorage.

    Production implementation would use boto3 with STORAGE_BUCKET /
    AWS credentials from env. Intentionally raises NotImplementedError
    rather than silently pretending to upload.
    """

    def __init__(self, bucket: str | None = None):
        self.bucket = bucket or os.getenv("STORAGE_BUCKET", "")

    def save(self, src_path: str, subdir: str, filename: str) -> str:
        raise NotImplementedError("S3 storage not configured — set STORAGE_BACKEND=local for dev")

    def path(self, subdir: str, filename: str) -> str:
        return f"s3://{self.bucket}/{subdir}/{filename}"

    def exists(self, path: str) -> bool:
        raise NotImplementedError("S3 storage not configured")

    def delete(self, path: str) -> None:
        raise NotImplementedError("S3 storage not configured")


def get_storage():
    if os.getenv("STORAGE_BACKEND", "local").lower() == "s3":
        return S3Storage()
    return LocalStorage()
