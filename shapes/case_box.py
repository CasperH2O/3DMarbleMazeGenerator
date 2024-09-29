# shapes/case_box.py

from .case_base import CaseBase
import cadquery as cq


class CaseBox(CaseBase):
    def __init__(self, config):
        self.width = config.WIDTH
        self.height = config.HEIGHT
        self.length = config.LENGTH
        self.panel_thickness = config.PANEL_THICKNESS

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
            "casing": (self.casing, {"alpha": 0.9, "color": (1, 1, 1)}),
        }
