import asyncio
import statistics
from dataclasses import dataclass
from time import perf_counter
from typing import Tuple

import google.generativeai as genai
import tiktoken
from anthropic import Anthropic
from openai import OpenAI
from pydantic import BaseModel
from src.config import ANTHROPIC_API_KEY, GEMINI_API_KEY, OPENAI_API_KEY

from .prompts import system_prompt, user_prompt


@dataclass
class ModelConfig:
    provider: str
    name: str
    streaming: bool = True


@dataclass
class BenchmarkResult:
    model: ModelConfig
    response_times: list[float]
    token_counts: list[int]
    time_to_first_token: list[float]
    avg_time: float
    std_dev: float
    min_time: float
    max_time: float
    avg_tokens: float
    tokens_per_second: float
    avg_time_to_first_token: float


def count_tokens(text: str) -> int:
    encoding = tiktoken.get_encoding(
        "cl100k_base"
    )  # Using OpenAI's encoding as approximation
    return len(encoding.encode(text))


def gemini_chat(
    model: str,
    system: str,
    message: str,
) -> BaseModel:
    genai.configure(
        api_key=GEMINI_API_KEY,
        # client_options={
        #     "api_endpoint": "gateway.helicone.ai",
        # },
        # default_metadata=[
        #     ("helicone-auth", f"Bearer {HELICONE_API_KEY}"),
        #     ("helicone-target-url", "https://generativelanguage.googleapis.com"),
        # ],
        transport="rest",
    )

    client = genai.GenerativeModel(
        model_name=model,
        system_instruction=system,
    )

    return client.generate_content(message).text


def openai_chat(
    model: str,
    system: str,
    message: str,
) -> str:
    client = OpenAI(
        api_key=OPENAI_API_KEY,
        # default_headers={
        #     "Helicone-Auth": f"Bearer {HELICONE_API_KEY}",
        # },
        # base_url="https://gateway.helicone.ai/v1",
    )

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": message},
        ],
    )
    return response.choices[0].message.content


def anthropic_chat(
    model: str,
    system: str,
    message: str,
) -> str:
    client = Anthropic(
        api_key=ANTHROPIC_API_KEY,
        # default_headers={
        #     "Helicone-Auth": f"Bearer {HELICONE_API_KEY}",
        # },
        # base_url="https://gateway.helicone.ai/v1/anthropic",
    )

    response = client.messages.create(
        model=model,
        system=system,
        messages=[{"role": "user", "content": message}],
    )
    return response.content[0].text


async def stream_response(model_config: ModelConfig) -> Tuple[float, float, str]:
    start_time = perf_counter()

    if model_config.provider == "gemini":
        client = genai.GenerativeModel(
            model_name=model_config.name,
            system_instruction=system_prompt,
        )
        response = client.generate_content(user_prompt, stream=model_config.streaming)
    elif model_config.provider == "openai":
        client = OpenAI(api_key=OPENAI_API_KEY)
        response = client.chat.completions.create(
            model=model_config.name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            stream=model_config.streaming,
        )
    elif model_config.provider == "anthropic":
        client = Anthropic(api_key=ANTHROPIC_API_KEY)
        response = client.messages.create(
            model=model_config.name,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
            stream=model_config.streaming,
            max_tokens=4096,
        )

    # Handle streaming response
    first_chunk = None
    full_response = []

    if model_config.streaming:
        for chunk in response:
            if first_chunk is None:
                first_chunk = chunk
                first_token_time = perf_counter() - start_time
            if model_config.provider == "gemini":
                full_response.append(chunk.text)
            elif model_config.provider == "openai":
                full_response.append(chunk.choices[0].delta.content or "")
            elif model_config.provider == "anthropic":
                if chunk.type == "content_block_delta":
                    full_response.append(chunk.delta.text)
    else:
        # Handle non-streaming response
        first_token_time = perf_counter() - start_time
        if model_config.provider == "gemini":
            full_response = [response.text]
        elif model_config.provider == "openai":
            full_response = [response.choices[0].message.content]
        elif model_config.provider == "anthropic":
            full_response = [response.content[0].text]

    end_time = perf_counter()
    total_time = end_time - start_time

    return total_time, first_token_time, "".join(full_response)


def get_prompt_tokens():
    encoding = tiktoken.get_encoding("cl100k_base")
    system_tokens = len(encoding.encode(system_prompt))
    user_tokens = len(encoding.encode(user_prompt))
    return system_tokens, user_tokens


async def benchmark_model_parallel(
    model: ModelConfig, iterations: int = 5
) -> BenchmarkResult:
    # Create tasks for parallel execution
    tasks = [stream_response(model) for _ in range(iterations)]

    # Run all tasks concurrently
    results = await asyncio.gather(*tasks)

    # Unpack the results
    times = [total_time for total_time, _, _ in results]
    first_token_times = [ttf for _, ttf, _ in results]
    token_counts = [count_tokens(response) for _, _, response in results]

    avg_tokens = statistics.mean(token_counts)
    avg_time = statistics.mean(times)
    tokens_per_second = avg_tokens / avg_time

    return BenchmarkResult(
        model=model,
        response_times=times,
        token_counts=token_counts,
        time_to_first_token=first_token_times,
        avg_time=avg_time,
        std_dev=statistics.stdev(times),
        min_time=min(times),
        max_time=max(times),
        avg_tokens=avg_tokens,
        tokens_per_second=tokens_per_second,
        avg_time_to_first_token=statistics.mean(first_token_times),
    )


async def run_all_benchmarks(
    models: list[ModelConfig], iterations: int
) -> list[BenchmarkResult]:
    tasks = [benchmark_model_parallel(model, iterations) for model in models]
    return await asyncio.gather(*tasks)


if __name__ == "__main__":
    # Define models to benchmark
    models = [
        ModelConfig("gemini", "gemini-1.5-pro"),
        ModelConfig("gemini", "gemini-1.5-flash-8b"),
        ModelConfig("gemini", "gemini-2.0-flash-exp"),
        ModelConfig("openai", "gpt-4o"),
        ModelConfig("openai", "gpt-4o-mini"),
        ModelConfig("anthropic", "claude-3-5-sonnet-20241022"),
    ]

    # Print token counts for prompts
    system_tokens, user_tokens = get_prompt_tokens()
    print("\nPrompt Token Counts:")
    print(f"System prompt: {system_tokens} tokens")
    print(f"User prompt: {user_tokens} tokens")
    print(f"Total: {system_tokens + user_tokens} tokens\n")

    iterations = 10

    # Run parallel benchmarks
    results = asyncio.run(run_all_benchmarks(models, iterations))

    # Print results in a formatted table
    print(f"\Model Benchmarks ({iterations} iterations)")
    print("-" * 100)
    print(
        f"{'Model':<25} {'Avg Time':>10} {'Std Dev':>10} {'TTF':>10} {'Tokens':>10} {'Tok/s':>10}"
    )
    print("-" * 100)

    for result in results:
        print(
            f"{result.model.name:<25} "
            f"{result.avg_time:>10.2f}s "
            f"{result.std_dev:>10.2f}s "
            f"{result.avg_time_to_first_token:>10.2f}s "
            f"{result.avg_tokens:>10.0f} "
            f"{result.tokens_per_second:>10.1f}"
        )
