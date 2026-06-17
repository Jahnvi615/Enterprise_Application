from functools import lru_cache
from app.config import settings, StorageProvider, JobRunner
from app.core.interfaces import StorageInterface, JobRunnerInterface
from app.infrastructure.local_storage import LocalStorage
from app.infrastructure.sync_job_runner import SyncJobRunner


@lru_cache()
def get_storage() -> StorageInterface:
    if settings.storage_provider == StorageProvider.LOCAL:
        return LocalStorage()
    raise NotImplementedError(
        f"Storage provider '{settings.storage_provider}' not yet implemented"
    )


@lru_cache()
def get_job_runner() -> JobRunnerInterface:
    if settings.job_runner == JobRunner.SYNC:
        return SyncJobRunner()
    raise NotImplementedError(
        f"Job runner '{settings.job_runner}' not yet implemented"
    )
