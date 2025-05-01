from dotenv import load_dotenv
from src.config import ANTHROPIC_API_KEY
from src.utils.logging import logger

load_dotenv()

logger.info("don't use this")
ANTHROPIC_API_KEY = ANTHROPIC_API_KEY
