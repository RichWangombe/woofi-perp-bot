from loguru import logger
from pathlib import Path


def setup_logger(log_dir: str = "logs"):
    Path(log_dir).mkdir(parents=True, exist_ok=True)
    logger.remove()
    logger.add(lambda msg: print(msg, end=""))
    logger.add(Path(log_dir) / "runtime.log", rotation="10 MB", level="INFO")
    return logger
