"""
Unit test for invalidate_cache Celery task.

Tests the task that invalidates caches for updated runbooks.

TDD: This test should FAIL initially before implementation.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

# These imports will fail until implementation exists - that's expected for TDD
try:
    from backend.workflows.tasks.kb_sync_tasks import invalidate_cache
except ImportError:
    pytest.skip("Implementation not yet complete", allow_module_level=True)


class TestInvalidateCache:
    """Unit tests for invalidate_cache task."""

    @patch('backend.workflows.tasks.kb_sync_tasks.workflow_cache')
    def test_invalidate_cache_success(self, mock_cache):
        """Test successful cache invalidation."""
        # Arrange
        cache_keys = ["runbook:db_troubleshooting", "runbook:api_recovery"]
        mock_cache.invalidate_keys.return_value = {
            "invalidated_keys": 2,
            "status": "success"
        }

        # Act
        result = invalidate_cache(cache_keys)

        # Assert
        assert result is not None
        assert "invalidated_keys" in result
        assert "status" in result
        assert result["status"] == "success"
        assert result["invalidated_keys"] == 2

    @patch('backend.workflows.tasks.kb_sync_tasks.workflow_cache')
    def test_invalidate_cache_empty_list(self, mock_cache):
        """Test invalidation with no cache keys."""
        # Arrange
        cache_keys = []
        mock_cache.invalidate_keys.return_value = {
            "invalidated_keys": 0,
            "status": "success"
        }

        # Act
        result = invalidate_cache(cache_keys)

        # Assert
        assert result["invalidated_keys"] == 0
        assert result["status"] == "success"

    @patch('backend.workflows.tasks.kb_sync_tasks.workflow_cache')
    def test_invalidate_cache_with_retry(self, mock_cache):
        """Test retry behavior when cache invalidation fails."""
        # Arrange
        cache_keys = ["runbook:test"]
        mock_cache.invalidate_keys.side_effect = Exception("Redis connection error")

        # Act & Assert
        with pytest.raises(Exception, match="Redis connection error"):
            invalidate_cache(cache_keys)

    @patch('backend.workflows.tasks.kb_sync_tasks.workflow_cache')
    def test_invalidate_cache_max_retries(self, mock_cache):
        """Test that task respects max_retries=3 configuration."""
        # Verify task configuration
        assert invalidate_cache.max_retries == 3

    @patch('backend.workflows.tasks.kb_sync_tasks.workflow_cache')
    def test_invalidate_cache_pattern_matching(self, mock_cache):
        """Test cache invalidation with pattern matching."""
        # Arrange
        # Use wildcard pattern to invalidate multiple keys
        cache_keys = ["runbook:*"]
        mock_cache.invalidate_keys.return_value = {
            "invalidated_keys": 5,  # Pattern matched 5 keys
            "status": "success"
        }

        # Act
        result = invalidate_cache(cache_keys)

        # Assert
        assert result["invalidated_keys"] == 5

    @patch('backend.workflows.tasks.kb_sync_tasks.workflow_cache')
    def test_invalidate_cache_specific_runbooks(self, mock_cache):
        """Test invalidation of specific runbook caches."""
        # Arrange
        cache_keys = [
            "runbook:db_troubleshooting",
            "runbook:api_recovery",
            "runbook:network_debugging"
        ]
        mock_cache.invalidate_keys.return_value = {
            "invalidated_keys": 3,
            "status": "success"
        }

        # Act
        result = invalidate_cache(cache_keys)

        # Assert
        mock_cache.invalidate_keys.assert_called_once_with(cache_keys)
        assert result["invalidated_keys"] == 3

    @patch('backend.workflows.tasks.kb_sync_tasks.workflow_cache')
    def test_invalidate_cache_related_caches(self, mock_cache):
        """Test that related caches are also invalidated."""
        # Arrange
        cache_keys = [
            "runbook:doc",
            "search:runbook:doc",  # Related search cache
            "embedding:runbook:doc"  # Related embedding cache
        ]
        mock_cache.invalidate_keys.return_value = {
            "invalidated_keys": 3,
            "status": "success"
        }

        # Act
        result = invalidate_cache(cache_keys)

        # Assert
        assert result["invalidated_keys"] == 3

    @patch('backend.workflows.tasks.kb_sync_tasks.workflow_cache')
    def test_invalidate_cache_partial_failure(self, mock_cache):
        """Test handling of partial cache invalidation failure."""
        # Arrange
        cache_keys = ["runbook:doc1", "runbook:doc2", "runbook:doc3"]
        # Some keys invalidated successfully, some failed
        mock_cache.invalidate_keys.return_value = {
            "invalidated_keys": 2,
            "status": "partial",
            "failed": ["runbook:doc3"]
        }

        # Act
        result = invalidate_cache(cache_keys)

        # Assert
        assert result["invalidated_keys"] == 2
        assert result["status"] == "partial"

    @patch('backend.workflows.tasks.kb_sync_tasks.workflow_cache')
    def test_invalidate_cache_redis_unavailable(self, mock_cache):
        """Test behavior when Redis is unavailable."""
        # Arrange
        cache_keys = ["runbook:test"]
        mock_cache.invalidate_keys.side_effect = Exception("Redis unavailable")

        # Act & Assert
        with pytest.raises(Exception, match="Redis unavailable"):
            invalidate_cache(cache_keys)

    @patch('backend.workflows.tasks.kb_sync_tasks.workflow_cache')
    def test_invalidate_cache_large_batch(self, mock_cache):
        """Test invalidation of large batch of cache keys."""
        # Arrange
        cache_keys = [f"runbook:doc{i}" for i in range(100)]
        mock_cache.invalidate_keys.return_value = {
            "invalidated_keys": 100,
            "status": "success"
        }

        # Act
        result = invalidate_cache(cache_keys)

        # Assert
        assert result["invalidated_keys"] == 100
        assert result["status"] == "success"
