from pathlib import Path
from typing import BinaryIO
from app.core.interfaces import StorageInterface
from app.config import settings
import structlog

logger = structlog.get_logger()


class LocalStorage(StorageInterface):
    def __init__(self, base_path: str | None = None):
        self.base_path = Path(base_path or settings.storage_local_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

    def save(self, path: str, data: bytes | BinaryIO) -> str:
        full_path = self.base_path / path
        full_path.parent.mkdir(parents=True, exist_ok=True)

        if isinstance(data, bytes):
            full_path.write_bytes(data)
        else:
            full_path.write_bytes(data.read())

        logger.info("file_saved", path=str(full_path))
        return path

    def load(self, path: str) -> bytes:
        full_path = self.base_path / path
        if not full_path.exists():
            raise FileNotFoundError(f"File not found: {path}")
        return full_path.read_bytes()

    def delete(self, path: str) -> None:
        full_path = self.base_path / path
        if full_path.exists():
            full_path.unlink()
            logger.info("file_deleted", path=str(full_path))

    def exists(self, path: str) -> bool:
        return (self.base_path / path).exists()

    def get_url(self, path: str) -> str:
        return str((self.base_path / path).resolve())

    def list_files(self, prefix: str = "") -> list[str]:
        target = self.base_path / prefix
        if not target.exists():
            return []
        return [
            str(p.relative_to(self.base_path))
            for p in target.rglob("*")
            if p.is_file()
        ]
