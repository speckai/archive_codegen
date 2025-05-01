import asyncio
import base64
import traceback
from typing import Any, AsyncGenerator, Type

import instructor
from anthropic import AsyncAnthropic
from google import genai
from google.genai.types import Part
from groq import AsyncGroq
from helicone_helpers import HeliconeManualLogger
from helicone_helpers.manual_logger import HeliconeResultRecorder
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletion, ParsedChatCompletion
from pydantic import BaseModel
from src.config import (
    ANTHROPIC_API_KEY,
    GEMINI_API_KEY,
    GROQ_API_KEY,
    HELICONE_API_KEY,
    OPENAI_API_KEY,
    POSTHOG_HOST,
    POSTHOG_KEY,
)
from src.schemas.llm import EndStream, Model, PartialStream
from src.utils.logging import logger

openai_async_client: AsyncOpenAI = None
anthropic_async_client: AsyncAnthropic = None
groq_async_client: AsyncGroq = None

helicone_logger = HeliconeManualLogger(
    api_key=HELICONE_API_KEY,
    headers={
        "Helicone-Posthog-Key": POSTHOG_KEY,
        "Helicone-Posthog-Host": POSTHOG_HOST,
    },
)

MAX_CLAUDE_TOKENS = 200_000


def _get_system_role(model: str) -> str:
    return "developer" if model in [Model.O1, Model.O3_MINI] else "system"


def _sanitize_headers(extra_headers: dict[str, str]) -> dict[str, str]:
    """Remove None values from headers and log warnings for each removed key."""
    # OpenAI errors if None values are passed
    sanitized = {}
    for key, value in extra_headers.items():
        if value is None:
            logger.warning(f"Header '{key}' had None value and was removed")
            continue
        sanitized[key] = value
    return sanitized


def _setup_clients_and_models() -> None:
    global openai_async_client, anthropic_async_client, groq_async_client

    if OPENAI_API_KEY:
        openai_async_client = AsyncOpenAI(
            api_key=OPENAI_API_KEY,
            base_url="https://oai.helicone.ai/v1",
            default_headers={
                "Helicone-Auth": f"Bearer {HELICONE_API_KEY}",
                "Helicone-Posthog-Key": POSTHOG_KEY,
                "Helicone-Posthog-Host": POSTHOG_HOST,
            },
        )
    if ANTHROPIC_API_KEY:
        anthropic_async_client = instructor.from_anthropic(
            AsyncAnthropic(
                api_key=ANTHROPIC_API_KEY,
                base_url="https://anthropic.helicone.ai/",
                default_headers={
                    "Helicone-Auth": f"Bearer {HELICONE_API_KEY}",
                    "Helicone-Posthog-Key": POSTHOG_KEY,
                    "Helicone-Posthog-Host": POSTHOG_HOST,
                },
            ),
            mode=instructor.Mode.ANTHROPIC_JSON,
        )

    if GROQ_API_KEY:
        groq_async_client = instructor.from_groq(
            AsyncGroq(
                api_key=GROQ_API_KEY,
                # base_url="https://groq.helicone.ai/openai/v1",
                # default_headers={
                #     "Helicone-Auth": f"Bearer {HELICONE_API_KEY}",
                #     "Helicone-Posthog-Key": POSTHOG_KEY,
                #     "Helicone-Posthog-Host": POSTHOG_HOST,
                # },
            ),
        )

    if GEMINI_API_KEY:
        # genai.configure(api_key=GEMINI_API_KEY)
        pass  # Has to be done on a per-client basis


_setup_clients_and_models()


