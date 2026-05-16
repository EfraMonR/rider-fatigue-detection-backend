import logging
import sys

_fmt = logging.Formatter(
    fmt="[%(levelname)s] %(asctime)s %(name)s: %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%SZ",
)
_handler = logging.StreamHandler(sys.stdout)
_handler.setFormatter(_fmt)


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.addHandler(_handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    return logger
