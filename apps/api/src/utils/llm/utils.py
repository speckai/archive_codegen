import google.generativeai as genai
from anthropic import AsyncAnthropic
from openai import AsyncOpenAI
from src.schemas.account import User

openai_async_client: AsyncOpenAI = None
anthropic_async_client: AsyncAnthropic = None
gemini_async_client: genai.GenerativeModel = None


def get_helicone_headers(
    task_path: str = None,
    task_id: str = None,
    task_name: str = None,
    user: User | None = None,
) -> dict[str, str]:
    headers: dict[str, str] = {}
    if task_path:
        headers["Helicone-Session-Path"] = task_path
    if task_id:
        headers["Helicone-Session-Id"] = (
            f"{task_id}_DEBUG" if user is None else f"{user.email}_{task_id}"
        )
    if task_name:
        headers["Helicone-Session-Name"] = task_name
    if user is not None:
        headers["Helicone-Property-User-Id"] = user.id
        headers["Helicone-Property-User-Email"] = user.email
        headers["Helicone-Property-User-Name"] = user.name
        headers["Helicone-User-Id"] = user.email
    return headers