# OPENAI
async def openai_chat(
    model: str,
    system: str,
    messages: list[dict[str, str]],
    response_model: BaseModel | Type[str],
    extra_headers: dict[str, str],
    **kwargs,
) -> BaseModel | AsyncGenerator:
    extra_headers = _sanitize_headers(extra_headers)

    # Handle optional args
    optional_args: dict[str, Any] = {}
    if Model(model) not in [Model.O1, Model.O3_MINI]:
        optional_args["temperature"] = (
            0.0 if kwargs.get("temperature") is None else kwargs["temperature"]
        )

    # Combine kwargs with optional_args
    kwargs = {**kwargs, **optional_args}
    kwargs.pop("temperature", None)  # Remove temperature from kwargs if it exists

    if response_model is str:
        response: ChatCompletion = await openai_async_client.chat.completions.create(
            model=model,
            messages=[{"role": _get_system_role(model), "content": system}, *messages],
            extra_headers=extra_headers,
            **kwargs,
        )
        return response.choices[0].message.content
    else:
        response: ParsedChatCompletion = (
            await openai_async_client.beta.chat.completions.parse(
                model=model,
                messages=[
                    {"role": _get_system_role(model), "content": system},
                    *messages,
                ],
                response_format=response_model,
                extra_headers=extra_headers,
                **kwargs,
            )
        )
        return response.choices[0].message.parsed


async def openai_basemodel_stream_chat(
    model: str,
    system: str,
    messages: list[dict[str, str]],
    response_model: BaseModel,
    extra_headers: dict[str, str],
    **kwargs,
) -> AsyncGenerator:
    extra_headers = _sanitize_headers(extra_headers)
    if Model(model) not in [Model.O1, Model.O3_MINI]:
        temperature = (
            0.0 if kwargs.get("temperature") is None else kwargs["temperature"]
        )
        kwargs = {**kwargs, "temperature": temperature}

    stream_request = openai_async_client.beta.chat.completions.stream(
        model=model,
        messages=[{"role": _get_system_role(model), "content": system}, *messages],
        response_format=response_model,
        extra_headers=extra_headers,
        **kwargs,
    )
    async with stream_request as stream:
        async for event in stream:
            if event.type == "content.delta":
                if event.parsed is not None:
                    yield event.parsed
            elif event.type == "error":
                raise RuntimeError(f"Error in stream: {event.error}")


async def anthropic_chat(
    model: str,
    system: str,
    messages: list[dict[str, str]],
    response_model: BaseModel | Type[str],
    extra_headers: dict[str, str],
    **kwargs,
) -> BaseModel | AsyncGenerator | str:
    extra_headers["anthropic-beta"] = (
        "max-tokens-3-5-sonnet-2024-07-15,prompt-caching-2024-07-31"
    )
    extra_headers = _sanitize_headers(extra_headers)
    temperature: int = (
        0.0 if kwargs.get("temperature") is None else kwargs["temperature"]
    )
    long_output: bool = kwargs.get("long_output", False)
    if long_output:
        kwargs["betas"] = ["output-128k-2025-02-19"]
    kwargs.pop("temperature", None)
    kwargs.pop("long_output", None)

    if response_model is str:
        local_client: AsyncAnthropic = AsyncAnthropic(
            api_key=ANTHROPIC_API_KEY,
            base_url="https://anthropic.helicone.ai/",
            default_headers={
                "Helicone-Auth": f"Bearer {HELICONE_API_KEY}",
                "Helicone-Posthog-Key": POSTHOG_KEY,
                "Helicone-Posthog-Host": POSTHOG_HOST,
            },
        )
        stream = await local_client.messages.create(
            model=model,
            system=system,
            messages=messages,
            max_tokens=64000 if not long_output else 128_000,
            extra_headers=extra_headers,
            temperature=temperature,
            stream=True,
            **kwargs,
        )

        # Collect all content from the stream
        full_text = ""
        async for chunk in stream:
            if chunk.type == "content_block_delta":
                full_text += chunk.delta.text

        return full_text
    else:
        # For non-string response models, we need a different approach since we can't
        # simply concatenate stream chunks.
        # If you're seeing timeouts for large models, consider implementing
        # streaming here as well and constructing the response model from the stream data
        return await anthropic_async_client.messages.create(
            model=model,
            system=system,
            messages=messages,
            max_tokens=64000 if not long_output else 128_000,
            response_model=response_model,
            extra_headers=extra_headers,
            temperature=temperature,
            max_retries=5,
            stream=True,
            **kwargs,
        )


