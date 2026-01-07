"""
GitHub API client with circuit breaker pattern.

This module provides a robust GitHub API client for creating issues,
with circuit breaker protection against API failures and rate limiting.
"""

import os
from typing import Dict, Any, List, Optional
from enum import Enum
import time
import requests
from requests.exceptions import RequestException

from backend.utils.logging import get_logger

logger = get_logger(__name__)


class CircuitState(str, Enum):
    """Circuit breaker states."""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing recovery


class GitHubAPIError(Exception):
    """Exception raised for GitHub API errors."""
    pass


class GitHubDisabledError(Exception):
    """Exception raised when GitHub integration is disabled."""
    pass


class CircuitBreaker:
    """
    Circuit breaker for protecting against cascading failures.

    States:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Too many failures, reject requests immediately
    - HALF_OPEN: Testing if service recovered, allow limited requests
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        success_threshold: int = 2
    ):
        """
        Initialize circuit breaker.

        Args:
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Seconds to wait before attempting recovery
            success_threshold: Number of successes needed to close circuit in half-open state
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.success_threshold = success_threshold

        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED

    def call(self, func, *args, **kwargs):
        """
        Execute function through circuit breaker.

        Args:
            func: Function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Function result if successful

        Raises:
            GitHubAPIError: If circuit is open or function fails
        """
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
                logger.info("circuit_breaker_half_open")
            else:
                raise GitHubAPIError("Circuit breaker is OPEN - GitHub API unavailable")

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise

    def _on_success(self):
        """Handle successful request."""
        self.failure_count = 0

        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.success_threshold:
                self.state = CircuitState.CLOSED
                self.success_count = 0
                logger.info("circuit_breaker_closed")

    def _on_failure(self):
        """Handle failed request."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        self.success_count = 0

        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            logger.warning("circuit_breaker_open", failure_count=self.failure_count)

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt recovery."""
        if self.last_failure_time is None:
            return False
        return (time.time() - self.last_failure_time) >= self.recovery_timeout


class GitHubClient:
    """
    GitHub API client with circuit breaker protection.

    Provides methods for creating issues, with automatic retry logic
    and circuit breaker pattern for resilience.
    """

    def __init__(
        self,
        token: Optional[str] = None,
        repo: Optional[str] = None,
        base_url: str = "https://api.github.com",
        enabled: Optional[bool] = None
    ):
        """
        Initialize GitHub client.

        Args:
            token: GitHub API token (defaults to env GITHUB_TOKEN)
            repo: Repository in format "owner/repo" (defaults to env GITHUB_REPO)
            base_url: GitHub API base URL
            enabled: Whether GitHub integration is enabled (defaults to env GITHUB_ENABLED)
        """
        # Check if GitHub integration is enabled
        if enabled is None:
            enabled_env = os.getenv("GITHUB_ENABLED", "false").lower()
            self.enabled = enabled_env in ("true", "1", "yes", "on")
        else:
            self.enabled = enabled
        
        self.token = token or os.getenv("GITHUB_TOKEN")
        self.repo = repo or os.getenv("GITHUB_REPO")
        self.base_url = base_url

        # Log configuration status
        if not self.enabled:
            logger.info("github_client_disabled", message="GitHub integration is disabled")
            return

        if not self.token:
            logger.warning("github_client_no_token", message="GITHUB_TOKEN not configured")

        if not self.repo:
            logger.warning("github_client_no_repo", message="GITHUB_REPO not configured")

        self.circuit_breaker = CircuitBreaker(
            failure_threshold=5,
            recovery_timeout=60,
            success_threshold=2
        )

        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json"
        })

    def _check_enabled(self):
        """Check if GitHub integration is enabled."""
        if not self.enabled:
            raise GitHubDisabledError("GitHub integration is disabled")

    def create_issue(
        self,
        title: str,
        body: str,
        labels: Optional[List[str]] = None,
        assignees: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Create a GitHub issue.

        Args:
            title: Issue title
            body: Issue body (markdown)
            labels: List of label names
            assignees: List of usernames to assign

        Returns:
            Dict[str, Any]: {
                "html_url": "https://github.com/owner/repo/issues/123",
                "number": 123,
                "state": "open",
                "skipped": False
            }
            Or if disabled:
            {
                "skipped": True,
                "reason": "GitHub integration is disabled"
            }

        Raises:
            GitHubDisabledError: If GitHub integration is disabled
            GitHubAPIError: If issue creation fails
        """
        # Check if enabled
        if not self.enabled:
            logger.info("github_create_issue_skipped", reason="GitHub integration disabled")
            return {
                "skipped": True,
                "reason": "GitHub integration is disabled"
            }

        if not self.repo:
            raise GitHubAPIError("GitHub repository not configured")

        logger.info("github_create_issue_started", title=title, repo=self.repo)

        def _create():
            url = f"{self.base_url}/repos/{self.repo}/issues"
            payload = {
                "title": title,
                "body": body,
                "labels": labels or [],
                "assignees": assignees or []
            }

            try:
                response = self.session.post(url, json=payload, timeout=10)
                response.raise_for_status()
                data = response.json()

                logger.info(
                    "github_create_issue_success",
                    issue_number=data["number"],
                    issue_url=data["html_url"]
                )

                return {
                    "html_url": data["html_url"],
                    "number": data["number"],
                    "state": data["state"],
                    "skipped": False
                }

            except RequestException as e:
                logger.error("github_create_issue_failed", error=str(e))
                raise GitHubAPIError(f"GitHub API request failed: {str(e)}")

        try:
            return self.circuit_breaker.call(_create)
        except Exception as e:
            logger.error("github_create_issue_circuit_breaker_error", error=str(e))
            raise

    def get_issue(self, issue_number: int) -> Dict[str, Any]:
        """
        Get issue details.

        Args:
            issue_number: Issue number

        Returns:
            Dict[str, Any]: Issue details

        Raises:
            GitHubDisabledError: If GitHub integration is disabled
            GitHubAPIError: If request fails
        """
        self._check_enabled()
        
        if not self.repo:
            raise GitHubAPIError("GitHub repository not configured")

        def _get():
            url = f"{self.base_url}/repos/{self.repo}/issues/{issue_number}"
            try:
                response = self.session.get(url, timeout=10)
                response.raise_for_status()
                return response.json()
            except RequestException as e:
                raise GitHubAPIError(f"GitHub API request failed: {str(e)}")

        return self.circuit_breaker.call(_get)

    def is_enabled(self) -> bool:
        """
        Check if GitHub integration is enabled.

        Returns:
            bool: True if enabled, False otherwise
        """
        return self.enabled