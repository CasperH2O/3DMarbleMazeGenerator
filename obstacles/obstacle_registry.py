# obstacles/obstacle_registry.py

from typing import Dict, List, Type

from obstacles.obstacle import Obstacle  # Use the correct path

# Registry to hold the mapping from obstacle name (string) to the Obstacle class
OBSTACLE_REGISTRY: Dict[str, Type[Obstacle]] = {}


def register_obstacle(name: str, cls: Type[Obstacle]):
    """Registers an Obstacle subclass in the registry."""
    if not name:
        raise ValueError("Obstacle name cannot be empty.")
    if name in OBSTACLE_REGISTRY:
        print(f"Warning: Overwriting obstacle registration for '{name}'")
    if not issubclass(cls, Obstacle):
        raise TypeError(f"Class {cls.__name__} is not a subclass of Obstacle.")

    OBSTACLE_REGISTRY[name] = cls


def get_obstacle_class(name: str) -> Type[Obstacle]:
    """Retrieves an obstacle class from the registry by name."""
    cls = OBSTACLE_REGISTRY.get(name)
    if cls is None:
        raise ValueError(
            f"No obstacle registered with name '{name}'. Available: {list(OBSTACLE_REGISTRY.keys())}"
        )
    return cls


def get_available_obstacles() -> List[str]:
    """Returns a list of names of all registered obstacles."""
    return list(OBSTACLE_REGISTRY.keys())
