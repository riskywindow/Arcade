from __future__ import annotations

import json
import logging
from typing import Any


def configure_logging(service_name: str, log_level: str) -> logging.Logger:
    logging.basicConfig(level=getattr(logging, log_level.upper(), logging.INFO), force=True)
    logger = logging.getLogger(service_name)
    logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    return logger


def log_event(logger: logging.Logger, event: str, **fields: Any) -> None:
    payload = {"event": event, **fields}
    logger.info(json.dumps(payload, sort_keys=True))
