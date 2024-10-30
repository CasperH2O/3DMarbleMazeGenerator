# shapes/case_box.py

from .case_base import CaseBase
import cadquery as cq
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
        outer_box = cq.Workplane("XY").box(self.width, self.height, self.length,)

        # Create the inner box to hollow out the outer box
        inner_width = self.width - 2 * self.panel_thickness
        inner_length = self.length - 2 * self.panel_thickness
        inner_height = self.height - 2 * self.panel_thickness

        inner_box = (cq.Workplane("XY")
                     .box(inner_width, inner_height, inner_length)
                     )

        # Subtract the inner box from the outer box
        casing = outer_box.cut(inner_box)
        return casing

    def get_cad_objects(self):
        return {
            "Casing": (self.casing, {"alpha": 0.05, "color": (1, 1, 1)}),
        }

    def get_cut_shape(self):
        # Create an extended inner box to ensure it cuts the path_body properly

        # Add small distance for tolerances
        flush_distance_tolerance = 0.4

        # Extend the outer box dimensions to make sure it intersects with the path_body
        outer_box = cq.Workplane("XY").box(self.width * 2, self.height * 2, self.length * 2)

        # Create the inner box to hollow out the outer box
        inner_width = self.width - 2 * self.panel_thickness - 2 * flush_distance_tolerance
        inner_length = self.length - 2 * self.panel_thickness - 2 * flush_distance_tolerance
        inner_height = self.height - 2 * self.panel_thickness - 2 * flush_distance_tolerance

        inner_box = (cq.Workplane("XY")
                     .box(inner_width, inner_height, inner_length)
                     )

        # Subtract the inner box from the outer box
        cut_shape = outer_box.cut(inner_box)

        return cut_shape
