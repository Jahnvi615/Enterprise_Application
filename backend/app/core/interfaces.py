from abc import ABC, abstractmethod
from typing import BinaryIO


class StorageInterface(ABC):
    """Abstract storage layer. Swap implementations without touching business logic."""

    @abstractmethod
    def save(self, path: str, data: bytes | BinaryIO) -> str:
        ...

    @abstractmethod
    def load(self, path: str) -> bytes:
        ...

    @abstractmethod
    def delete(self, path: str) -> None:
        ...

    @abstractmethod
    def exists(self, path: str) -> bool:
        ...

    @abstractmethod
    def get_url(self, path: str) -> str:
        ...

    @abstractmethod
    def list_files(self, prefix: str = "") -> list[str]:
        ...


class JobRunnerInterface(ABC):
    """Abstract job runner. Sync for dev, Celery for production."""

    @abstractmethod
    def submit(self, task_name: str, payload: dict) -> str:
        ...

    @abstractmethod
    def get_status(self, job_id: str) -> dict:
        ...

    @abstractmethod
    def cancel(self, job_id: str) -> bool:
        ...
