"""
Celery configuration for DevOps Copilot workflows.

Configures:
- Redis broker and result backend
- Task serialization (JSON)
- Result expiration (7 days)
- Task acknowledgment settings
- Retry policy with exponential backoff
"""

import os
from typing import Dict, Any
from kombu import Queue


def get_celery_config() -> Dict[str, Any]:
    """
    Get Celery configuration from environment variables.

    Returns:
        Dict[str, Any]: Celery configuration dictionary
    """
    broker_url = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/1")
    result_backend = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/2")

    return {
        # Broker settings
        "broker_url": broker_url,
        "result_backend": result_backend,

        # Serialization
        "task_serializer": "json",
        "result_serializer": "json",
        "accept_content": ["json"],
        "timezone": "UTC",
        "enable_utc": True,

        # Result settings
        "result_expires": int(os.getenv("WORKFLOW_RESULT_EXPIRES_DAYS", "7")) * 86400,  # 7 days in seconds
        "result_extended": True,

        # Task execution
        "task_acks_late": True,  # At-least-once delivery
        "task_reject_on_worker_lost": True,
        "task_time_limit": int(os.getenv("WORKFLOW_TIMEOUT", "600")),  # 10 minutes
        "task_soft_time_limit": int(os.getenv("WORKFLOW_TIMEOUT", "600")) - 30,  # 9.5 minutes

        # Retry settings
        "task_autoretry_for": (Exception,),
        "task_retry_backoff": True,
        "task_retry_backoff_max": int(os.getenv("WORKFLOW_RETRY_BACKOFF_MAX", "60")),  # Max 60 seconds
        "task_retry_jitter": True,  # Add jitter to prevent thundering herd

        # Queue configuration
        "task_queues": (
            Queue("celery", routing_key="celery"),
            Queue("workflows", routing_key="workflows.#"),
        ),
        "task_default_queue": "celery",
        "task_default_routing_key": "celery",

        # Worker settings
        "worker_prefetch_multiplier": 4,
        "worker_max_tasks_per_child": 1000,


        # Para evitar warnings de seguridad
        "worker_hijack_root_logger": False,
        "broker_connection_retry_on_startup": True,
        
        # Task routing
        #"task_routes": {
        #    "workflows.*": {"queue": "workflows"},
        #    "backend.workflows.tasks.incident_tasks.*": {"queue": "workflows"},
        #},

    }
