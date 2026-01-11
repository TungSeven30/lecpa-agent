"""Filesystem storage backend for NAS."""

from pathlib import Path
from typing import BinaryIO

import aiofiles

from .base import StorageBackend


class FilesystemBackend(StorageBackend):
    """Direct filesystem storage (NAS volume mount).

    This backend provides direct access to files stored on the Synology NAS
    via a mounted volume. Files are organized by client code and tax year,
    matching the existing folder structure.

    Example structure:
        /volume1/LeCPA/ClientFiles/
            └── 1001_Lastname, FirstName/
                └── 2024/
                    └── document.pdf

    In container, this is mounted at /client-files.
    """

    def __init__(self, base_path: str):
        """Initialize with base path to client files.

        Args:
            base_path: Path to mounted NAS volume (e.g., /client-files)

        Raises:
            FileNotFoundError: If base_path doesn't exist
        """
        self.base_path = Path(base_path)
        if not self.base_path.exists():
            raise FileNotFoundError(
                f"Storage path not found: {base_path}. "
                f"Ensure NAS volume is mounted correctly."
            )

    async def upload(self, file: BinaryIO, key: str) -> str:
        """Save file to NAS.

        Creates parent directories if they don't exist.

        Args:
            file: File-like object to upload
            key: Storage key (e.g., "1001_Client/2024/uuid_file.pdf")

        Returns:
            Storage key

        Raises:
            IOError: If write fails
        """
        dest_path = self.base_path / key
        dest_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            async with aiofiles.open(dest_path, "wb") as f:
                content = file.read()
                await f.write(content)
        except Exception as e:
            raise IOError(f"Failed to write file {key}: {e}") from e

        return key

    async def download(self, key: str) -> bytes:
        """Read file from NAS.

        Args:
            key: Storage key

        Returns:
            File contents as bytes

        Raises:
            FileNotFoundError: If file doesn't exist
            IOError: If read fails
        """
        file_path = self.base_path / key
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {key}")

        try:
            async with aiofiles.open(file_path, "rb") as f:
                return await f.read()
        except Exception as e:
            raise IOError(f"Failed to read file {key}: {e}") from e

    async def delete(self, key: str) -> bool:
        """Delete file from NAS.

        Args:
            key: Storage key

        Returns:
            True if deleted, False if not found

        Raises:
            IOError: If deletion fails
        """
        file_path = self.base_path / key
        if not file_path.exists():
            return False

        try:
            file_path.unlink()
            return True
        except Exception as e:
            raise IOError(f"Failed to delete file {key}: {e}") from e

    def get_url(self, key: str) -> str:
        """Get local filesystem path.

        Args:
            key: Storage key

        Returns:
            Full filesystem path (for internal use only, not exposed to clients)
        """
        return str(self.base_path / key)