async def anthropic_raw_chat(
    model: str,
    system: str,
    messages: list[dict[str, str]],
    response_model: BaseModel | Type[str],
    extra_headers: dict[str, str],
    **kwargs,
) -> BaseModel | AsyncGenerator | str:
    local_client: AsyncAnthropic = AsyncAnthropic(
        api_key=ANTHROPIC_API_KEY,
        base_url="https://anthropic.helicone.ai/",
        default_headers={
            "Helicone-Auth": f"Bearer {HELICONE_API_KEY}",
            "Helicone-Posthog-Key": POSTHOG_KEY,
            "Helicone-Posthog-Host": POSTHOG_HOST,
        },
    )
    temperature: int = (
        0.0 if kwargs.get("temperature") is None else kwargs["temperature"]
    )
    kwargs.pop("temperature", None)

    return await local_client.beta.messages.create(
        model=model,
        system=system,
        messages=messages,
        max_tokens=8192,
        extra_headers=extra_headers,
        temperature=temperature,
        **kwargs,
    )


async def anthropic_basemodel_stream_chat(
    model: str,
    system: str,
    messages: list[dict[str, str]],
    response_model: BaseModel,
    extra_headers: dict[str, str],
    **kwargs,
) -> AsyncGenerator:
    extra_headers["anthropic-beta"] = (
        "max-tokens-3-5-sonnet-2024-07-15,prompt-caching-2024-07-31"
    )
    extra_headers = _sanitize_headers(extra_headers)
    temperature: int = (
        0.0 if kwargs.get("temperature") is None else kwargs["temperature"]
    )
    kwargs.pop("temperature", None)

    return anthropic_async_client.messages.create_partial(
        model=model,
        system=system,
        messages=messages,
        max_tokens=8000,
        response_model=response_model,
        extra_headers=extra_headers,
        temperature=temperature,
        max_retries=5,
        stream=True,
        **kwargs,
    )


async def anthropic_str_stream_chat(
    model: str,
    system: str,
    messages: list[dict[str, str]],
    extra_headers: dict[str, str],
    retries: int = 3,
    **kwargs,
) -> AsyncGenerator:
    extra_headers = _sanitize_headers(extra_headers)
    local_client: AsyncAnthropic = AsyncAnthropic(
        api_key=ANTHROPIC_API_KEY,
        base_url="https://anthropic.helicone.ai/",
        default_headers={
            "Helicone-Auth": f"Bearer {HELICONE_API_KEY}",
            "Helicone-Posthog-Key": POSTHOG_KEY,
            "Helicone-Posthog-Host": POSTHOG_HOST,
        },
    )
    temperature: int = (
        0.0 if kwargs.get("temperature") is None else kwargs["temperature"]
    )
    long_output: bool = kwargs.get("long_output", False)
    if long_output:
        kwargs["betas"] = ["output-128k-2025-02-19"]
    kwargs.pop("temperature", None)
    kwargs.pop("long_output", None)

    collected_str: str = ""
    response_gen = None

    for i in range(retries):
        try:
            response_gen: AsyncGenerator = await local_client.beta.messages.create(
                system=system,
                messages=messages,
                model=model,
                temperature=temperature,
                max_tokens=128_000 if long_output else 8192,
                extra_headers=extra_headers,
                stream=True,
                **kwargs,
            )
            break
        except Exception as e:
            if i == retries - 1:
                raise e
            await asyncio.sleep(min(2**i, 4))
            continue

    if response_gen is None:
        raise Exception("Failed to create message stream after all retries")

    try:
        async for event in response_gen:
            if event.type == "content_block_delta":
                collected_str += event.delta.text
                yield PartialStream(
                    chunk_text=event.delta.text,
                    total_text=collected_str,
                )
            elif event.type == "message_stop":
                yield EndStream(text=collected_str)
                break
    except Exception as e:
        if "overloaded_error" not in str(e):
            raise e
        logger.critical(f"Anthropic overloaded error: {e}")
        logger.critical(traceback.format_exc())
        await asyncio.sleep(5)
        async for event in anthropic_str_stream_chat(
            model=model,
            system=system,
            messages=messages,
            extra_headers=extra_headers,
            retries=retries - 1,
            **kwargs,
        ):
            yield event


