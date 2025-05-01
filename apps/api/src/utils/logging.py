import logging
import sys

from logtail import LogtailHandler
from loguru import logger

from src.config import BETTERSTACK_SOURCE_TOKEN

logtail_handler: LogtailHandler = LogtailHandler(source_token=BETTERSTACK_SOURCE_TOKEN)
if BETTERSTACK_SOURCE_TOKEN:
    logger.add(
        logtail_handler,
        format="{message}",
        level="TRACE",
        backtrace=False,
        diagnose=False,
    )
else:
    logger.add(
        sys.stdout, format="{message}", level="TRACE", backtrace=False, diagnose=False
    )


class EndpointFilter(logging.Filter):
    banned_keywords: set[str] = {'"GET /is_already_connected HTTP/1.1" 200'}

    def filter(self, record: logging.LogRecord) -> bool:
        message: str = record.getMessage()
        return all(keyword not in message for keyword in self.banned_keywords)


logging.getLogger("uvicorn.access").addFilter(EndpointFilter())
