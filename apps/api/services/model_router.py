"""Model router for LLM calls with provider abstraction."""

import os
from collections.abc import AsyncGenerator
from functools import lru_cache
from typing import TypedDict

import anthropic
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

from shared.config import load_model_router_config
from shared.config.schemas import ModelRouterConfig

logger = structlog.get_logger()


class GenerationSettings(TypedDict, total=False):
    """Type-safe generation settings for LLM calls."""

    max_tokens: int
    temperature: float


class ModelRouter:
    """Routes LLM calls to configured providers and models.

    All LLM calls go through this router, enabling:
    - Provider/model switching via config
    - Fallback handling
    - Token counting and logging
    - Consistent error handling
    """

    def __init__(self, config: ModelRouterConfig) -> None:
        """Initialize the model router.

        Args:
            config: Model router configuration
        """
        self.config = config
        self._anthropic_client: anthropic.Anthropic | None = None
        self._anthropic_async_client: anthropic.AsyncAnthropic | None = None
        self._init_clients()

    def _init_clients(self) -> None:
        """Initialize provider clients."""
        for provider_name, provider_config in self.config.providers.items():
            if provider_name == "anthropic":
                api_key = os.environ.get(provider_config.api_key_env)
                if api_key:
                    self._anthropic_client = anthropic.Anthropic(api_key=api_key)
                    self._anthropic_async_client = anthropic.AsyncAnthropic(
                        api_key=api_key
                    )

    def _get_route(self, task: str) -> tuple[str, str, GenerationSettings]:
        """Get the provider, model, and settings for a task.

        Args:
            task: Task type (orchestrator, drafting, extraction, qc, research)

        Returns:
            Tuple of (provider, model, settings)
        """
        route = self.config.routes.get(task)
        if route:
            return (
                route.provider,
                route.model,
                {"max_tokens": route.max_tokens, "temperature": route.temperature},
            )

        # Use defaults
        return (
            self.config.default_provider,
            self.config.default_model,
            {"max_tokens": 4096, "temperature": 0.3},
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
    )
    async def generate(
        self,
        task: str,
        messages: list[dict[str, str]],
        system: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> str:
        """Generate a response from the LLM.

        Args:
            task: Task type for routing
            messages: List of message dicts with 'role' and 'content'
            system: Optional system prompt
            max_tokens: Override max tokens from config
            temperature: Override temperature from config

        Returns:
            Generated response text

        Raises:
            ValueError: If provider is unknown
            RuntimeError: If provider client not initialized
        """
        provider, model, settings = self._get_route(task)
        if max_tokens is not None:
            settings["max_tokens"] = max_tokens
        if temperature is not None:
            settings["temperature"] = temperature

        logger.info(
            "Generating LLM response",
            task=task,
            provider=provider,
            model=model,
        )

        if provider == "anthropic":
            return await self._generate_anthropic(model, messages, system, settings)

        raise ValueError(f"Unknown provider: {provider}")

    async def _generate_anthropic(
        self,
        model: str,
        messages: list[dict[str, str]],
        system: str | None,
        settings: GenerationSettings,
    ) -> str:
        """Generate response using Anthropic API.

        Args:
            model: Model ID
            messages: Conversation messages
            system: System prompt
            settings: Generation settings

        Returns:
            Generated text

        Raises:
            RuntimeError: If Anthropic client not initialized
        """
        if not self._anthropic_async_client:
            raise RuntimeError("Anthropic client not initialized")

        response = await self._anthropic_async_client.messages.create(
            model=model,
            messages=messages,
            system=system or "",
            max_tokens=settings.get("max_tokens", 4096),
            temperature=settings.get("temperature", 0.3),
        )

        return response.content[0].text

    async def stream(
        self,
        task: str,
        messages: list[dict[str, str]],
        system: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> AsyncGenerator[str, None]:
        """Stream a response from the LLM.

        Args:
            task: Task type for routing
            messages: List of message dicts
            system: Optional system prompt
            max_tokens: Override max tokens from config
            temperature: Override temperature from config

        Yields:
            Response text chunks

        Raises:
            ValueError: If provider is unknown
        """
        provider, model, settings = self._get_route(task)
        if max_tokens is not None:
            settings["max_tokens"] = max_tokens
        if temperature is not None:
            settings["temperature"] = temperature

        if provider == "anthropic":
            async for chunk in self._stream_anthropic(model, messages, system, settings):
                yield chunk
        else:
            raise ValueError(f"Unknown provider: {provider}")

    async def _stream_anthropic(
        self,
        model: str,
        messages: list[dict[str, str]],
        system: str | None,
        settings: GenerationSettings,
    ) -> AsyncGenerator[str, None]:
        """Stream response using Anthropic API.

        Args:
            model: Model ID
            messages: Conversation messages
            system: System prompt
            settings: Generation settings

        Yields:
            Text chunks

        Raises:
            RuntimeError: If Anthropic client not initialized
        """
        if not self._anthropic_async_client:
            raise RuntimeError("Anthropic client not initialized")

        async with self._anthropic_async_client.messages.stream(
            model=model,
            messages=messages,
            system=system or "",
            max_tokens=settings.get("max_tokens", 4096),
            temperature=settings.get("temperature", 0.3),
        ) as stream:
            async for text in stream.text_stream:
                yield text


@lru_cache
def get_model_router() -> ModelRouter:
    """Get cached model router instance."""
    config = load_model_router_config()
    return ModelRouter(config)
