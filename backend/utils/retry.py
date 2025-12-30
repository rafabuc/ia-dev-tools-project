"""
Retry utilities with exponential backoff and jitter.
"""

import random
import time
from typing import Callable, Any, Optional

def exponential_backoff_with_jitter(
    func: Callable,
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    jitter: bool = True,
    exceptions: tuple = (Exception,),
    on_retry: Optional[Callable[[int, float], None]] = None
) -> Any:
    """
    Retry a function with exponential backoff and optional jitter.

    Args:
        func: Function to retry
        max_retries: Maximum number of retry attempts
        base_delay: Base delay in seconds
        max_delay: Maximum delay in seconds
        jitter: Whether to add random jitter to delays
        exceptions: Exceptions that trigger a retry
        on_retry: Callback invoked on each retry (retry_count, delay)

    Returns:
        Any: The result of the function

    Raises:
        Exception: The last exception if all retries fail
    """
    retry_count = 0
    last_exception = None

    while retry_count <= max_retries:
        try:
            return func()
        except exceptions as e:
            last_exception = e
            retry_count += 1

            if retry_count > max_retries:
                break

            # Calculate delay with exponential backoff
            delay = min(base_delay * (2 ** (retry_count - 1)), max_delay)

            # Add jitter (randomization)
            if jitter:
                delay = random.uniform(0.5 * delay, 1.5 * delay)

            # Call on_retry callback if provided
            if on_retry:
                on_retry(retry_count, delay)

            # Wait before retrying
            time.sleep(delay)

    # All retries failed
    raise last_exception

class RetryPolicy:
    """Configuration for retry behavior."""

    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        jitter: bool = True,
        retry_on: tuple = (Exception,)
    ):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.jitter = jitter
        self.retry_on = retry_on

    def apply(self, func: Callable) -> Any:
        """Apply retry policy to a function."""
        return exponential_backoff_with_jitter(
            func=func,
            max_retries=self.max_retries,
            base_delay=self.base_delay,
            max_delay=self.max_delay,
            jitter=self.jitter,
            exceptions=self.retry_on
        )