async def gemini_chat(
    model: str,
    system: str,
    messages: list[dict[str, str]],
    response_model: BaseModel | Type[str],
    extra_headers: dict[str, str],
    **kwargs,
) -> BaseModel:
    client_openai: AsyncOpenAI = AsyncOpenAI(
        api_key=GEMINI_API_KEY,
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
    )

    # TODO: get the output to be logged as well. currently not working
    async def chat_completion_operation(result_recorder: HeliconeResultRecorder):
        if response_model is str:
            response = await client_openai.chat.completions.create(
                model=model,
                messages=[{"role": "system", "content": system}, *messages],
                **kwargs,
            )
            # Log the raw response data
            result_recorder.append_results(response)
            return response.choices[0].message.content
        else:
            response = await client_openai.beta.chat.completions.parse(
                model=model,
                messages=[{"role": "system", "content": system}, *messages],
                response_format=response_model,
                **kwargs,
            )
            # Log the raw response data
            result_recorder.append_results(
                response.choices[0].message.parsed.model_dump()
            )
            return response.choices[0].message.parsed

    request = {
        "model": model,
        "messages": [{"role": "system", "content": system}, *messages],
        **kwargs,
    }
    if response_model is not str:
        request["response_format"] = {
            "type": "json_object"
        }  # This is what OpenAI expects

    return await helicone_logger.log_request(
        provider="google",
        request=request,
        operation=chat_completion_operation,
        additional_headers=extra_headers,
    )


async def gemini_str_chat(
    model: str,
    system: str,
    messages: list[dict[str, str]],
    extra_headers: dict[str, str],
    **kwargs,
) -> str:
    extra_headers = _sanitize_headers(extra_headers)
    local_client: AsyncOpenAI = AsyncOpenAI(
        api_key=GEMINI_API_KEY,
        base_url="https://gateway.helicone.ai/v1beta/openai",
        default_headers={
            "helicone-auth": f"Bearer {HELICONE_API_KEY}",
            "helicone-target-url": "https://generativelanguage.googleapis.com",
        },
    )
    temperature: int = (
        0.0 if kwargs.get("temperature") is None else kwargs["temperature"]
    )
    kwargs.pop("temperature", None)

    response: ChatCompletion = await local_client.chat.completions.create(
        model=model,
        messages=[{"role": "system", "content": system}, *messages],
        temperature=temperature,
        extra_headers=extra_headers,
        **kwargs,
    )
    return response.choices[0].message.content


async def gemini_str_stream_chat(
    model: str,
    system: str,
    messages: list[dict[str, str]],
    extra_headers: dict[str, str],
    **kwargs,
) -> AsyncGenerator:
    local_client: AsyncOpenAI = AsyncOpenAI(
        api_key=GEMINI_API_KEY,
        base_url="https://gateway.helicone.ai/v1beta/openai",
        default_headers={
            "helicone-auth": f"Bearer {HELICONE_API_KEY}",
            "helicone-target-url": "https://generativelanguage.googleapis.com",
        },
    )
    temperature: int = (
        0.0 if kwargs.get("temperature") is None else kwargs["temperature"]
    )
    kwargs.pop("temperature", None)

    response_gen = await local_client.chat.completions.create(
        model=model,
        messages=[{"role": "system", "content": system}, *messages],
        temperature=temperature,
        extra_headers=extra_headers,
        stream=True,
        **kwargs,
    )
    collected_str: str = ""
    async for event in response_gen:
        if event.choices[0].delta.content is not None:
            collected_str += event.choices[0].delta.content
            yield PartialStream(
                chunk_text=event.choices[0].delta.content,
                total_text=collected_str,
            )
        elif event.choices[0].finish_reason is not None:
            yield EndStream(text=collected_str)
            break


