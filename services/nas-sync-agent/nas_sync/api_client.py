"""HTTP client for communicating with Le CPA Agent API."""

from datetime import datetime

import httpx
import structlog
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from nas_sync.models import (
    Config,
    FileArrivedRequest,
    FileArrivedResponse,
    FileDeletedRequest,
    FileDeletedResponse,
    ParsedPath,
    SyncStatus,
)

logger = structlog.get_logger()


class APIClient:
    """HTTP client for Le CPA Agent API.

    Handles communication with the main API server including:
    - Notifying about new/modified files
    - Notifying about deleted files
    - Sending heartbeats
    - Querying sync status
    """

    def __init__(self, config: Config):
        """Initialize the API client.

        Args:
            config: Full configuration object
        """
        self.config = config
        self.base_url = config.api.base_url.rstrip("/")
        self.timeout = httpx.Timeout(config.api.timeout_seconds)
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout,
                headers={
                    "Authorization": f"Bearer {self.config.api.api_key}",
                    "Content-Type": "application/json",
                    "User-Agent": "nas-sync-agent/0.1.0",
                },
            )
        return self._client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    @retry(
        retry=retry_if_exception_type((httpx.NetworkError, httpx.TimeoutException)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
    )
    async def notify_file_arrived(
        self,
        nas_path: str,
        file_size: int,
        file_hash: str,
        modified_time: datetime,
        parsed_info: ParsedPath,
    ) -> FileArrivedResponse:
        """Notify the API that a file has been created or modified.

        Args:
            nas_path: Full path to the file on NAS
            file_size: File size in bytes
            file_hash: SHA256 hash of the file
            modified_time: File modification timestamp
            parsed_info: Parsed path information

        Returns:
            Response indicating how the file was handled
        """
        client = await self._get_client()

        request = FileArrivedRequest(
            nas_path=nas_path,
            file_size=file_size,
            file_hash=file_hash,
            modified_time=modified_time,
            parsed_info=parsed_info,
        )

        logger.info(
            "Notifying API of file arrival",
            nas_path=nas_path,
            client_code=parsed_info.client_code,
        )

        try:
            response = await client.post(
                "/ingest/file-arrived",
                json=request.model_dump(mode="json"),
            )
            response.raise_for_status()
            data = response.json()
            result = FileArrivedResponse(**data)

            logger.info(
                "File arrival notification sent",
                nas_path=nas_path,
                status=result.status,
                document_id=result.document_id,
            )
            return result

        except httpx.HTTPStatusError as e:
            logger.error(
                "API error on file arrival",
                nas_path=nas_path,
                status_code=e.response.status_code,
                detail=e.response.text,
            )
            return FileArrivedResponse(
                status="error",
                message=f"API error: {e.response.status_code}",
            )

    @retry(
        retry=retry_if_exception_type((httpx.NetworkError, httpx.TimeoutException)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
    )
    async def notify_file_deleted(self, nas_path: str) -> FileDeletedResponse:
        """Notify the API that a file has been deleted.

        Args:
            nas_path: Full path to the deleted file

        Returns:
            Response indicating how the deletion was handled
        """
        client = await self._get_client()

        request = FileDeletedRequest(nas_path=nas_path)

        logger.info("Notifying API of file deletion", nas_path=nas_path)

        try:
            response = await client.post(
                "/ingest/file-deleted",
                json=request.model_dump(mode="json"),
            )
            response.raise_for_status()
            data = response.json()
            result = FileDeletedResponse(**data)

            logger.info(
                "File deletion notification sent",
                nas_path=nas_path,
                status=result.status,
            )
            return result

        except httpx.HTTPStatusError as e:
            logger.error(
                "API error on file deletion",
                nas_path=nas_path,
                status_code=e.response.status_code,
                detail=e.response.text,
            )
            return FileDeletedResponse(
                status="error",
                message=f"API error: {e.response.status_code}",
            )

    @retry(
        retry=retry_if_exception_type((httpx.NetworkError, httpx.TimeoutException)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
    )
    async def send_heartbeat(self) -> bool:
        """Send a heartbeat to the API server.

        Returns:
            True if heartbeat was acknowledged, False otherwise
        """
        client = await self._get_client()

        try:
            response = await client.post(
                "/ingest/heartbeat",
                json={"timestamp": datetime.now().isoformat()},
            )
            response.raise_for_status()
            return True

        except httpx.HTTPStatusError as e:
            logger.warning(
                "Heartbeat failed",
                status_code=e.response.status_code,
            )
            return False

    async def get_sync_status(self) -> SyncStatus | None:
        """Get current sync status from the API.

        Returns:
            SyncStatus object or None if request failed
        """
        client = await self._get_client()

        try:
            response = await client.get("/ingest/sync-status")
            response.raise_for_status()
            return SyncStatus(**response.json())

        except httpx.HTTPError as e:
            logger.error("Failed to get sync status", error=str(e))
            return None

    async def notify_relationship(
        self,
        individual_code: str,
        business_code: str,
        source_path: str,
    ) -> bool:
        """Notify the API about a client relationship discovered from .lnk file.

        Args:
            individual_code: Client code of the individual
            business_code: Client code of the business
            source_path: Path to the .lnk file

        Returns:
            True if relationship was recorded, False otherwise
        """
        client = await self._get_client()

        try:
            response = await client.post(
                "/ingest/relationship",
                json={
                    "individual_code": individual_code,
                    "business_code": business_code,
                    "source": "lnk_shortcut",
                    "source_path": source_path,
                },
            )
            response.raise_for_status()

            logger.info(
                "Relationship notification sent",
                individual_code=individual_code,
                business_code=business_code,
            )
            return True

        except httpx.HTTPError as e:
            logger.error(
                "Failed to notify relationship",
                individual_code=individual_code,
                business_code=business_code,
                error=str(e),
            )
            return False
