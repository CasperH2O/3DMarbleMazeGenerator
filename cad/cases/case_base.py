# cad/cases/case_base.py

from abc import ABC, abstractmethod
from .case_parts import CasePart


class CaseBase(ABC):
    @abstractmethod
    def __init__(self):
        pass

    @abstractmethod
    def get_parts(self):
        """
        Returns a dictionary of CasePart objects representing the case components.
        """
        pass
