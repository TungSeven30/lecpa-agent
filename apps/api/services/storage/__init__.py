"""Storage backend factory."""

from functools import lru_cache

from apps.api.config import settings

from .base import StorageBackend
from .filesystem import FilesystemBackend


@lru_cache
def get_storage() -> StorageBackend:
    """Get configured storage backend.

    Returns the appropriate storage backend based on the STORAGE_BACKEND
    environment variable. Uses LRU cache to ensure singleton pattern.

    Returns:
        Configured storage backend instance

    Raises:
        ValueError: If unknown storage backend is configured
        FileNotFoundError: If filesystem backend path doesn't exist
    """
    if settings.storage_backend == "filesystem":
        return FilesystemBackend(settings.nas_mount_path)
    else:
        raise ValueError(
            f"Unknown storage backend: {settings.storage_backend}. "
            f"Supported backends: filesystem"
        )


__all__ = ["StorageBackend", "FilesystemBackend", "get_storage"]
