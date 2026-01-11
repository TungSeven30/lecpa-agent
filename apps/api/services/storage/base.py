"""Storage backend interface."""

from abc import ABC, abstractmethod
from typing import BinaryIO


class StorageBackend(ABC):
    """Abstract storage backend interface.

    This interface defines the contract for all storage backends,
    whether filesystem-based (NAS) or cloud-based (S3/MinIO).
    """

    @abstractmethod
    async def upload(self, file: BinaryIO, key: str) -> str:
        """Upload file and return storage path.

        Args:
            file: File-like object to upload
            key: Storage key (e.g., "1001_Client/2024/uuid_file.pdf")

        Returns:
            Storage key where file was saved

        Raises:
            IOError: If upload fails
        """

    @abstractmethod
    async def download(self, key: str) -> bytes:
        """Download file contents.

        Args:
            key: Storage key

        Returns:
            File contents as bytes

        Raises:
            FileNotFoundError: If file doesn't exist
            IOError: If download fails
        """

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete file.

        Args:
            key: Storage key

        Returns:
            True if deleted, False if not found

        Raises:
            IOError: If deletion fails
        """

    @abstractmethod
    def get_url(self, key: str) -> str:
        """Get access URL/path for file.

        Args:
            key: Storage key

        Returns:
            URL or filesystem path to access the file
        """
