"""
Redis client utilities for Celery result backend.

This module provides utilities for interacting with Redis as the Celery result backend,
including result retrieval and connection management.
"""

import os
from typing import Optional, Any, Dict
import redis
import json


class RedisClient:
    """Redis client for Celery result backend operations."""

    def __init__(self, redis_url: Optional[str] = None):
        """
        Initialize Redis client.

        Args:
            redis_url: Redis connection URL (defaults to env CELERY_RESULT_BACKEND)
        """
        self.redis_url = redis_url or os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/2")
        self.client = redis.from_url(self.redis_url, decode_responses=True)

    def get_task_result(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get Celery task result from Redis.

        Args:
            task_id: Celery task identifier

        Returns:
            Optional[Dict[str, Any]]: Task result or None if not found

        Example:
            {
                "status": "SUCCESS",
                "result": {...},
                "traceback": null,
                "children": [],
                "date_done": "2025-12-29T10:30:00Z"
            }
        """
        key = f"celery-task-meta-{task_id}"
        result_data = self.client.get(key)

        if not result_data:
            return None

        try:
            return json.loads(result_data)
        except json.JSONDecodeError:
            return None

    def set_task_result(self, task_id: str, result: Dict[str, Any], ttl_seconds: int = 604800) -> bool:
        """
        Set Celery task result in Redis.

        Args:
            task_id: Celery task identifier
            result: Task result data
            ttl_seconds: Time to live in seconds (default: 7 days)

        Returns:
            bool: True if successful, False otherwise
        """
        key = f"celery-task-meta-{task_id}"
        try:
            self.client.setex(key, ttl_seconds, json.dumps(result))
            return True
        except Exception:
            return False

    def delete_task_result(self, task_id: str) -> bool:
        """
        Delete Celery task result from Redis.

        Args:
            task_id: Celery task identifier

        Returns:
            bool: True if deleted, False if not found
        """
        key = f"celery-task-meta-{task_id}"
        return bool(self.client.delete(key))

    def ping(self) -> bool:
        """
        Test Redis connection.

        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            return self.client.ping()
        except Exception:
            return False
