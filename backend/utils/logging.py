"""
Structured logging utilities with correlation IDs.

This module provides structured logging configuration using structlog
with correlation ID tracking for workflow execution tracing.
"""

import os
import uuid
import logging
from typing import Optional, Dict, Any
from contextvars import ContextVar

import structlog
from structlog.types import EventDict, Processor


# Context variable for correlation ID (thread-safe)
correlation_id_var: ContextVar[Optional[str]] = ContextVar("correlation_id", default=None)


def set_correlation_id(correlation_id: Optional[str] = None) -> str:
    """
    Set correlation ID for current context.

    Args:
        correlation_id: Optional correlation ID (generates new UUID if not provided)

    Returns:
        str: The correlation ID that was set
    """
    if correlation_id is None:
        correlation_id = str(uuid.uuid4())
    correlation_id_var.set(correlation_id)
    return correlation_id


def get_correlation_id() -> Optional[str]:
    """
    Get correlation ID for current context.

    Returns:
        Optional[str]: Correlation ID or None if not set
    """
    return correlation_id_var.get()


def add_correlation_id(logger: Any, method_name: str, event_dict: EventDict) -> EventDict:
    """
    Add correlation ID to log event.

    This is a structlog processor that adds the correlation ID to every log entry.

    Args:
        logger: Logger instance
        method_name: Log method name
        event_dict: Event dictionary

    Returns:
        EventDict: Event dictionary with correlation_id added
    """
    correlation_id = get_correlation_id()
    if correlation_id:
        event_dict["correlation_id"] = correlation_id
    return event_dict


def configure_logging(log_level: Optional[str] = None) -> None:
    """
    Configure structured logging with structlog.

    Args:
        log_level: Optional log level (defaults to env LOG_LEVEL or INFO)
    """
    level = log_level or os.getenv("LOG_LEVEL", "INFO")

    # Configure standard logging
    logging.basicConfig(
        format="%(message)s",
        level=getattr(logging, level.upper()),
    )

    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            add_correlation_id,  # Add correlation ID processor
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """
    Get a structured logger instance.

    Args:
        name: Logger name (typically __name__)

    Returns:
        structlog.stdlib.BoundLogger: Configured logger instance

    Example:
        logger = get_logger(__name__)
        logger.info("workflow_started", workflow_id=workflow.id, type=workflow.type)
    """
    return structlog.get_logger(name)


def log_workflow_event(
    logger: structlog.stdlib.BoundLogger,
    event: str,
    workflow_id: uuid.UUID,
    **kwargs: Any
) -> None:
    """
    Log a workflow event with standard fields.

    Args:
        logger: Structured logger instance
        event: Event name (e.g., "workflow_started", "step_completed")
        workflow_id: Workflow identifier
        **kwargs: Additional fields to log
    """
    logger.info(
        event,
        workflow_id=str(workflow_id),
        **kwargs
    )


# Initialize logging on module import
configure_logging()
