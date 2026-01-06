"""
Celery tasks for knowledge base synchronization workflow.

Tasks:
- scan_runbooks_dir: Scan runbook directory for files
- detect_changes: Detect added/modified/deleted files
- regenerate_embeddings: Regenerate embeddings for a file
- update_chromadb: Batch update ChromaDB with changes
- invalidate_cache: Invalidate caches for updated files
"""

from typing import Dict, Any, List
from datetime import datetime
from celery import Task

from backend.celery_app import app
from backend.utils.file_scanner import file_scanner
from backend.services.sync_service import sync_service
from backend.services.embedding_service import embedding_service
from backend.services.workflow_cache import WorkflowCache
from backend.utils.logging import get_logger

logger = get_logger(__name__)


@app.task(
    bind=True,
    max_retries=0,  # No retries for directory scanning
    name="kb_sync.scan_runbooks"
)
def scan_runbooks_dir(self: Task, runbooks_dir: str) -> Dict[str, Any]:
    """
    Scan runbook directory for files.

    Args:
        runbooks_dir: Path to runbooks directory

    Returns:
        Dict containing:
        - files: List of file info dicts (path, mtime)
        - total_files: Total number of files found
        - scan_timestamp: Scan timestamp in ISO format

    Raises:
        FileNotFoundError: If directory doesn't exist
    """
    logger.info(f"Scanning runbooks directory: {runbooks_dir}")

    try:
        # Scan directory for markdown files
        scan_result = file_scanner.scan_directory(
            directory=runbooks_dir,
            pattern="*.md",
            recursive=True
        )

        result = {
            "files": scan_result["files"],
            "total_files": scan_result["total_files"],
            "scan_timestamp": datetime.now().isoformat() + "Z"
        }

        logger.info(
            f"Scan complete: found {result['total_files']} files in {runbooks_dir}"
        )
        return result

    except FileNotFoundError as exc:
        logger.error(f"Runbooks directory not found: {runbooks_dir}")
        raise
    except Exception as exc:
        logger.error(f"Failed to scan runbooks directory: {exc}")
        raise


@app.task(
    bind=True,
    max_retries=0,  # No retries for change detection (deterministic)
    name="kb_sync.detect_changes"
)
def detect_changes(self: Task, current_files: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Detect changes in runbook files by comparing with previous state.

    Args:
        current_files: List of current file info dicts

    Returns:
        Dict containing:
        - added: List of newly added file paths
        - modified: List of modified file paths
        - deleted: List of deleted file paths
        - unchanged: List of unchanged file paths
        - total_changes: Total number of changes
    """
    logger.info(f"Detecting changes in {len(current_files)} files")

    try:
        # Detect changes using sync service
        changes = sync_service.detect_changes(current_files)

        logger.info(
            f"Changes detected: {changes['total_changes']} total "
            f"({len(changes['added'])} added, {len(changes['modified'])} modified, "
            f"{len(changes['deleted'])} deleted)"
        )

        return changes

    except Exception as exc:
        logger.error(f"Failed to detect changes: {exc}")
        raise


@app.task(
    bind=True,
    max_retries=3,
    name="kb_sync.regenerate_embeddings"
)
def regenerate_embeddings(self: Task, file_path: str) -> Dict[str, Any]:
    """
    Regenerate embeddings for a runbook file.

    Args:
        file_path: Path to runbook file

    Returns:
        Dict containing:
        - file_path: File path
        - embedding_id: UUID of the embedding
        - chunks: Number of chunks created
        - status: "embedded" or "failed"

    Raises:
        FileNotFoundError: If file doesn't exist
        Exception: If embedding fails (will retry)
    """
    logger.info(f"Regenerating embeddings for: {file_path}")

    try:
        # Read file content
        with open(file_path, 'r', encoding='utf-8') as f:
            document = f.read()

        if not document.strip():
            raise ValueError(f"File is empty: {file_path}")

        # Generate embedding using embedding service
        # For runbooks, use "runbooks" collection
        embedding_result = embedding_service.embed_document(
            incident_id=file_path,  # Use file path as ID for runbooks
            document=document,
            metadata={
                "document_type": "runbook",
                "file_path": file_path,
                "indexed_at": datetime.now().isoformat()
            }
        )

        result = {
            "file_path": file_path,
            "embedding_id": embedding_result["embedding_id"],
            "chunks": embedding_result.get("chunks", 1),
            "status": "embedded"
        }

        logger.info(
            f"Successfully regenerated embeddings for {file_path} "
            f"({result['chunks']} chunks)"
        )
        return result

    except FileNotFoundError as exc:
        logger.error(f"File not found: {file_path}")
        raise
    except Exception as exc:
        logger.error(f"Failed to regenerate embeddings for {file_path}: {exc}")
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)


@app.task(
    bind=True,
    max_retries=3,
    name="kb_sync.update_chromadb"
)
def update_chromadb(
    self: Task,
    embeddings: List[Dict[str, Any]],
    deleted_files: List[str] = None
) -> Dict[str, Any]:
    """
    Batch update ChromaDB with new/modified embeddings and deletions.

    Args:
        embeddings: List of embedding dicts from regenerate_embeddings
        deleted_files: List of file paths to delete

    Returns:
        Dict containing:
        - updated_count: Number of embeddings updated
        - deleted_count: Number of embeddings deleted
        - status: "success", "partial", or "failed"

    Raises:
        Exception: If ChromaDB operation fails (will retry)
    """
    deleted_files = deleted_files or []
    logger.info(
        f"Updating ChromaDB: {len(embeddings)} updates, "
        f"{len(deleted_files)} deletions"
    )

    try:
        # Batch update ChromaDB
        result = embedding_service.batch_update(
            embeddings=embeddings,
            deleted_files=deleted_files
        )

        logger.info(
            f"ChromaDB update complete: {result['updated_count']} updated, "
            f"{result['deleted_count']} deleted"
        )
        return result

    except Exception as exc:
        logger.error(f"Failed to update ChromaDB: {exc}")
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)


@app.task(
    bind=True,
    max_retries=3,
    name="kb_sync.invalidate_cache"
)
def invalidate_cache(self: Task, cache_keys: List[str]) -> Dict[str, Any]:
    """
    Invalidate caches for updated runbooks.

    Args:
        cache_keys: List of cache keys to invalidate

    Returns:
        Dict containing:
        - invalidated_keys: Number of keys invalidated
        - status: "success" or "failed"

    Raises:
        Exception: If cache invalidation fails (will retry)
    """
    logger.info(f"Invalidating {len(cache_keys)} cache keys")

    try:
        # Invalidate cache using workflow cache
        cache = WorkflowCache()
        result = cache.invalidate_keys(cache_keys)

        logger.info(f"Cache invalidation complete: {result['invalidated_keys']} keys")
        return result

    except Exception as exc:
        logger.error(f"Failed to invalidate cache: {exc}")
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)
