# cad/case_base.py

from abc import ABC, abstractmethod


class CaseBase(ABC):
    @abstractmethod
    def __init__(self):
        pass

    @abstractmethod
    def get_cad_objects(self):
        """
        Returns a dictionary of CADQuery objects representing the case components.
        """
        pass