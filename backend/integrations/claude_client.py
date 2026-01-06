"""
Claude API client for generating postmortem content.

Implements circuit breaker pattern and timeout handling for reliability.
"""

from typing import Dict, Any, Optional
import os
import time
from datetime import datetime, timedelta
import anthropic

from backend.utils.logging import get_logger

logger = get_logger(__name__)


class CircuitBreaker:
    """
    Circuit breaker to prevent cascading failures.

    States:
    - CLOSED: Normal operation
    - OPEN: Failures exceeded threshold, reject requests
    - HALF_OPEN: Test if service recovered
    """

    def __init__(self, failure_threshold: int = 5, timeout: int = 60):
        """
        Initialize circuit breaker.

        Args:
            failure_threshold: Number of failures before opening circuit
            timeout: Seconds to wait before attempting recovery
        """
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failures = 0
        self.last_failure_time: Optional[datetime] = None
        self.state = "CLOSED"

    def call(self, func, *args, **kwargs):
        """
        Execute function with circuit breaker protection.

        Args:
            func: Function to execute
            *args: Positional arguments for function
            **kwargs: Keyword arguments for function

        Returns:
            Function result

        Raises:
            Exception: If circuit is open or function fails
        """
        if self.state == "OPEN":
            if self.last_failure_time and \
               datetime.now() - self.last_failure_time > timedelta(seconds=self.timeout):
                logger.info("Circuit breaker transitioning to HALF_OPEN")
                self.state = "HALF_OPEN"
            else:
                raise Exception("Circuit breaker is OPEN, rejecting request")

        try:
            result = func(*args, **kwargs)
            if self.state == "HALF_OPEN":
                logger.info("Circuit breaker transitioning to CLOSED")
                self.state = "CLOSED"
                self.failures = 0
            return result
        except Exception as exc:
            self.failures += 1
            self.last_failure_time = datetime.now()

            if self.failures >= self.failure_threshold:
                logger.warning(
                    f"Circuit breaker opening after {self.failures} failures"
                )
                self.state = "OPEN"

            raise exc


class ClaudeClient:
    """Claude API client for postmortem generation."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        timeout: int = 30,
        max_tokens: int = 4096
    ):
        """
        Initialize Claude API client.

        Args:
            api_key: Anthropic API key (defaults to ANTHROPIC_API_KEY env var)
            timeout: Request timeout in seconds
            max_tokens: Maximum tokens for response
        """
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY not set")

        self.timeout = timeout
        self.max_tokens = max_tokens
        self.client = anthropic.Anthropic(api_key=self.api_key)
        self.circuit_breaker = CircuitBreaker(failure_threshold=5, timeout=60)

        logger.info("Claude API client initialized")

    def generate_postmortem(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate postmortem sections using Claude API.

        Args:
            context: Incident context containing:
                - incident_id: Incident UUID
                - title: Incident title
                - description: Incident description
                - severity: Incident severity
                - created_at: Incident creation timestamp
                - resolved_at: Incident resolution timestamp
                - duration: Incident duration
                - metadata: Additional incident metadata

        Returns:
            Dict containing postmortem sections:
            - summary: Brief summary
            - timeline: List of timeline events
            - root_cause: Root cause analysis
            - impact: Impact description
            - resolution: Resolution description
            - lessons_learned: List of lessons learned

        Raises:
            Exception: If API call fails or circuit breaker is open
        """
        logger.info(f"Generating postmortem for incident {context['incident_id']}")

        prompt = self._build_postmortem_prompt(context)

        def api_call():
            """Make API call with timeout."""
            start_time = time.time()

            try:
                message = self.client.messages.create(
                    model="claude-haiku-4-5-20251001",#"claude-3-5-sonnet-20241022", model="claude-sonnet-4-5-20250929"
                    max_tokens=self.max_tokens,
                    temperature=0.7,
                    messages=[
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    timeout=self.timeout
                )

                elapsed = time.time() - start_time
                logger.info(f"Claude API call completed in {elapsed:.2f}s")

                # Parse response
                response_text = message.content[0].text
                sections = self._parse_postmortem_response(response_text)

                return sections

            except anthropic.APITimeoutError as exc:
                logger.error(f"Claude API timeout after {self.timeout}s")
                raise Exception(f"API timeout: {exc}")
            except anthropic.APIError as exc:
                logger.error(f"Claude API error: {exc}")
                raise Exception(f"API error: {exc}")

        # Execute with circuit breaker
        return self.circuit_breaker.call(api_call)

    def _build_postmortem_prompt(self, context: Dict[str, Any]) -> str:
        """
        Build prompt for postmortem generation.

        Args:
            context: Incident context

        Returns:
            Formatted prompt string
        """
        #TODO RBM
        #metadata_str = "\n".join(
        #    f"- {k}: {v}" for k, v in context.get("metadata", {}).items()
        #)

        metadata_str= ""

        prompt = f"""Generate a comprehensive postmortem for the following incident:

**Incident Details:**
- Title: {context['title']}
- Description: {context['description']}
- Severity: {context['severity']}
- Created: {context.get('created_at', 'Unknown')}
- Resolved: {context.get('resolved_at', 'Unknown')}
- Duration: {context.get('duration', 'Unknown')}

**Additional Context:**
{metadata_str if metadata_str else 'None'}

Please provide a detailed postmortem with the following sections in JSON format:

{{
  "summary": "Brief 2-3 sentence summary of the incident",
  "timeline": [
    {{"time": "HH:MM", "event": "Event description"}},
    ...
  ],
  "root_cause": "Detailed root cause analysis",
  "impact": "Description of impact on users and systems",
  "resolution": "How the incident was resolved",
  "lessons_learned": [
    "Lesson 1",
    "Lesson 2",
    ...
  ]
}}

Respond with valid JSON only, no additional text.
"""
        return prompt

    def _parse_postmortem_response(self, response_text: str) -> Dict[str, Any]:
        """
        Parse Claude API response into structured sections.

        Args:
            response_text: Raw response from Claude API

        Returns:
            Parsed postmortem sections

        Raises:
            ValueError: If response cannot be parsed
        """
        import json

        try:
            # Try to parse as JSON
            sections = json.loads(response_text)
            return sections
        except json.JSONDecodeError:
            # Try to extract JSON from markdown code block
            if "```json" in response_text:
                start = response_text.find("```json") + 7
                end = response_text.find("```", start)
                json_str = response_text[start:end].strip()
                sections = json.loads(json_str)
                return sections
            elif "```" in response_text:
                start = response_text.find("```") + 3
                end = response_text.find("```", start)
                json_str = response_text[start:end].strip()
                sections = json.loads(json_str)
                return sections
            else:
                raise ValueError("Could not parse postmortem response as JSON")


# Global client instance
claude_client = ClaudeClient()
