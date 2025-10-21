# obstacles/obstacle_registry.py

"""
Registry for all obstacle types.
"""

# obstacles/obstacle_registry.py
import importlib
import logging
import pkgutil
from typing import Dict, Type

from logging_config import configure_logging
from obstacles.obstacle import Obstacle

# Lazy-load guard
_CATALOGUE_LOADED = False

# Registry to hold the mapping from obstacle name (string) to the Obstacle class
OBSTACLE_REGISTRY: Dict[str, Type[Obstacle]] = {}

configure_logging()
logger = logging.getLogger(__name__)


def register_obstacle(name: str, cls: Type[Obstacle]):
    """Registers an Obstacle subclass in the registry."""
    if not name:
        raise ValueError("Obstacle name cannot be empty.")
    if name in OBSTACLE_REGISTRY:
        logger.warning("Overwriting obstacle registration for '%s'", name)
    if not issubclass(cls, Obstacle):
        raise TypeError(f"Class {cls.__name__} is not a subclass of Obstacle.")

    OBSTACLE_REGISTRY[name] = cls


def _load_all_catalogue_obstacles_once():
    """Import all modules in obstacles.catalogue once"""
    global _CATALOGUE_LOADED
    if _CATALOGUE_LOADED:
        return
    import obstacles.catalogue as catalogue_pkg

    # find all submodules in obstacles.catalogue and import them
    for modinfo in pkgutil.iter_modules(
        catalogue_pkg.__path__, catalogue_pkg.__name__ + "."
    ):
        importlib.import_module(modinfo.name)
    _CATALOGUE_LOADED = True


def get_obstacle_class(name: str) -> Type[Obstacle]:
    """Retrieves an obstacle class from the registry by name."""
    _load_all_catalogue_obstacles_once()
    cls = OBSTACLE_REGISTRY.get(name)
    if cls is None:
        raise ValueError(
            f"No obstacle registered with name '{name}'. Available: {list(OBSTACLE_REGISTRY.keys())}"
        )
    return cls


def get_available_obstacles() -> list[str]:
    """Returns a list of names of all registered obstacles."""
    _load_all_catalogue_obstacles_once()
    return list(OBSTACLE_REGISTRY.keys())
