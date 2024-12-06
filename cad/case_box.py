# shapes/case_box.py

from .case_base import CaseBase
from build123d import *
from config import Config


class CaseBox(CaseBase):
    def __init__(self):
        self.width = Config.Box.WIDTH
        self.height = Config.Box.HEIGHT
        self.length = Config.Box.LENGTH
        self.panel_thickness = Config.Box.PANEL_THICKNESS

        # Create the box casing
        self.casing = self.create_casing()

    def create_casing(self):
        # Create the outer box
        with BuildPart() as casing:
            # Create the outer box
            Box(self.width, self.height, self.length)
            # Hollow out the box
            offset(amount=-Config.Box.PANEL_THICKNESS, mode=Mode.SUBTRACT)
    
        return casing

    def get_cad_objects(self):
        return {
            "Casing": (self.casing, {"alpha": 0.05, "color": (1, 1, 1)}),
        }

    def get_cut_shape(self):
        # Create a box to ensure it cuts the path body properly

        # Add small distance for tolerances
        flush_distance_tolerance = 0.4

        # Create the inner box to hollow out the outer box
        inner_width = self.width - 2 * self.panel_thickness - 2 * flush_distance_tolerance
        inner_length = self.length - 2 * self.panel_thickness - 2 * flush_distance_tolerance
        inner_height = self.height - 2 * self.panel_thickness - 2 * flush_distance_tolerance

        with BuildPart() as cut_shape:
            # Extend the outer box sizes to ensure it cuts the path body properly
            OuterBox = Box(self.width * 2, self.height * 2, self.length * 2)
            # Create the inner box
            InnerBox = Box(inner_width, inner_height, inner_length)
            # Hollow out the outer box inner box
            OuterBox - InnerBox

        return cut_shape
