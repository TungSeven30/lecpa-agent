"""Full scanner for initial backfill of NAS files.

Performs a complete scan of the NAS filesystem to index all existing
documents. Used for initial setup and periodic re-syncs.
"""

import asyncio
import hashlib
from datetime import datetime
from pathlib import Path

import structlog
from tqdm import tqdm

from nas_sync.api_client import APIClient
from nas_sync.lnk_parser import find_relationship_from_lnk
from nas_sync.models import Config
from nas_sync.parser import FolderParser

logger = structlog.get_logger()


class FullScanner:
    """Scan the NAS filesystem for all documents.

    Walks the directory tree and sends notifications for each file
    to the API server. Supports filtering by client and year.
    """

    def __init__(self, config: Config):
        """Initialize the scanner.

        Args:
            config: Full configuration
        """
        self.config = config
        self.parser = FolderParser(config)
        self.api_client = APIClient(config)

        # Statistics
        self.files_scanned = 0
        self.files_queued = 0
        self.files_skipped = 0
        self.files_failed = 0
        self.relationships_found = 0

    async def scan(
        self,
        client_filter: list[str] | None = None,
        year_filter: list[int] | None = None,
        dry_run: bool = False,
    ) -> dict:
        """Perform a full scan of the NAS.

        Args:
            client_filter: Only process these client codes (e.g., ["1001", "1002"])
            year_filter: Only process these years (e.g., [2024, 2023])
            dry_run: If True, don't actually send notifications

        Returns:
            Dictionary with scan statistics
        """
        nas_root = Path(self.config.nas.root_path)
        if not nas_root.exists():
            raise FileNotFoundError(f"NAS root not found: {nas_root}")

        logger.info(
            "Starting full scan",
            root=str(nas_root),
            client_filter=client_filter,
            year_filter=year_filter,
            dry_run=dry_run,
        )

        # Reset statistics
        self.files_scanned = 0
        self.files_queued = 0
        self.files_skipped = 0
        self.files_failed = 0
        self.relationships_found = 0

        # Collect all files first for progress tracking
        all_files = self._collect_files(nas_root, client_filter, year_filter)

        logger.info("Files to process", count=len(all_files))

        # Process files with progress bar
        for file_path in tqdm(all_files, desc="Scanning NAS", unit="files"):
            await self._process_file(file_path, dry_run)

        # Close API client
        await self.api_client.close()

        results = {
            "status": "completed",
            "files_scanned": self.files_scanned,
            "files_queued": self.files_queued,
            "files_skipped": self.files_skipped,
            "files_failed": self.files_failed,
            "relationships_found": self.relationships_found,
        }

        logger.info("Scan completed", **results)
        return results

    def _collect_files(
        self,
        nas_root: Path,
        client_filter: list[str] | None,
        year_filter: list[int] | None,
    ) -> list[Path]:
        """Collect all files to process.

        Args:
            nas_root: Root path to scan
            client_filter: Client codes to include
            year_filter: Years to include

        Returns:
            List of file paths to process
        """
        files: list[Path] = []

        for client_dir in nas_root.iterdir():
            if not client_dir.is_dir():
                continue

            # Parse client folder name
            parsed = self.parser.parse(client_dir / "dummy.txt")
            if not parsed.is_valid or not parsed.client_code:
                continue

            # Apply client filter
            if client_filter and parsed.client_code not in client_filter:
                continue

            # Walk the client directory
            for file_path in client_dir.rglob("*"):
                if not file_path.is_file():
                    continue

                # Check year filter if specified
                if year_filter:
                    file_parsed = self.parser.parse(file_path)
                    if file_parsed.year and file_parsed.year not in year_filter:
                        continue

                files.append(file_path)

        return files

    async def _process_file(self, file_path: Path, dry_run: bool) -> None:
        """Process a single file.

        Args:
            file_path: Path to the file
            dry_run: If True, don't send notifications
        """
        self.files_scanned += 1

        try:
            # Parse the path
            parsed = self.parser.parse(file_path)

            if not parsed.is_valid:
                self.files_skipped += 1
                return

            # Handle .lnk files for relationships
            if self.parser.is_lnk_file(file_path):
                if not dry_run and parsed.client_code:
                    relationship = find_relationship_from_lnk(
                        file_path,
                        parsed.client_code,
                        self.parser.client_patterns,
                    )
                    if relationship:
                        await self.api_client.notify_relationship(
                            individual_code=relationship["individual_code"],
                            business_code=relationship["business_code"],
                            source_path=relationship["source_path"],
                        )
                        self.relationships_found += 1
                self.files_skipped += 1  # Don't queue .lnk as documents
                return

            if dry_run:
                self.files_queued += 1
                return

            # Get file info
            stat = file_path.stat()
            file_hash = self._compute_hash(file_path)

            response = await self.api_client.notify_file_arrived(
                nas_path=str(file_path),
                file_size=stat.st_size,
                file_hash=file_hash,
                modified_time=datetime.fromtimestamp(stat.st_mtime),
                parsed_info=parsed,
            )

            if response.status in ("queued", "pending_approval"):
                self.files_queued += 1
            elif response.status == "duplicate":
                self.files_skipped += 1
            else:
                self.files_failed += 1

            # Small delay to avoid overwhelming the API
            await asyncio.sleep(0.01)

        except Exception as e:
            self.files_failed += 1
            logger.error(
                "Failed to process file",
                path=str(file_path),
                error=str(e),
            )

    def _compute_hash(self, path: Path) -> str:
        """Compute SHA256 hash of a file."""
        sha256 = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        return f"sha256:{sha256.hexdigest()}"
