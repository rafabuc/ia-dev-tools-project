"""
Workflow state cache utilities using Redis.

This module provides caching for workflow state snapshots to enable
fast dashboard queries without hitting the database.
"""

import os
import uuid
from typing import Optional, Dict, Any
import redis
import json


class WorkflowCache:
    """Workflow state cache for fast retrieval."""

    def __init__(self, redis_url: Optional[str] = None):
        """
        Initialize workflow cache.

        Args:
            redis_url: Redis connection URL (defaults to env REDIS_URL)
        """
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.client = redis.from_url(self.redis_url, decode_responses=True)
        self.ttl_seconds = 3600  # 1 hour

        # Test connection
        try:
            self.client.ping()
            print(f"✅ WorkflowCache __init__ Connected to Redis at {self.redis_url}")
        except Exception as e:
            print(f"❌ WorkflowCache __init__ Failed to connect to Redis: {e}")


    def get_workflow_state(self, workflow_id: uuid.UUID) -> Optional[Dict[str, Any]]:
        """
        Get cached workflow state.

        Args:
            workflow_id: Workflow identifier

        Returns:
            Optional[Dict[str, Any]]: Workflow state snapshot or None

        Example:
            {
                "id": "uuid",
                "type": "incident_response",
                "status": "running",
                "progress": "3/5 steps completed",
                "current_step": "search_related_runbooks"
            }
        """
        key = f"workflow:state:{workflow_id}"
        state_data = self.client.get(key)

        if not state_data:
            return None

        try:
            return json.loads(state_data)
        except json.JSONDecodeError:
            return None

    def set_workflow_state(
        self,
        workflow_id: uuid.UUID,
        state: Dict[str, Any],
        ttl_seconds: Optional[int] = None
    ) -> bool:
        """
        Set cached workflow state.

        Args:
            workflow_id: Workflow identifier
            state: Workflow state snapshot
            ttl_seconds: Optional TTL override (default: 1 hour)

        Returns:
            bool: True if successful, False otherwise
        """
        key = f"workflow:state:{workflow_id}"
        ttl = ttl_seconds or self.ttl_seconds

        try:
            self.client.setex(key, ttl, json.dumps(state))
            return True
        except Exception:
            return False

    def delete_workflow_state(self, workflow_id: uuid.UUID) -> bool:
        """
        Delete cached workflow state.

        Args:
            workflow_id: Workflow identifier

        Returns:
            bool: True if deleted, False if not found
        """
        key = f"workflow:state:{workflow_id}"
        return bool(self.client.delete(key))

    def invalidate_cache(self, cache_keys: list) -> int:
        """
        Invalidate multiple cache keys (for KB sync workflow).

        Args:
            cache_keys: List of cache key patterns (e.g., ["runbook:*"])

        Returns:
            int: Number of keys deleted
        """
        deleted_count = 0
        for pattern in cache_keys:
            keys = self.client.keys(pattern)
            if keys:
                deleted_count += self.client.delete(*keys)
        return deleted_count
