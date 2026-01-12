"""Daily digest email sender.

Sends a daily summary of NAS sync activity to configured recipients.
"""

import smtplib
from datetime import date, datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import structlog

from nas_sync.api_client import APIClient
from nas_sync.models import Config

logger = structlog.get_logger()


class DigestSender:
    """Send daily digest emails about sync activity.

    Collects statistics from the API and sends a summary email
    to configured recipients.
    """

    def __init__(self, config: Config):
        """Initialize the digest sender.

        Args:
            config: Full configuration
        """
        self.config = config
        self.api_client = APIClient(config)

    async def send(self) -> bool:
        """Send the daily digest email.

        Returns:
            True if email was sent successfully
        """
        if not self.config.digest.enabled:
            logger.info("Digest emails disabled")
            return False

        # Get sync status from API
        status = await self.api_client.get_sync_status()
        await self.api_client.close()

        if not status:
            logger.error("Could not get sync status for digest")
            return False

        # Generate email content
        subject = f"NAS Sync Daily Digest - {date.today().isoformat()}"
        html_content = self._generate_html(status)
        text_content = self._generate_text(status)

        # Send email
        return self._send_email(subject, html_content, text_content)

    def _generate_html(self, status) -> str:
        """Generate HTML email content.

        Args:
            status: SyncStatus from API

        Returns:
            HTML string
        """
        pending = status.queue_stats.get("pending_approval", 0)
        processed = status.today_stats.get("files_processed", 0)
        detected = status.today_stats.get("files_detected", 0)
        failed = status.today_stats.get("files_failed", 0)

        pending_class = "warning" if pending > 0 else "ok"
        failed_class = "error" if failed > 0 else "ok"

        return f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        h1 {{ color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px; }}
        .stats {{ display: flex; flex-wrap: wrap; gap: 20px; margin: 20px 0; }}
        .stat-box {{
            background: #f8f9fa; border-radius: 8px;
            padding: 15px; min-width: 120px;
        }}
        .stat-value {{ font-size: 32px; font-weight: bold; color: #2c3e50; }}
        .stat-label {{ font-size: 14px; color: #666; }}
        .warning {{ background: #fff3cd; }}
        .warning .stat-value {{ color: #856404; }}
        .error {{ background: #f8d7da; }}
        .error .stat-value {{ color: #721c24; }}
        .ok .stat-value {{ color: #28a745; }}
        .footer {{ margin-top: 30px; font-size: 12px; color: #666; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>NAS Sync Daily Digest</h1>
        <p>Summary for {date.today().strftime("%B %d, %Y")}</p>

        <div class="stats">
            <div class="stat-box">
                <div class="stat-value">{detected}</div>
                <div class="stat-label">Files Detected</div>
            </div>
            <div class="stat-box">
                <div class="stat-value">{processed}</div>
                <div class="stat-label">Files Processed</div>
            </div>
            <div class="stat-box {failed_class}">
                <div class="stat-value">{failed}</div>
                <div class="stat-label">Files Failed</div>
            </div>
            <div class="stat-box {pending_class}">
                <div class="stat-value">{pending}</div>
                <div class="stat-label">Pending Approval</div>
            </div>
        </div>

        <p><strong>Agent Status:</strong> {status.agent_status}</p>

        {self._pending_alert(pending)}
        {self._failed_alert(failed)}

        <div class="footer">
            <p>This is an automated message from Le CPA Agent NAS Sync.</p>
            <p>Generated at {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
        </div>
    </div>
</body>
</html>
"""

    def _pending_alert(self, pending: int) -> str:
        """Generate pending approval alert HTML."""
        if pending > 0:
            return (
                "<p style='color: #856404;'><strong>Action Required:</strong> "
                "There are items pending approval in the sync queue.</p>"
            )
        return ""

    def _failed_alert(self, failed: int) -> str:
        """Generate failed files alert HTML."""
        if failed > 0:
            return (
                "<p style='color: #721c24;'><strong>Attention:</strong> "
                "Some files failed to process. Please check the logs.</p>"
            )
        return ""

    def _generate_text(self, status) -> str:
        """Generate plain text email content.

        Args:
            status: SyncStatus from API

        Returns:
            Plain text string
        """
        pending = status.queue_stats.get("pending_approval", 0)
        processed = status.today_stats.get("files_processed", 0)
        detected = status.today_stats.get("files_detected", 0)
        failed = status.today_stats.get("files_failed", 0)

        text = f"""
NAS Sync Daily Digest
=====================

Summary for {date.today().strftime("%B %d, %Y")}

Statistics:
- Files Detected: {detected}
- Files Processed: {processed}
- Files Failed: {failed}
- Pending Approval: {pending}

Agent Status: {status.agent_status}
"""

        if pending > 0:
            text += "\n** ACTION REQUIRED: Items pending approval in sync queue **\n"

        if failed > 0:
            text += "\n** ATTENTION: Some files failed to process **\n"

        text += f"""
---
This is an automated message from Le CPA Agent NAS Sync.
Generated at {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
"""
        return text

    def _send_email(self, subject: str, html: str, text: str) -> bool:
        """Send email via SMTP.

        Args:
            subject: Email subject
            html: HTML content
            text: Plain text content

        Returns:
            True if sent successfully
        """
        smtp_config = self.config.digest.smtp
        recipients = self.config.digest.recipients

        if not recipients:
            logger.warning("No recipients configured for digest")
            return False

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = smtp_config.user
        msg["To"] = ", ".join(recipients)

        msg.attach(MIMEText(text, "plain"))
        msg.attach(MIMEText(html, "html"))

        try:
            with smtplib.SMTP(smtp_config.host, smtp_config.port) as server:
                server.starttls()
                server.login(smtp_config.user, smtp_config.password)
                server.sendmail(smtp_config.user, recipients, msg.as_string())

            logger.info(
                "Digest email sent",
                recipients=recipients,
                subject=subject,
            )
            return True

        except Exception as e:
            logger.error(
                "Failed to send digest email",
                error=str(e),
                recipients=recipients,
            )
            return False