def analyze_video(prompt: str, video_base64: str) -> str:
    """
    Analyze a base64-encoded WebM video using Gemini and return a text description.

    Args:
        video_base64: Base64-encoded WebM video data (without data URI prefix)
        api_key: Optional Gemini API key (if not using environment variable)

    Returns:
        String description of the video content
    """
    client = genai.Client(api_key=GEMINI_API_KEY)

    if "base64," in video_base64:
        video_base64 = video_base64.split("base64,")[1]

    try:
        # Create a proper data URI for the video

        # Call Gemini with the video
        response = client.models.generate_content(
            model=Model.GEMINI_2_0_FLASH,
            contents=[
                prompt,
                Part.from_bytes(
                    data=base64.b64decode(video_base64), mime_type="video/webm"
                ),
            ],
        )

        # Return the text response
        return response.text
    except Exception as e:
        return f"Error analyzing video: {str(e)}"


async def groq_chat(
    model: str,
    system: str,
    messages: list[dict[str, str]],
    response_model: BaseModel,
    extra_headers: dict[str, str],
    **kwargs,
) -> BaseModel | AsyncGenerator:
    temperature: int = (
        0.0 if kwargs.get("temperature") is None else kwargs["temperature"]
    )
    kwargs.pop("temperature", None)

    response: dict[str, list[dict[str, str]]] = (
        await groq_async_client.chat.completions.create(
            model=model,
            messages=[{"role": "system", "content": system}, *messages],
            max_completion_tokens=4000,
            response_model=response_model,
            extra_headers=extra_headers,
            temperature=temperature,
            max_retries=5,
        )
    )
    return response


async def groq_basemodel_stream_chat(
    model: str,
    system: str,
    messages: list[dict[str, str]],
    response_model: BaseModel,
    extra_headers: dict[str, str],
    **kwargs,
) -> AsyncGenerator:
    temperature: int = (
        0.0 if kwargs.get("temperature") is None else kwargs["temperature"]
    )
    kwargs.pop("temperature", None)

    return groq_async_client.chat.completions.create_partial(
        model=model,
        messages=[{"role": "system", "content": system}, *messages],
        response_model=response_model,
        extra_headers=extra_headers,
        stream=True,
        temperature=temperature,
        **kwargs,
    )


async def groq_str_stream_chat(
    model: str,
    system: str,
    messages: list[dict[str, str]],
    extra_headers: dict[str, str],
    **kwargs,
) -> AsyncGenerator:
    local_client: AsyncGroq = AsyncGroq(
        api_key=GROQ_API_KEY,
        # base_url="https://groq.helicone.ai/openai/v1",
        # default_headers={
        #     "Helicone-Auth": f"Bearer {HELICONE_API_KEY}",
        #     "Helicone-Posthog-Key": POSTHOG_KEY,
        #     "Helicone-Posthog-Host": POSTHOG_HOST,
        # },
    )
    temperature: int = (
        0.0 if kwargs.get("temperature") is None else kwargs["temperature"]
    )
    kwargs.pop("temperature", None)

    response_gen = await local_client.chat.completions.create(
        model=model,
        messages=[{"role": "system", "content": system}, *messages],
        temperature=temperature,
        extra_headers=extra_headers,
        stream=True,
        **kwargs,
    )
    collected_str: str = ""
    async for event in response_gen:
        if event.choices[0].delta.content is not None:
            collected_str += event.choices[0].delta.content
            yield PartialStream(
                chunk_text=event.choices[0].delta.content,
                total_text=collected_str,
            )
        elif event.choices[0].finish_reason is not None:
            yield EndStream(text=collected_str)
            break
