import logging
import sys

from pathlib import Path

from loguru import logger

BASE_DIR = Path(__file__).resolve().parent.parent
LOG_FILE = BASE_DIR / "logs.txt"


class InterceptHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        level = logger.level(record.levelname).name

        logger.opt(depth=6, exception=record.exc_info).log(level, record.getMessage())


def setup_logging():
    logging.basicConfig(
        handlers=[InterceptHandler()],
        level=logging.INFO,
        force=True
    )

    logging.getLogger("watchfiles").setLevel(logging.CRITICAL)

    logger.remove()

    logger.add(
        sys.stdout,
        level="INFO",
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan> | "
            "<level>{message}</level>"
        ),
        colorize=True,
    )

    logger.add(
        LOG_FILE,
        level="INFO",
        format=(
            "{time:YYYY-MM-DD HH:mm:ss} | "
            "{level: <8} | "
            "{name} | "
            "{message}"
        ),
        rotation="10 MB",
        retention="14 days",
        compression="zip",
    )