"""Filesystem watcher using watchdog.

Monitors the NAS directory for file changes and triggers processing
with debouncing to handle rapid file system events.
"""

import asyncio
import hashlib
from datetime import datetime, timedelta
from pathlib import Path

import structlog
from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

from nas_sync.api_client import APIClient
from nas_sync.lnk_parser import find_relationship_from_lnk
from nas_sync.models import Config
from nas_sync.parser import FolderParser

logger = structlog.get_logger()


class DebouncedHandler(FileSystemEventHandler):
    """File event handler with debouncing for rapid changes.

    When files are copied or saved, they often trigger multiple events
    in quick succession. This handler debounces events by waiting for
    a quiet period before processing.
    """

    def __init__(
        self,
        parser: FolderParser,
        api_client: APIClient,
        config: Config,
    ):
        """Initialize the debounced handler.

        Args:
            parser: Folder parser for extracting path info
            api_client: API client for notifications
            config: Full configuration
        """
        self.parser = parser
        self.api_client = api_client
        self.config = config
        self.debounce_seconds = config.nas.debounce_seconds
        self.pending_events: dict[str, dict] = {}
        self._loop: asyncio.AbstractEventLoop | None = None

    def set_event_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        """Set the event loop for async operations."""
        self._loop = loop

    def on_created(self, event: FileSystemEvent) -> None:
        """Handle file creation event."""
        if event.is_directory:
            return
        self._schedule_processing(event.src_path, "created")

    def on_modified(self, event: FileSystemEvent) -> None:
        """Handle file modification event."""
        if event.is_directory:
            return
        self._schedule_processing(event.src_path, "modified")

    def on_deleted(self, event: FileSystemEvent) -> None:
        """Handle file deletion event."""
        if event.is_directory:
            return
        self._schedule_processing(event.src_path, "deleted")

    def on_moved(self, event: FileSystemEvent) -> None:
        """Handle file move event (treated as delete + create)."""
        if event.is_directory:
            return
        self._schedule_processing(event.src_path, "deleted")
        if hasattr(event, "dest_path"):
            self._schedule_processing(event.dest_path, "created")

    def _schedule_processing(self, path: str, event_type: str) -> None:
        """Schedule file processing with debounce.

        Args:
            path: Path to the file
            event_type: Type of event (created, modified, deleted)
        """
        self.pending_events[path] = {
            "time": datetime.now(),
            "type": event_type,
        }
        logger.debug("Event scheduled", path=path, event_type=event_type)

    async def process_pending(self) -> None:
        """Process events that have passed the debounce window."""
        now = datetime.now()
        cutoff = now - timedelta(seconds=self.debounce_seconds)

        to_process: list[tuple[str, str]] = []
        paths_to_remove: list[str] = []

        for path, info in list(self.pending_events.items()):
            if info["time"] < cutoff:
                to_process.append((path, info["type"]))
                paths_to_remove.append(path)

        for path in paths_to_remove:
            del self.pending_events[path]

        for path, event_type in to_process:
            try:
                await self._process_file(path, event_type)
            except Exception as e:
                logger.error(
                    "Error processing file",
                    path=path,
                    event_type=event_type,
                    error=str(e),
                )

    async def _process_file(self, path: str, event_type: str) -> None:
        """Process a single file event.

        Args:
            path: Path to the file
            event_type: Type of event (created, modified, deleted)
        """
        logger.info("Processing file", path=path, event_type=event_type)

        # Parse the path
        parsed = self.parser.parse(path)

        if not parsed.is_valid:
            logger.debug("Skipping file", path=path, reason=parsed.skip_reason)
            return

        # Handle .lnk files specially to extract relationships
        if self.parser.is_lnk_file(path) and event_type != "deleted":
            await self._process_lnk_file(path, parsed.client_code)
            return

        if event_type == "deleted":
            await self.api_client.notify_file_deleted(path)
        else:
            # Get file info
            file_path = Path(path)
            if not file_path.exists():
                logger.warning("File no longer exists", path=path)
                return

            stat = file_path.stat()
            file_hash = _compute_hash(file_path)

            await self.api_client.notify_file_arrived(
                nas_path=path,
                file_size=stat.st_size,
                file_hash=file_hash,
                modified_time=datetime.fromtimestamp(stat.st_mtime),
                parsed_info=parsed,
            )

    async def _process_lnk_file(
        self, path: str, source_client_code: str | None
    ) -> None:
        """Process a .lnk shortcut file to extract relationships.

        Args:
            path: Path to the .lnk file
            source_client_code: Client code of the containing folder
        """
        if not source_client_code:
            return

        relationship = find_relationship_from_lnk(
            path,
            source_client_code,
            self.parser.client_patterns,
        )

        if relationship:
            await self.api_client.notify_relationship(
                individual_code=relationship["individual_code"],
                business_code=relationship["business_code"],
                source_path=relationship["source_path"],
            )


def _compute_hash(path: Path) -> str:
    """Compute SHA256 hash of a file.

    Args:
        path: Path to the file

    Returns:
        Hash string in format "sha256:hexdigest"
    """
    sha256 = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return f"sha256:{sha256.hexdigest()}"


class NASWatcher:
    """Watch NAS filesystem for changes.

    Manages the watchdog observer and processing loop.
    """

    def __init__(self, config: Config):
        """Initialize the NAS watcher.

        Args:
            config: Full configuration
        """
        self.config = config
        self.parser = FolderParser(config)
        self.api_client = APIClient(config)
        self.handler = DebouncedHandler(
            parser=self.parser,
            api_client=self.api_client,
            config=config,
        )
        self.observer = Observer()
        self._running = False

    def start(self) -> None:
        """Start watching the NAS."""
        nas_root = self.config.nas.root_path
        recursive = self.config.nas.watch_recursive

        self.observer.schedule(
            self.handler,
            nas_root,
            recursive=recursive,
        )
        self.observer.start()
        self._running = True
        logger.info("Watcher started", root=nas_root, recursive=recursive)

    def stop(self) -> None:
        """Stop watching."""
        self._running = False
        self.observer.stop()
        self.observer.join()
        logger.info("Watcher stopped")

    async def run_processing_loop(self) -> None:
        """Run the event processing loop.

        This should be called as an async task after starting the watcher.
        It processes pending events every 0.5 seconds.
        """
        self.handler.set_event_loop(asyncio.get_event_loop())

        while self._running:
            await self.handler.process_pending()
            await asyncio.sleep(0.5)

        # Process any remaining events
        await self.handler.process_pending()

        # Close API client
        await self.api_client.close()

    @property
    def is_running(self) -> bool:
        """Check if the watcher is running."""
        return self._running
