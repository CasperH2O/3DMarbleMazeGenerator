# cad/cases/case_box.py

from .case_base import CaseBase, CasePart
from build123d import BuildPart, Box, offset, Mode, BuildSketch, Rectangle, extrude
from config import Config

class CaseBox(CaseBase):
    def __init__(self):
        self.length = Config.Box.LENGTH
        self.width = Config.Box.WIDTH
        self.height = Config.Box.HEIGHT
        self.panel_thickness = Config.Box.PANEL_THICKNESS

        # Create the box casing
        self.casing = self.create_casing()
        self.cut_shape = self.create_cut_shape()

    def create_casing(self):
        with BuildPart() as casing:
            # Create the outer box
            Box(self.width, self.length, self.height)
            # Hollow out the box
            offset(amount=-Config.Box.PANEL_THICKNESS, mode=Mode.SUBTRACT)
        return casing

    def get_parts(self):
        return {
            "Casing": CasePart("Casing", self.casing, {"alpha": 0.05, "color": (1, 1, 1)}),
        }

    def create_cut_shape(self):
        # Create a box to ensure it cuts the path body properly
        flush_distance_tolerance = 0.4  # Add small distance for tolerances

        # Create the inner box to hollow out the outer box
        inner_width = self.width - 2 * self.panel_thickness - 2 * flush_distance_tolerance
        inner_length = self.length - 2 * self.panel_thickness - 2 * flush_distance_tolerance
        inner_height = self.height - 2 * self.panel_thickness - 2 * flush_distance_tolerance

        with BuildPart() as cut_shape:
            # Extend the outer box sizes to ensure it cuts the path body properly
            Box(self.width * 2, self.length * 2, self.height * 2)
            with BuildSketch():
                # Size to cut the box
                Rectangle(inner_width, inner_length)
            # Hollow out the box
            extrude(amount=inner_height / 2, both=True, mode=Mode.SUBTRACT)
        return cut_shape
