# -*- coding: utf-8 -*-
"""OpenAI-compatible chat client (DeepSeek by default).

The app is fully usable without any API key: every caller treats
LLMUnavailable as "fall back to the deterministic path" rather than as an error.
That keeps a classroom laptop working on a locked-down network.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any

from . import zh

__all__ = [
    'LLMConfig',
    'LLMClient',
    'LLMUnavailable',
    'default_client',
    'extract_json_object',
]

DEFAULT_BASE_URL = 'https://api.deepseek.com'
DEFAULT_MODEL = 'deepseek-chat'

#: Checked in order; the first non-empty value wins.
API_KEY_VARS = (
    'READEXPRESS_LLM_API_KEY',
    'DEEPSEEK_API_KEY',
    'OPENAI_API_KEY',
)
BASE_URL_VARS = (
    'READEXPRESS_LLM_BASE_URL',
    'DEEPSEEK_BASE_URL',
    'OPENAI_BASE_URL',
)
MODEL_VARS = (
    'READEXPRESS_LLM_MODEL',
    'DEEPSEEK_MODEL',
    'OPENAI_MODEL',
)

SYSTEM_PROMPT = (
    '你是一位專業、耐心的臺灣國小國語科助教。'
    '你的學生是六年級學生，請用溫暖、簡潔、鼓勵的語氣回答，'
    '句子不要太長，避免困難的成人詞彙。'
)

_FENCE = chr(96)


class LLMUnavailable(RuntimeError):
    """Raised when no usable LLM backend is configured or the call failed."""


def _first_env(names: tuple[str, ...], default: str = '') -> str:
    for name in names:
        value = os.environ.get(name, '').strip()
        if value:
            return value
    return default


@dataclass(frozen=True)
class LLMConfig:
    api_key: str = ''
    base_url: str = DEFAULT_BASE_URL
    model: str = DEFAULT_MODEL
    temperature: float = 0.3
    max_tokens: int = 900
    timeout: float = 30.0

    @property
    def configured(self) -> bool:
        return bool(self.api_key)

    @classmethod
    def from_env(cls) -> 'LLMConfig':
        return cls(
            api_key=_first_env(API_KEY_VARS),
            base_url=_first_env(BASE_URL_VARS, DEFAULT_BASE_URL),
            model=_first_env(MODEL_VARS, DEFAULT_MODEL),
            temperature=float(os.environ.get('READEXPRESS_LLM_TEMPERATURE', '0.3')),
            max_tokens=int(os.environ.get('READEXPRESS_LLM_MAX_TOKENS', '900')),
            timeout=float(os.environ.get('READEXPRESS_LLM_TIMEOUT', '30')),
        )

    def redacted(self) -> dict[str, Any]:
        """Config summary safe to log or show in the UI."""
        if not self.api_key:
            shown = ''
        elif len(self.api_key) > 12:
            shown = self.api_key[:6] + '…' + self.api_key[-4:]
        else:
            shown = 'set'
        return {
            'configured': self.configured,
            'base_url': self.base_url,
            'model': self.model,
            'api_key': shown,
        }


@dataclass
class LLMClient:
    """Thin wrapper over the OpenAI SDK with lazy import and graceful failure."""

    config: LLMConfig = field(default_factory=LLMConfig.from_env)
    _client: Any = field(default=None, repr=False)

    @property
    def available(self) -> bool:
        return self.config.configured

    def status(self) -> dict[str, Any]:
        return {'available': self.available, **self.config.redacted()}

    def _ensure_client(self) -> Any:
        if self._client is not None:
            return self._client
        if not self.available:
            raise LLMUnavailable('no API key configured')
        try:
            from openai import OpenAI
        except ImportError as exc:  # pragma: no cover - dependency guard
            raise LLMUnavailable(f'openai package unavailable: {exc}') from exc
        self._client = OpenAI(
            api_key=self.config.api_key,
            base_url=self.config.base_url,
            timeout=self.config.timeout,
        )
        return self._client

    def complete(
        self,
        prompt: str,
        system: str = SYSTEM_PROMPT,
        json_mode: bool = False,
    ) -> str:
        """Return the assistant's reply text, in Traditional Chinese.

        Raises LLMUnavailable on any failure — callers decide what to do,
        because "the model is down" is a normal state for this app.
        """
        client = self._ensure_client()
        messages: list[dict[str, str]] = []
        if system:
            messages.append({'role': 'system', 'content': system})
        messages.append({'role': 'user', 'content': prompt})

        kwargs: dict[str, Any] = {
            'model': self.config.model,
            'messages': messages,
            'temperature': self.config.temperature,
            'max_tokens': self.config.max_tokens,
        }
        if json_mode:
            kwargs['response_format'] = {'type': 'json_object'}

        try:
            response = client.chat.completions.create(**kwargs)
            content = response.choices[0].message.content or ''
        except Exception as exc:  # noqa: BLE001 - any backend error degrades
            raise LLMUnavailable(f'{type(exc).__name__}: {exc}') from exc
        # The single seam where model output becomes app text. Converting here
        # rather than at each display site covers both callers — the evaluator's
        # JSON reply and the reflection's prose — and it runs *before*
        # extract_json_object() parses, so the feedback inside the JSON is
        # Traditional by the time anything reads it. Authored corpus text never
        # passes through here; it is already Traditional and conversion is not
        # free. to_traditional() cannot raise, so a missing OpenCC costs the
        # conversion, never the reply.
        return zh.to_traditional(content.strip())


def extract_json_object(text: str) -> dict[str, Any]:
    """Pull the first JSON object out of a model reply.

    Small models often wrap JSON in prose or a code fence even when asked not
    to, so we scan for balanced braces rather than trusting the whole reply.
    """
    cleaned = text.strip()
    if cleaned.startswith(_FENCE):
        cleaned = cleaned.strip(_FENCE).strip()
        if cleaned.lower().startswith('json'):
            cleaned = cleaned[4:].strip()
    start = cleaned.find('{')
    if start == -1:
        raise ValueError('no JSON object found in model reply')
    depth = 0
    for pos in range(start, len(cleaned)):
        char = cleaned[pos]
        if char == '{':
            depth += 1
        elif char == '}':
            depth -= 1
            if depth == 0:
                return json.loads(cleaned[start: pos + 1])
    raise ValueError('unterminated JSON object in model reply')


_shared_client: LLMClient | None = None


def default_client() -> LLMClient:
    """Process-wide client, configured from the environment on first use."""
    global _shared_client
    if _shared_client is None:
        _shared_client = LLMClient()
    return _shared_client
