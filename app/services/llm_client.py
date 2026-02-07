"""LLM client wrapper using Meitu model router (OpenAI-compatible)."""

import base64
import json
import re
from typing import Optional

import openai
from openai import AsyncOpenAI

from app.config import get_settings


class LLMClient:
    """Client for interacting with Meitu model router."""

    def __init__(self):
        """Initialize the LLM client with settings."""
        settings = get_settings()
        self._api_key = (settings.llm_api_key or "").strip()
        # Basic local-dev fallback:
        # - If user hasn't set a real key yet, we enable a mock mode so the
        #   pipeline + web UI can run end-to-end without external calls.
        self.mock_mode = (self._api_key == "" or self._api_key == "your_api_key_here")
        self.client = AsyncOpenAI(
            base_url=settings.llm_base_url,
            api_key=settings.llm_api_key,
        )
        self.model = settings.llm_model
        self.vision_model = settings.llm_vision_model

    def _mock_scene_classification(self) -> str:
        return json.dumps(
            {
                "primary_scene": "other",
                "secondary_attributes": ["unknown lighting", "unknown composition"],
                "ai_likelihood": 0.5,
            },
            ensure_ascii=False,
        )

    def _mock_fake_signals(self) -> str:
        return json.dumps(
            {
                "fake_signals": [
                    {"signal": "Unable to run vision analysis in mock mode; no artifacts detected.", "severity": "low"}
                ]
            },
            ensure_ascii=False,
        )

    def _mock_strategy(self) -> str:
        return json.dumps(
            {
                "goal": "Introduce subtle imperfections to reduce synthetic smoothness while preserving identity and composition",
                "priority": "very_low",
                "operations": [
                    {
                        "module": "noise",
                        "action": "Add subtle sensor-like noise concentrated in shadows to reduce overly clean gradients",
                        "strength": "very_low",
                        "locality": "global",
                    },
                    {
                        "module": "texture",
                        "action": "Introduce slight micro-variation in flat regions to reduce over-uniformity",
                        "strength": "very_low",
                        "locality": "local",
                    },
                ],
                "constraints": [
                    "Do not change identity, composition, or intent",
                    "Do not introduce stylization or cinematic grading",
                    "Do not change geometry or add/remove objects",
                ],
            },
            ensure_ascii=False,
        )

    async def chat_completion(
        self,
        messages: list[dict],
        model: Optional[str] = None,
        temperature: float = 0,
        max_tokens: int = 2048,
        response_format: Optional[dict] = None,
    ) -> str:
        """
        Send a chat completion request.

        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Model to use (defaults to configured model)
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response
            response_format: Optional response format specification

        Returns:
            The assistant's response content
        """
        if self.mock_mode:
            # Strategy generator uses text-only chat completion.
            return self._mock_strategy()

        kwargs = {
            "model": model or self.model,
            "messages": messages,
            "max_tokens": max_tokens,
        }

        # Only add temperature if explicitly set to non-default value
        # Some models don't support temperature parameter
        if temperature > 0 and temperature != 1.0:
            kwargs["temperature"] = temperature

        if response_format:
            kwargs["response_format"] = response_format

        response = await self.client.chat.completions.create(**kwargs)
        return response.choices[0].message.content

    async def chat_completion_with_image(
        self,
        prompt: str,
        image_base64: str,
        model: Optional[str] = None,
        temperature: float = 0,
        max_tokens: int = 2048,
        system_prompt: Optional[str] = None,
    ) -> str:
        """
        Send a chat completion request with an image.

        Args:
            prompt: The text prompt to accompany the image
            image_base64: Base64-encoded image data
            model: Model to use (defaults to configured vision model)
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response
            system_prompt: Optional system prompt

        Returns:
            The assistant's response content
        """
        if self.mock_mode:
            prompt_l = (prompt or "").lower()
            if "scene classification" in prompt_l or "primary scene type" in prompt_l:
                return self._mock_scene_classification()
            return self._mock_fake_signals()

        messages = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        # Construct message with image
        user_content = [
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{image_base64}"
                }
            },
            {
                "type": "text",
                "text": prompt
            }
        ]

        messages.append({"role": "user", "content": user_content})

        kwargs = {
            "model": model or self.vision_model,
            "messages": messages,
            "max_tokens": max_tokens,
        }

        # Only add temperature if explicitly set to non-default value
        if temperature > 0 and temperature != 1.0:
            kwargs["temperature"] = temperature

        response = await self.client.chat.completions.create(**kwargs)
        return response.choices[0].message.content

    def _extract_first_json_object(self, text: str) -> Optional[str]:
        """Find first complete JSON object (from first '{' to matching '}')."""
        start = text.find("{")
        if start == -1:
            return None
        depth = 0
        in_string = False
        escape = False
        quote = None
        i = start
        while i < len(text):
            c = text[i]
            if escape:
                escape = False
                i += 1
                continue
            if c == "\\" and in_string:
                escape = True
                i += 1
                continue
            if in_string:
                if c == quote:
                    in_string = False
                i += 1
                continue
            if c in ('"', "'"):
                in_string = True
                quote = c
                i += 1
                continue
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    return text[start : i + 1]
            i += 1
        return None

    async def parse_json_response(self, response: str) -> dict:
        """
        Parse JSON from LLM response, handling markdown code blocks and truncated output.

        Args:
            response: Raw response string from LLM

        Returns:
            Parsed JSON as dictionary. On unrecoverable parse failure, returns a safe default
            so the pipeline can continue (e.g. scene classification fallback).
        """
        # Remove markdown code blocks if present
        content = response.strip()
        if content.startswith("```json"):
            content = content[7:]
        elif content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()

        # Try direct parse first
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass

        # Try to extract a single JSON object (handles trailing text or truncated output)
        extracted = self._extract_first_json_object(content)
        if extracted:
            try:
                return json.loads(extracted)
            except json.JSONDecodeError as e:
                raise ValueError(
                    f"LLM 返回的 JSON 无效或截断，解析失败: {e}. 内容前 300 字符: {content[:300]!r}"
                ) from e

        raise ValueError(
            f"LLM 响应中未找到有效 JSON 对象。内容前 300 字符: {content[:300]!r}"
        )


# Global client instance
_client: Optional[LLMClient] = None


def get_llm_client() -> LLMClient:
    """Get or create the global LLM client instance."""
    global _client
    if _client is None:
        _client = LLMClient()
    return _client
