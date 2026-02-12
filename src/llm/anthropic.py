"""Anthropic Claude LLM connector.

Provides text completions, structured output, and embeddings
via the Anthropic Messages API.

From ARCHITECTURE_PLAN.md Section 3.2 - primary provider for
entity extraction, reasoning, and interpretation tasks.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import TypeVar

from pydantic import BaseModel

from src.llm.base import BaseLLMConnector, LLMConfig

T = TypeVar("T", bound=BaseModel)

logger = logging.getLogger(__name__)


class AnthropicConnector(BaseLLMConnector):
    """Anthropic Claude API connector.

    Supports Claude models for text completion, structured output,
    and (via external embedding provider fallback) embeddings.
    """

    def __init__(self, config: LLMConfig | None = None) -> None:
        super().__init__(
            config
            or LLMConfig(
                provider="anthropic",
                model="claude-sonnet-4-20250514",
            )
        )
        self._client: object | None = None

    async def _ensure_client(self) -> object:
        """Lazily initialize the Anthropic client."""
        if self._client is not None:
            return self._client

        try:
            from anthropic import AsyncAnthropic

            self._client = AsyncAnthropic(
                api_key=self.config.api_key,
                timeout=self.config.timeout,
            )
        except ImportError:
            logger.warning(
                "anthropic package not installed. "
                "Install with: pip install anthropic"
            )
            raise

        return self._client

    async def complete(
        self,
        prompt: str,
        system_prompt: str | None = None,
        **kwargs: object,
    ) -> str:
        """Generate a text completion using Claude.

        Retries up to 3 times with exponential backoff on rate-limit (429)
        or transient server errors (5xx).
        """
        client = await self._ensure_client()

        messages = [{"role": "user", "content": prompt}]
        create_kwargs: dict = {
            "model": self.config.model,
            "max_tokens": self.config.max_tokens,
            "messages": messages,
            "temperature": self.config.temperature,
        }
        if system_prompt:
            create_kwargs["system"] = system_prompt

        max_retries = 3
        for attempt in range(max_retries + 1):
            try:
                response = await client.messages.create(**create_kwargs)  # type: ignore[union-attr]
                return response.content[0].text  # type: ignore[union-attr]
            except Exception as exc:
                exc_str = str(exc)
                is_retryable = (
                    "rate" in exc_str.lower()
                    or "429" in exc_str
                    or "529" in exc_str
                    or "overloaded" in exc_str.lower()
                    or "500" in exc_str
                    or "503" in exc_str
                )
                if is_retryable and attempt < max_retries:
                    wait = 2 ** (attempt + 1)  # 2s, 4s, 8s
                    logger.warning(
                        "Anthropic API error (attempt %d/%d), retrying in %ds: %s",
                        attempt + 1,
                        max_retries,
                        wait,
                        exc_str[:120],
                    )
                    await asyncio.sleep(wait)
                else:
                    raise

    async def complete_structured(
        self,
        prompt: str,
        output_schema: type[T],
        system_prompt: str | None = None,
        **kwargs: object,
    ) -> T:
        """Generate structured output matching a Pydantic schema.

        Instructs Claude to return JSON matching the schema, then
        parses and validates against the Pydantic model.
        """
        schema_json = json.dumps(output_schema.model_json_schema(), indent=2)
        structured_prompt = (
            f"{prompt}\n\n"
            f"Respond ONLY with valid JSON matching this schema:\n"
            f"```json\n{schema_json}\n```"
        )

        system = system_prompt or ""
        system += "\nYou must respond with valid JSON only. No markdown, no explanation."

        raw = await self.complete(structured_prompt, system_prompt=system.strip())

        # Strip markdown code fences if present
        text = raw.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:])
            if text.endswith("```"):
                text = text[:-3].strip()

        return output_schema.model_validate_json(text)

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Anthropic does not natively support embeddings.

        Raises NotImplementedError. Use the LLMRouter to route
        embedding requests to an OpenAI or Together connector.
        """
        raise NotImplementedError(
            "Anthropic Claude does not provide an embedding API. "
            "Use OpenAI or another provider for embeddings."
        )
