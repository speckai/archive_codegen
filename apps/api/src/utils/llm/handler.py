from typing import AsyncGenerator, Type

from pydantic import BaseModel
from src.schemas.account import User
from src.schemas.llm import Model
from src.utils.llm.calls import (
    anthropic_basemodel_stream_chat,
    anthropic_chat,
    anthropic_raw_chat,
    anthropic_str_stream_chat,
    gemini_chat,
    gemini_str_chat,
    gemini_str_stream_chat,
    groq_basemodel_stream_chat,
    groq_chat,
    groq_str_stream_chat,
    openai_basemodel_stream_chat,
    openai_chat,
)
from src.utils.llm.utils import get_helicone_headers
from src.utils.logging import logger

fallbacks: dict[Model, Model] = {
    Model.CLAUDE_SONNET: Model.GPT_4o,
    Model.GPT_4o: Model.CLAUDE_SONNET,
    Model.GEMINI_2_0_FLASH: Model.GPT_4o_MINI,
    Model.GPT_4o_MINI: Model.GEMINI_2_0_FLASH,
    Model.GEMINI_2_0_FLASH_LITE: Model.GEMINI_2_0_FLASH,
    Model.O1: Model.O3_MINI,
    Model.O3_MINI: Model.O1,
}


async def _chat(
    model_type: Model,
    system: str,
    messages: list[dict[str, str]],
    response_model: BaseModel | Type[str],
    task_path: str = None,
    task_id: str = None,
    task_name: str = None,
    user: User | None = None,
    stream: bool = False,
    **kwargs,
) -> BaseModel | AsyncGenerator | str:
    allowed_kwargs = [
        "prediction",
        "temperature",
        "reasoning_effort",
        "thinking",
        "long_output",
        "tools",
        "betas",
    ]
    if any(key not in allowed_kwargs for key in kwargs):
        raise ValueError(f"Invalid keyword arguments: {kwargs.keys()}")

    provider: str = None
    model: str = None

    if model_type in {Model.GPT_4o, Model.GPT_4o_MINI, Model.O1, Model.O3_MINI}:
        provider = "openai"
    elif model_type in {Model.CLAUDE_SONNET, Model.CLAUDE_COMPUTER}:
        provider = "anthropic"
    elif model_type in {
        Model.GEMINI_2_0_FLASH,
        Model.GEMINI_2_0_FLASH_LITE,
        Model.GEMINI_1_5_FLASH,
        Model.GEMINI_1_5_FLASH_8B,
    }:
        provider = "gemini"
    elif model_type in {
        Model.DEEPSEEK_R1_DISTILL_LLAMA_70B,
        Model.LLAMA_3_1_8B_INSTANT,
        Model.LLAMA_3_3_70B_VERSATILE,
    }:
        provider = "groq"
    model = model_type.value

    extra_headers: dict[str, str] = get_helicone_headers(
        task_path, task_id, task_name, user
    )

    if provider == "openai":
        if stream and response_model is str:
            return openai_chat(model, system, messages, extra_headers, **kwargs)
        elif stream:
            return await openai_basemodel_stream_chat(
                model, system, messages, response_model, extra_headers, **kwargs
            )
        return await openai_chat(
            model, system, messages, response_model, extra_headers, **kwargs
        )
    elif provider == "anthropic":
        if stream and response_model is str:
            return anthropic_str_stream_chat(
                model, system, messages, extra_headers, **kwargs
            )
        elif stream:
            return await anthropic_basemodel_stream_chat(
                model, system, messages, response_model, extra_headers, **kwargs
            )
        if model == Model.CLAUDE_COMPUTER:
            logger.info(f"Using raw anthropic chat for {model}")
            return await anthropic_raw_chat(
                model, system, messages, response_model, extra_headers, stream=stream
            )
        return await anthropic_chat(
            model,
            system,
            messages,
            response_model,
            extra_headers,
        )
    elif provider == "gemini":
        if stream:
            return gemini_str_stream_chat(
                model,
                system,
                messages,
                extra_headers,
                **kwargs,
            )
        if response_model is str:
            return await gemini_str_chat(
                model,
                system,
                messages,
                extra_headers,
                **kwargs,
            )

        return await gemini_chat(
            model,
            system,
            messages,
            response_model,
            extra_headers,
        )
    elif provider == "groq":
        if stream and response_model is str:
            return groq_str_stream_chat(
                model,
                system,
                messages,
                extra_headers,
                **kwargs,
            )
        elif stream:
            return await groq_basemodel_stream_chat(
                model,
                system,
                messages,
                response_model,
                extra_headers,
                **kwargs,
            )
        return await groq_chat(model, system, messages, response_model, extra_headers)


async def chat(
    model_type: Model,
    system: str,
    messages: list[dict[str, str]],
    response_model: BaseModel | Type[str],
    **kwargs,
) -> BaseModel | AsyncGenerator | str:
    try:
        return await _chat(model_type, system, messages, response_model, **kwargs)
    except Exception as e:
        logger.error(f"Error calling {model_type}: {str(e)[:300]}")
        import json

        with open("error.json", "w") as f:
            json.dump(
                {
                    "model_type": str(model_type),
                    "system": system,
                    "messages": messages,
                    "response_model": str(response_model),
                    "kwargs": kwargs,
                },
                f,
                indent=2,
            )
        fallback_model: Model = fallbacks.get(model_type, model_type)
        return await _chat(fallback_model, system, messages, response_model, **kwargs)
