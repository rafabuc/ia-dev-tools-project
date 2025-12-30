"""
Notification service for sending alerts via multiple channels.

This module provides a notification service supporting webhook delivery
with extensibility for additional channels (email, Slack, etc.).
"""

import os
from typing import List, Dict, Any, Optional
import requests
from requests.exceptions import RequestException

from backend.utils.logging import get_logger

logger = get_logger(__name__)


class NotificationError(Exception):
    """Exception raised for notification delivery failures."""
    pass


class NotificationService:
    """
    Service for sending notifications to configured channels.

    Supports:
    - Webhook (HTTP POST)
    - Email (future)
    - Slack (future)
    """

    def __init__(self):
        """Initialize notification service with configuration from environment."""
        self.webhook_url = os.getenv("NOTIFICATION_WEBHOOK_URL")
        self.webhook_enabled = bool(self.webhook_url)

        if not self.webhook_enabled:
            logger.warning("notification_service_webhook_disabled", message="NOTIFICATION_WEBHOOK_URL not configured")

    def send(
        self,
        message: str,
        channels: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Send notification to specified channels.

        Args:
            message: Notification message
            channels: List of channels ("webhook", "email", "slack")
            metadata: Optional metadata to include

        Returns:
            Dict[str, Any]: {
                "sent_to": ["webhook"],
                "failed": [],
                "status": "success" | "partial" | "failed"
            }

        Raises:
            NotificationError: If all channels fail
        """
        if channels is None:
            channels = ["webhook"]

        logger.info("notification_send_started", message=message, channels=channels)

        sent_to = []
        failed = []

        for channel in channels:
            try:
                if channel == "webhook":
                    self._send_webhook(message, metadata)
                    sent_to.append("webhook")
                elif channel == "email":
                    logger.warning("notification_channel_not_implemented", channel="email")
                    failed.append("email")
                elif channel == "slack":
                    logger.warning("notification_channel_not_implemented", channel="slack")
                    failed.append("slack")
                else:
                    logger.warning("notification_channel_unknown", channel=channel)
                    failed.append(channel)
            except Exception as e:
                logger.error("notification_channel_failed", channel=channel, error=str(e))
                failed.append(channel)

        # Determine overall status
        if len(sent_to) == len(channels):
            status = "success"
        elif len(sent_to) > 0:
            status = "partial"
        else:
            status = "failed"
            raise NotificationError(f"All notification channels failed: {failed}")

        result = {
            "sent_to": sent_to,
            "failed": failed,
            "status": status
        }

        logger.info("notification_send_completed", status=status, sent_to=sent_to, failed=failed)
        return result

    def _send_webhook(self, message: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Send notification via webhook (HTTP POST).

        Args:
            message: Notification message
            metadata: Optional metadata

        Raises:
            NotificationError: If webhook delivery fails
        """
        if not self.webhook_enabled:
            raise NotificationError("Webhook notifications not configured")

        payload = {
            "message": message,
            "timestamp": "auto",  # TODO: Add actual timestamp
            "metadata": metadata or {}
        }

        try:
            response = requests.post(
                self.webhook_url,
                json=payload,
                timeout=10,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()

            logger.info("notification_webhook_success", url=self.webhook_url)

        except RequestException as e:
            logger.error("notification_webhook_failed", url=self.webhook_url, error=str(e))
            raise NotificationError(f"Webhook delivery failed: {str(e)}")

    def _send_email(self, message: str, recipients: List[str], metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Send notification via email (future implementation).

        Args:
            message: Notification message
            recipients: List of email addresses
            metadata: Optional metadata

        Raises:
            NotImplementedError: Not yet implemented
        """
        raise NotImplementedError("Email notifications not yet implemented")

    def _send_slack(self, message: str, channel: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Send notification via Slack (future implementation).

        Args:
            message: Notification message
            channel: Slack channel
            metadata: Optional metadata

        Raises:
            NotImplementedError: Not yet implemented
        """
        raise NotImplementedError("Slack notifications not yet implemented")
