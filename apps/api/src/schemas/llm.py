from enum import Enum

from pydantic import BaseModel


class Model(Enum):
    CLAUDE_SONNET = "claude-3-7-sonnet-20250219"
    CLAUDE_COMPUTER = "claude-3-7-sonnet-20250219"
    GPT_4o = "gpt-4o-2024-08-06"
    GPT_4o_MINI = "gpt-4o-mini"
    CHATGPT_4o = "chatgpt-4o-latest"
    GEMINI_2_0_FLASH = "gemini-2.0-flash-001"
    GEMINI_2_0_FLASH_LITE = "gemini-2.0-flash-lite"
    GEMINI_2_0_FLASH_THINKING = "gemini-2.0-flash-thinking-exp"
    GEMINI_1_5_FLASH = "gemini-1.5-flash"
    GEMINI_1_5_FLASH_8B = "gemini-1.5-flash-8b"
    DEEPSEEK_R1_DISTILL_LLAMA_70B = "deepseek-r1-distill-llama-70b"
    LLAMA_3_1_8B_INSTANT = "llama-3.1-8b-instant"
    LLAMA_3_3_70B_VERSATILE = "llama-3.3-70b-versatile"
    GEMINI_1_5_PRO = "gemini-1.5-pro"
    O1 = "o1"
    O3_MINI = "o3-mini"


class PartialStream(BaseModel):
    chunk_text: str
    total_text: str


class EndStream(BaseModel):
    text: str
