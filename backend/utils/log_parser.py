"""
Log parsing utilities for extracting error information from log files.

This module provides utilities for parsing log files to extract timestamps,
log levels, messages, and identify error patterns.
"""

import re
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path

from backend.utils.logging import get_logger

logger = get_logger(__name__)


class LogParseError(Exception):
    """Exception raised for log parsing errors."""
    pass


class LogParser:
    """
    Parser for analyzing log files and extracting error information.

    Supports common log formats:
    - Standard format: [YYYY-MM-DD HH:MM:SS] LEVEL Message
    - JSON logs
    - Custom formats (configurable)
    """

    # Common log patterns
    STANDARD_PATTERN = r'\[(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})\]\s+(\w+)\s+(.+)'
    ISO_PATTERN = r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})?)\s+(\w+)\s+(.+)'

    # Error patterns to detect
    ERROR_PATTERNS = [
        "error",
        "exception",
        "failed",
        "timeout",
        "unavailable",
        "connection refused",
        "permission denied",
        "not found",
        "500",
        "502",
        "503",
        "504"
    ]

    def __init__(self, log_format: str = "standard"):
        """
        Initialize log parser.

        Args:
            log_format: Log format ("standard", "iso", "json")
        """
        self.log_format = log_format

        if log_format == "standard":
            self.pattern = re.compile(self.STANDARD_PATTERN)
        elif log_format == "iso":
            self.pattern = re.compile(self.ISO_PATTERN)
        else:
            raise ValueError(f"Unsupported log format: {log_format}")

    def parse_file(self, file_path: str, max_lines: int = 10000) -> Dict[str, Any]:
        """
        Parse log file and extract error information.

        Args:
            file_path: Path to log file
            max_lines: Maximum number of lines to process

        Returns:
            Dict[str, Any]: {
                "errors_found": int,
                "timeline": [{"timestamp": "...", "level": "...", "message": "..."}],
                "patterns": ["pattern1", "pattern2"]
            }

        Raises:
            FileNotFoundError: If log file doesn't exist
            LogParseError: If log format is unrecognized
        """
        logger.info("parse_file_started", file_path=file_path)

        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Log file not found: {file_path}")

        timeline = []
        patterns_found = set()
        error_count = 0

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for i, line in enumerate(f):
                    if i >= max_lines:
                        logger.warning("parse_file_max_lines_reached", max_lines=max_lines)
                        break

                    line = line.strip()
                    if not line:
                        continue

                    # Parse line
                    entry = self._parse_line(line)
                    if not entry:
                        continue

                    # Check if it's an error
                    if entry["level"].upper() in ["ERROR", "CRITICAL", "FATAL"]:
                        error_count += 1
                        timeline.append(entry)

                        # Extract error patterns
                        message_lower = entry["message"].lower()
                        for pattern in self.ERROR_PATTERNS:
                            if pattern in message_lower:
                                patterns_found.add(pattern)

        except Exception as e:
            logger.error("parse_file_failed", file_path=file_path, error=str(e))
            raise LogParseError(f"Failed to parse log file: {str(e)}")

        result = {
            "errors_found": error_count,
            "timeline": timeline,
            "patterns": sorted(list(patterns_found))
        }

        logger.info(
            "parse_file_completed",
            file_path=file_path,
            errors_found=error_count,
            patterns=len(patterns_found)
        )

        return result

    def _parse_line(self, line: str) -> Optional[Dict[str, str]]:
        """
        Parse individual log line.

        Args:
            line: Log line to parse

        Returns:
            Optional[Dict[str, str]]: Parsed entry or None if unrecognized

        Example:
            Input: "[2025-12-29 10:30:00] ERROR Connection timeout"
            Output: {
                "timestamp": "2025-12-29 10:30:00",
                "level": "ERROR",
                "message": "Connection timeout"
            }
        """
        match = self.pattern.match(line)
        if not match:
            return None

        return {
            "timestamp": match.group(1),
            "level": match.group(2),
            "message": match.group(3)
        }

    def extract_error_summary(self, timeline: List[Dict[str, str]], max_length: int = 500) -> str:
        """
        Extract concise error summary from timeline.

        Args:
            timeline: Error timeline from parse_file
            max_length: Maximum summary length

        Returns:
            str: Error summary for semantic search
        """
        if not timeline:
            return "No errors found"

        # Take first 3 error messages
        messages = [entry["message"] for entry in timeline[:3]]
        summary = " | ".join(messages)

        if len(summary) > max_length:
            summary = summary[:max_length] + "..."

        return summary
