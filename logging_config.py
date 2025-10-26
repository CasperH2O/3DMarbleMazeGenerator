# logging_config.py

from __future__ import annotations

import logging
from logging.config import dictConfig
from typing import Dict, Mapping, MutableMapping, Optional, Union

from colorlog import ColoredFormatter

# Default format applied to all log records
DEFAULT_LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"

# Default log level
DEFAULT_LOG_LEVEL: int = logging.INFO

# Module log level overrides
MODULE_LOG_LEVELS: MutableMapping[str, Union[int, str]] = {
    # "cad.curve_detection": "DEBUG",
    # "cad.path_architect": "DEBUG",
    # "cad.path_segment": "DEBUG",
    # "cad.path_builder": "DEBUG",
    # "obstacles.obstacle_manager": "DEBUG",
    "build123d": "WARNING",
}

# Default color mapping used by ``colorlog`` for level names
DEFAULT_LOG_COLORS: Dict[str, str] = {
    "DEBUG": "cyan",
    "INFO": "green",
    "WARNING": "yellow",
    "ERROR": "red",
    "CRITICAL": "bold_red",
}

# Default format applied when color support is available via ``colorlog``
DEFAULT_COLOR_LOG_FORMAT = (
    "%(asctime)s [%(log_color)s%(levelname)s%(reset)s] %(name)s: %(message)s"
)


def _normalize_level(level: Union[int, str]) -> Union[int, str]:
    """Return a logging level accepted by :mod:`logging` configuration APIs."""

    if isinstance(level, str):
        return level.upper()
    return int(level)


def build_logging_config(
    level: Union[int, str] = DEFAULT_LOG_LEVEL,
    module_levels: Optional[Mapping[str, Union[int, str]]] = None,
) -> Dict[str, object]:
    """Construct the dictionary configuration used to set up logging."""

    config: Dict[str, object] = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "color": {
                "()": ColoredFormatter,
                "format": DEFAULT_COLOR_LOG_FORMAT,
                "log_colors": DEFAULT_LOG_COLORS,
            },
            "plain": {
                "format": DEFAULT_LOG_FORMAT,
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "color",
            }
        },
        "root": {
            "level": _normalize_level(level),
            "handlers": ["console"],
        },
        "loggers": {},
    }

    if module_levels:
        loggers_config: Dict[str, object] = {}
        for name, module_level in module_levels.items():
            loggers_config[name] = {
                "level": _normalize_level(module_level),
                "handlers": [],
                "propagate": True,
            }
        config["loggers"] = loggers_config

    return config


def configure_logging(
    level: Union[int, str] = DEFAULT_LOG_LEVEL,
    module_levels: Optional[Mapping[str, Union[int, str]]] = None,
) -> None:
    """Configure logging for the project using centralized defaults.

    Parameters
    ----------
    level:
        Root logger level to apply. Defaults to :data:`DEFAULT_LOG_LEVEL`.
    module_levels:
        Optional mapping of module names to logging levels. Any provided
        overrides are merged on top of :data:`MODULE_LOG_LEVELS`.
    """

    merged_levels: MutableMapping[str, Union[int, str]] = dict(MODULE_LOG_LEVELS)
    if module_levels:
        merged_levels.update(module_levels)

    effective_module_levels = merged_levels or None
    dictConfig(
        build_logging_config(
            level=_normalize_level(level), module_levels=effective_module_levels
        )
    )
