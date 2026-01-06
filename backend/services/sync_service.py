"""
Synchronization service for knowledge base change detection.

Tracks file state and detects changes between sync operations.
"""

from typing import Dict, Any, List
import json
import os
from pathlib import Path

from backend.database import get_db
from backend.models.workflow import Workflow
from backend.utils.logging import get_logger

logger = get_logger(__name__)


class SyncService:
    """Service for detecting changes in knowledge base files."""

    def __init__(self, state_file: str = None):
        """
        Initialize sync service.

        Args:
            state_file: Optional path to state file for persistence
        """
        if state_file is None:
            # Default to storing state in database metadata
            self.use_database = True
            self.state_file = None
        else:
            self.use_database = False
            self.state_file = state_file

        logger.info(f"Sync service initialized (use_database={self.use_database})")

    def detect_changes(
        self,
        current_files: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Detect changes by comparing current files with previous state.

        Args:
            current_files: List of current file info dicts (path, mtime)

        Returns:
            Dict containing:
            - added: List of newly added file paths
            - modified: List of modified file paths
            - deleted: List of deleted file paths
            - unchanged: List of unchanged file paths
            - total_changes: Total number of changes
        """
        logger.info(f"Detecting changes for {len(current_files)} files")

        # Get previous state
        previous_state = self._load_previous_state()

        # Build current state dict for easy lookup
        current_state = {
            file_info["path"]: file_info["mtime"]
            for file_info in current_files
        }

        added = []
        modified = []
        deleted = []
        unchanged = []

        # Find added and modified files
        for path, mtime in current_state.items():
            if path not in previous_state:
                added.append(path)
            elif previous_state[path] != mtime:
                modified.append(path)
            else:
                unchanged.append(path)

        # Find deleted files
        for path in previous_state.keys():
            if path not in current_state:
                deleted.append(path)

        total_changes = len(added) + len(modified) + len(deleted)

        result = {
            "added": added,
            "modified": modified,
            "deleted": deleted,
            "unchanged": unchanged,
            "total_changes": total_changes
        }

        logger.info(
            f"Changes detected: {total_changes} total "
            f"({len(added)} added, {len(modified)} modified, {len(deleted)} deleted)"
        )

        # Save current state for next comparison
        self._save_current_state(current_state)

        return result

    def _load_previous_state(self) -> Dict[str, float]:
        """
        Load previous file state.

        Returns:
            Dict mapping file paths to mtimes
        """
        if self.use_database:
            return self._load_state_from_database()
        else:
            return self._load_state_from_file()

    def _load_state_from_database(self) -> Dict[str, float]:
        """Load state from database metadata."""
        db = next(get_db())
        try:
            # Look for most recent KB sync workflow
            workflow = db.query(Workflow).filter(
                Workflow.type == "kb_sync"
            ).order_by(Workflow.created_at.desc()).first()

            if workflow and workflow.workflow_data:
                state = workflow.workflow_data.get("last_sync_state", {})
                logger.info(f"Loaded state from database: {len(state)} files")
                return state

            logger.info("No previous state found in database")
            return {}

        except Exception as exc:
            logger.warning(f"Failed to load state from database: {exc}")
            return {}
        finally:
            db.close()

    def _load_state_from_file(self) -> Dict[str, float]:
        """Load state from file."""
        if not self.state_file or not os.path.exists(self.state_file):
            logger.info("No previous state file found")
            return {}

        try:
            with open(self.state_file, 'r') as f:
                state = json.load(f)
            logger.info(f"Loaded state from file: {len(state)} files")
            return state
        except (IOError, json.JSONDecodeError) as exc:
            logger.warning(f"Failed to load state from file: {exc}")
            return {}

    def _save_current_state(self, state: Dict[str, float]) -> None:
        """
        Save current file state for next comparison.

        Args:
            state: Dict mapping file paths to mtimes
        """
        if self.use_database:
            self._save_state_to_database(state)
        else:
            self._save_state_to_file(state)

    def _save_state_to_database(self, state: Dict[str, float]) -> None:
        """Save state to database metadata."""
        db = next(get_db())
        try:
            # Look for most recent KB sync workflow or create new one
            workflow = db.query(Workflow).filter(
                Workflow.type == "kb_sync"
            ).order_by(Workflow.created_at.desc()).first()

            if workflow:
                # Update existing workflow metadata
                if workflow.workflow_data is None:
                    workflow.workflow_data = {}
                workflow.workflow_data["last_sync_state"] = state
                db.commit()
                logger.info(f"Saved state to database: {len(state)} files")
            else:
                logger.info("No workflow found to save state")

        except Exception as exc:
            logger.error(f"Failed to save state to database: {exc}")
            db.rollback()
        finally:
            db.close()

    def _save_state_to_file(self, state: Dict[str, float]) -> None:
        """Save state to file."""
        if not self.state_file:
            return

        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.state_file), exist_ok=True)

            with open(self.state_file, 'w') as f:
                json.dump(state, f, indent=2)

            logger.info(f"Saved state to file: {len(state)} files")
        except IOError as exc:
            logger.error(f"Failed to save state to file: {exc}")

    def clear_state(self) -> None:
        """Clear saved state (useful for testing or reset)."""
        if self.use_database:
            db = next(get_db())
            try:
                workflows = db.query(Workflow).filter(
                    Workflow.type == "kb_sync"
                ).all()

                for workflow in workflows:
                    if workflow.workflow_data:
                        workflow.workflow_data.pop("last_sync_state", None)

                db.commit()
                logger.info("Cleared state from database")
            finally:
                db.close()
        else:
            if self.state_file and os.path.exists(self.state_file):
                os.remove(self.state_file)
                logger.info("Cleared state file")


# Global sync service instance
sync_service = SyncService()
