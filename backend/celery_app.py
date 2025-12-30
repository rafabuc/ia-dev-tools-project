"""
Celery application initialization for DevOps Copilot workflows.

This module configures the Celery application with Redis broker and result backend,
registers task modules, and sets up retry configuration with exponential backoff.
"""

from celery import Celery
from backend.config.celery_config import get_celery_config

# Initialize Celery application
app = Celery("devops_copilot")

# Load configuration
app.config_from_object(get_celery_config())

# Auto-discover tasks from workflows package
app.autodiscover_tasks(["backend.workflows.tasks"])


if __name__ == "__main__":
    app.start()
