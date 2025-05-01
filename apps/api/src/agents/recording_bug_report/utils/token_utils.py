"""Utilities for token management in the implementer agent."""

import base64
from typing import Any

import tiktoken
from anthropic import AsyncAnthropic
from src.config import ANTHROPIC_API_KEY
from src.schemas.llm import Model
from src.utils.logging import logger


class TokenCounter:
    """Manages token counting and limits for LLM input."""

    def __init__(self, max_tokens: int = 200_000, tokens_per_char: int = 4):
        """
        Initialize the token manager.

        Args:
            max_tokens: Maximum number of tokens allowed in the context
            tokens_per_char: Approximate number of characters per token (for estimation)
        """
        self.max_tokens = max_tokens
        self.tokens_per_char = tokens_per_char
        # Cache for tiktoken encoders
        self._encoders = {}

    def _get_encoder(self, model_type: Model) -> tiktoken.Encoding:
        """
        Get the appropriate tiktoken encoder for a model.

        Args:
            model_type: The model to get an encoder for

        Returns:
            tiktoken.Encoding: The encoder for the model
        """
        model_value = model_type.value

        if model_value in self._encoders:
            return self._encoders[model_value]

        if model_value.startswith(("claude", "Claude")):
            encoding_name = "cl100k_base"
        elif model_value.startswith("gpt-4"):
            encoding_name = "cl100k_base"
        elif model_value.startswith("gpt-3.5"):
            encoding_name = "cl100k_base"
        elif "llama" in model_value.lower():
            encoding_name = "cl100k_base"
        elif "gemini" in model_value.lower():
            encoding_name = "cl100k_base"
        else:
            encoding_name = "cl100k_base"
            logger.warning(f"Using default encoding for unknown model: {model_value}")

        try:
            encoder = tiktoken.get_encoding(encoding_name)
            self._encoders[model_value] = encoder
            return encoder
        except Exception as e:
            logger.error(f"Error getting tiktoken encoding: {e}")
            encoder = tiktoken.get_encoding("cl100k_base")
            self._encoders[model_value] = encoder
            return encoder

    def estimate_tokens(self, text: str) -> int:
        """
        Estimate the number of tokens in a text string.
        This is a rough approximation - for precise counting you'd want to use count_tokens.

        Args:
            text: The text to estimate tokens for

        Returns:
            int: Estimated number of tokens
        """
        return int(len(text) / self.tokens_per_char)

    def count_tokens_with_tiktoken(self, model_type: Model, text: str) -> int:
        """
        Count tokens for text using tiktoken.

        Args:
            model_type: The model to count tokens for
            text: The text to count tokens for

        Returns:
            int: The number of tokens in the text
        """
        try:
            encoder = self._get_encoder(model_type)
            return len(encoder.encode(text))
        except Exception as e:
            logger.error(f"Error counting tokens with tiktoken: {e}")
            # Fall back to estimation
            return self.estimate_tokens(text)

    async def count_tokens(
        self,
        model_type: Model,
        system: str = "",
        message: list[dict[str, Any]] | None = None,
        thinking: dict[str, Any] | None = None,
        **kwargs,
    ) -> int:
        """
        Count tokens for a message.
        Uses tiktoken for text and Anthropic API for images.

        Args:
            model_type: The model to use (from Model enum)
            system: System prompt
            message: List of message dictionaries with role and content
            thinking: Optional thinking configuration for extended thinking
            **kwargs: Additional arguments to pass to the API

        Returns:
            int: The number of tokens in the input
        """
        # Check if message contains images
        has_images = False
        if message:
            for msg in message:
                content = msg.get("content", "")
                if isinstance(content, list):
                    for item in content:
                        if isinstance(item, dict) and item.get("type") == "image":
                            has_images = True
                            break
                if has_images:
                    break

        # If there are images, use the Anthropic API
        if has_images:
            return await self._count_tokens_with_api(
                model_type=model_type,
                system=system,
                message=message,
                thinking=thinking,
                **kwargs,
            )

        # Otherwise, use tiktoken
        total_tokens = 0

        # Count system prompt tokens
        if system:
            total_tokens += self.count_tokens_with_tiktoken(model_type, system)

        # Count message tokens
        if message:
            for msg in message:
                content = msg.get("content", "")
                if isinstance(content, str):
                    total_tokens += self.count_tokens_with_tiktoken(model_type, content)
                elif isinstance(content, list):
                    for item in content:
                        if isinstance(item, dict) and item.get("type") == "text":
                            text = item.get("text", "")
                            total_tokens += self.count_tokens_with_tiktoken(
                                model_type, text
                            )

        # Add tokens for message formatting (role indicators, etc.)
        # This is an approximation and may vary by model
        if message:
            # Add ~4 tokens per message for formatting
            total_tokens += len(message) * 4

        return total_tokens

    async def _count_tokens_with_api(
        self,
        model_type: Model,
        system: str = "",
        message: list[dict[str, Any]] | None = None,
        **kwargs,
    ) -> int:
        """
        Count tokens using the Anthropic API.
        Only used for messages containing images.

        Args:
            model_type: The model to use (from Model enum)
            system: System prompt
            message: List of message dictionaries with role and content
            thinking: Optional thinking configuration for extended thinking
            **kwargs: Additional arguments to pass to the API

        Returns:
            int: The number of tokens in the input
        """
        if not ANTHROPIC_API_KEY:
            logger.error("ANTHROPIC_API_KEY is not set")
            return 0

        # Only proceed with Claude models
        model_value = model_type.value
        if not model_value.startswith(("claude", "Claude")):
            logger.warning(
                f"API token counting only supported for Claude models, got {model_type}"
            )
            return 0

        # Initialize Anthropic client
        client = AsyncAnthropic(api_key=ANTHROPIC_API_KEY)

        try:
            # Ensure messages is always provided as required by the API
            if message is None:
                message = [{"role": "user", "content": ""}]

            response = await client.messages.count_tokens(
                model=model_value,
                messages=message,
                **({"system": system} if system else {}),
                **kwargs,
            )
            return response.input_tokens
        except Exception as e:
            logger.error(f"Error counting tokens with API: {e}")
            # Fall back to estimation if API call fails
            if message:
                total_chars = sum(len(str(m.get("content", ""))) for m in message)
                if system:
                    total_chars += len(system)
                return self.estimate_tokens(total_chars)
            return 0

    async def count_tokens_for_file(
        self, model_type: Model, file_path: str, file_content: str, **kwargs
    ) -> int:
        """
        Count tokens for a specific file with its content.

        Args:
            model_type: The model to use
            file_path: Path to the file
            file_content: Content of the file
            **kwargs: Additional arguments to pass to the API

        Returns:
            int: The number of tokens used by this file
        """
        # Format the file as it would appear in your XML
        file_xml = f'<file path="{file_path}">\n<![CDATA[\n{file_content}\n]]>\n</file>'

        # Use tiktoken directly for text files
        return self.count_tokens_with_tiktoken(model_type, file_xml)

    async def count_tokens_for_image(
        self,
        model_type: Model,
        image_data: bytes,
        media_type: str = "image/jpeg",
        **kwargs,
    ) -> int:
        """
        Count tokens for an image.

        Args:
            model_type: The model to use
            image_data: Raw image data bytes
            media_type: MIME type of the image
            **kwargs: Additional arguments to pass to the API

        Returns:
            int: The number of tokens used by this image
        """
        # Encode image to base64
        image_base64 = base64.b64encode(image_data).decode("utf-8")

        # Create message with image
        message = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": image_base64,
                        },
                    },
                ],
            }
        ]

        # Count tokens using the API (required for images)
        return await self._count_tokens_with_api(
            model_type=model_type, message=message, **kwargs
        )
