# shapes/case_base.py

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

    @abstractmethod
    def get_cut_shape(self):
        """
        Returns the CADQuery object used to cut the path_body to make it flush with the case.
        """
        return None