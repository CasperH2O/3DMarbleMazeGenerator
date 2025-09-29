# cad/cases/case_box.py

from typing import List

from build123d import Box, BuildPart, Mode, Part, add, offset

from cad.cases.case import Case, CasePart
from config import Config


class CaseBox(Case):
    def __init__(self):
        self.length = Config.Box.LENGTH
        self.width = Config.Box.WIDTH
        self.height = Config.Box.HEIGHT
        self.panel_thickness = Config.Box.PANEL_THICKNESS

        # Create the enclosure and external cut shape
        self.casing = self.create_casing()
        self.cut_shape = self.create_cut_shape()

    def create_casing(self) -> BuildPart:
        with BuildPart() as casing:
            # Create the outer box
            Box(self.width, self.length, self.height)
            # Hollow out the box
            offset(amount=-self.panel_thickness, mode=Mode.SUBTRACT)
        return casing

    def get_parts(self) -> list[Part]:
        # Assign name and color to the part
        self.casing.part.label = CasePart.CASING.value
        self.casing.part.color = Config.Puzzle.TRANSPARENT_CASE_COLOR

        return [self.casing.part]

    def create_cut_shape(self) -> BuildPart:
        # Create a box to ensure it cuts the path body properly
        flush_distance_tolerance = 0.4  # Ensure flush with case

        # Create the inner box to hollow out the outer box
        inner_width = (
            self.width - 2 * self.panel_thickness - 2 * flush_distance_tolerance
        )
        inner_length = (
            self.length - 2 * self.panel_thickness - 2 * flush_distance_tolerance
        )
        inner_height = (
            self.height - 2 * self.panel_thickness - 2 * flush_distance_tolerance
        )

        # Create cut shape part, part required for downstream
        with BuildPart() as cut_shape:
            # Extend the outer box sizes to ensure it cuts any external bodies
            box_outer = Box(self.width * 2, self.length * 2, self.height * 2)
            # Cut internals, include panel thickness and tolerance
            box_inner = Box(inner_width, inner_length, inner_height)
            # Hollow out the box
            add(box_outer - box_inner, mode=Mode.REPLACE)

        return cut_shape


if __name__ == "__main__":
    CaseBox().preview()
