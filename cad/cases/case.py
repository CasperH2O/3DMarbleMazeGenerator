# cad/cases/case_base.py

from abc import ABC, abstractmethod
from enum import Enum


class CasePart(Enum):
    """
    Enumeration representing the different types of case parts
    """

    MOUNTING_RING_CLIP_START = "Mounting Clip Start"
    MOUNTING_RING_CLIP_SINGLE = "Mounting Clip Single"
    MOUNTING_RING_CLIPS = "Mounting Clips"
    CASING = "Casing"
    DOME_TOP = "Dome Top"
    DOME_BOTTOM = "Dome Bottom"
    MOUNTING_RING = "Mounting Ring"
    MOUNTING_RING_TOP = "Mounting Ring Top"
    MOUNTING_RING_BOTTOM = "Mounting Ring Bottom"
    START_INDICATOR = "Start Indicator"
    INTERNAL_PATH_BRIDGES = "Path Bridges"


class Case(ABC):
    @abstractmethod
    def __init__(self):
        pass

    @abstractmethod
    def get_parts(self):
        """
        Returns a dictionary of CasePart objects representing the case components.
        """
        pass
