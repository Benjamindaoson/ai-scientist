"""LLM Gateway for AI Scientist.

Provides interface for connecting to various LLM providers.
"""
from __future__ import annotations

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class ModelResponse:
    """Response from LLM model."""
    content: str
    model: str
    usage: dict | None = None
    cost: float = 0.0
    latency_ms: float = 0.0


class BaseGateway(ABC):
    """Base class for LLM gateways."""

    @abstractmethod
    def generate(self, prompt: str, **kwargs) -> str:
        """Generate response from LLM."""
        pass

    @abstractmethod
    async def generate_async(self, prompt: str, **kwargs) -> str:
        """Async version of generate."""
        pass

    def generate_batch(self, prompts: list[str], **kwargs) -> list[str]:
        """Generate responses for multiple prompts."""
        return [self.generate(p, **kwargs) for p in prompts]


class ClaudeGateway(BaseGateway):
    """Gateway for Anthropic Claude API."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "claude-sonnet-4-20250514",
        max_tokens: int = 4096,
        temperature: float = 0.7,
        base_url: str | None = None,
    ):
        """Initialize Claude gateway.

        Args:
            api_key: Anthropic API key (defaults to ANTHROPIC_API_KEY env var)
            model: Claude model to use
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature
            base_url: Optional relay/proxy URL
        """
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.base_url = base_url or os.environ.get("ANTHROPIC_BASE_URL", "")

    def generate(self, prompt: str, **kwargs) -> str:
        """Generate response from Claude."""
        import anthropic

        client = anthropic.Anthropic(
            api_key=self.api_key or None,
            base_url=self.base_url or None,
        )

        response = client.messages.create(
            model=kwargs.get("model", self.model),
            max_tokens=kwargs.get("max_tokens", self.max_tokens),
            temperature=kwargs.get("temperature", self.temperature),
            messages=[{"role": "user", "content": prompt}],
        )

        return response.content[0].text

    async def generate_async(self, prompt: str, **kwargs) -> str:
        """Async version of generate."""
        import anthropic

        client = anthropic.AsyncAnthropic(
            api_key=self.api_key or None,
            base_url=self.base_url or None,
        )

        response = await client.messages.create(
            model=kwargs.get("model", self.model),
            max_tokens=kwargs.get("max_tokens", self.max_tokens),
            temperature=kwargs.get("temperature", self.temperature),
            messages=[{"role": "user", "content": prompt}],
        )

        return response.content[0].text


class ClaudeRelayGateway(BaseGateway):
    """Gateway for Claude relay/proxy (OpenAI-compatible API format)."""

    def __init__(
        self,
        relay_url: str = "http://localhost:8080",
        api_key: str | None = None,
        model: str = "claude-sonnet-4-20250514",
        max_tokens: int = 4096,
        temperature: float | None = None,
    ):
        """Initialize Claude relay gateway.

        Args:
            relay_url: URL of the Claude relay/proxy server
            api_key: Optional API key for relay authentication
            model: Model identifier to use
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature (optional for some relays)
        """
        self.relay_url = relay_url.rstrip("/")
        self.api_key = api_key or ""
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature

    def generate(self, prompt: str, **kwargs) -> str:
        """Generate response via relay (OpenAI-compatible format)."""
        import json
        import urllib.request
        import urllib.error

        # Build messages in OpenAI format
        messages = [{"role": "user", "content": prompt}]

        payload = {
            "model": kwargs.get("model", self.model),
            "messages": messages,
            "max_tokens": kwargs.get("max_tokens", self.max_tokens),
        }

        # Only add temperature if specified
        temp = kwargs.get("temperature", self.temperature)
        if temp is not None:
            payload["temperature"] = temp

        headers = {
            "Content-Type": "application/json",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        req = urllib.request.Request(
            f"{self.relay_url}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=300) as response:
                result = json.loads(response.read().decode("utf-8"))
                # OpenAI format: result["choices"][0]["message"]["content"]
                if "choices" in result:
                    return result["choices"][0]["message"]["content"]
                return result.get("content", result.get("response", ""))
        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8") if e.fp else ""
            raise RuntimeError(f"Relay error {e.code}: {error_body}")
        except Exception as e:
            raise RuntimeError(f"Relay request failed: {e}")

    async def generate_async(self, prompt: str, **kwargs) -> str:
        """Async version of generate via relay."""
        import aiohttp
        import json

        messages = [{"role": "user", "content": prompt}]

        payload = {
            "model": kwargs.get("model", self.model),
            "messages": messages,
            "max_tokens": kwargs.get("max_tokens", self.max_tokens),
        }

        temp = kwargs.get("temperature", self.temperature)
        if temp is not None:
            payload["temperature"] = temp

        headers = {
            "Content-Type": "application/json",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.relay_url}/chat/completions",
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=300),
            ) as response:
                if response.status != 200:
                    error_body = await response.text()
                    raise RuntimeError(f"Relay error {response.status}: {error_body}")
                result = await response.json()
                if "choices" in result:
                    return result["choices"][0]["message"]["content"]
                return result.get("content", result.get("response", ""))


class MockGateway(BaseGateway):
    """Mock gateway for testing without API access."""

    def __init__(
        self,
        responses: dict[str, str] | None = None,
        default_response: str = "This is a mock response.",
    ):
        """Initialize mock gateway.

        Args:
            responses: Dict mapping prompt patterns to responses
            default_response: Default response for unmatched prompts
        """
        self.responses = responses or {}
        self.default_response = default_response

    def generate(self, prompt: str, **kwargs) -> str:
        """Generate mock response."""
        # Try to find a matching response
        for pattern, response in self.responses.items():
            if pattern.lower() in prompt.lower():
                return response
        return self.default_response

    async def generate_async(self, prompt: str, **kwargs) -> str:
        """Async version of generate."""
        return self.generate(prompt, **kwargs)


def create_gateway(
    provider: str = "auto",
    **kwargs,
) -> BaseGateway:
    """Create a gateway based on environment and configuration.

    Args:
        provider: Provider name ("anthropic", "relay", "mock", or "auto")
        **kwargs: Additional arguments for the gateway

    Returns:
        Configured gateway instance
    """
    if provider == "mock":
        return MockGateway(**kwargs)

    if provider == "anthropic":
        return ClaudeGateway(**kwargs)

    if provider == "relay":
        return ClaudeRelayGateway(**kwargs)

    # Auto-detect: check environment
    if os.environ.get("ANTHROPIC_API_KEY"):
        return ClaudeGateway(**kwargs)

    if os.environ.get("CLAUDE_RELAY_URL"):
        return ClaudeRelayGateway(
            relay_url=os.environ["CLAUDE_RELAY_URL"],
            api_key=os.environ.get("CLAUDE_RELAY_KEY", ""),
            **kwargs,
        )

    # Fallback to mock
    return MockGateway(
        default_response="[Mock] Configure ANTHROPIC_API_KEY or CLAUDE_RELAY_URL for real responses."
    )
