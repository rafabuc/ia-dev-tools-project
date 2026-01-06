"""
File scanning utilities for knowledge base synchronization.

Provides recursive directory scanning with file metadata tracking.
"""

import os
from typing import Dict, Any, List
from pathlib import Path
import fnmatch

from backend.utils.logging import get_logger

logger = get_logger(__name__)


class FileScanner:
    """Service for scanning directories and tracking file metadata."""

    def scan_directory(
        self,
        directory: str,
        pattern: str = "*.md",
        recursive: bool = True
    ) -> Dict[str, Any]:
        """
        Scan directory for files matching pattern.

        Args:
            directory: Path to directory to scan
            pattern: File pattern to match (e.g., "*.md")
            recursive: Whether to scan subdirectories recursively

        Returns:
            Dict containing:
            - files: List of file info dicts (path, mtime, size)
            - total_files: Total number of files found

        Raises:
            FileNotFoundError: If directory doesn't exist
        """
        logger.info(f"Scanning directory: {directory} (pattern={pattern}, recursive={recursive})")

        if not os.path.exists(directory):
            raise FileNotFoundError(f"Directory not found: {directory}")

        if not os.path.isdir(directory):
            raise ValueError(f"Not a directory: {directory}")

        files = []

        if recursive:
            # Recursive scan
            for root, dirs, filenames in os.walk(directory):
                for filename in filenames:
                    if fnmatch.fnmatch(filename, pattern):
                        file_path = os.path.join(root, filename)
                        file_info = self._get_file_info(file_path)
                        if file_info:
                            files.append(file_info)
        else:
            # Non-recursive scan
            for entry in os.listdir(directory):
                file_path = os.path.join(directory, entry)
                if os.path.isfile(file_path) and fnmatch.fnmatch(entry, pattern):
                    file_info = self._get_file_info(file_path)
                    if file_info:
                        files.append(file_info)

        logger.info(f"Found {len(files)} files in {directory}")

        return {
            "files": files,
            "total_files": len(files)
        }

    def _get_file_info(self, file_path: str) -> Dict[str, Any]:
        """
        Get metadata for a file.

        Args:
            file_path: Path to file

        Returns:
            Dict containing file metadata or None if file can't be accessed
        """
        try:
            stat = os.stat(file_path)
            return {
                "path": file_path,
                "mtime": stat.st_mtime,
                "size": stat.st_size
            }
        except (OSError, IOError) as exc:
            logger.warning(f"Could not access file {file_path}: {exc}")
            return None

    def get_file_hash(self, file_path: str) -> str:
        """
        Calculate hash of file content.

        Args:
            file_path: Path to file

        Returns:
            SHA256 hash of file content
        """
        import hashlib

        sha256 = hashlib.sha256()

        try:
            with open(file_path, 'rb') as f:
                while chunk := f.read(8192):
                    sha256.update(chunk)
            return sha256.hexdigest()
        except (OSError, IOError) as exc:
            logger.error(f"Failed to hash file {file_path}: {exc}")
            raise


# Global file scanner instance
file_scanner = FileScanner()
