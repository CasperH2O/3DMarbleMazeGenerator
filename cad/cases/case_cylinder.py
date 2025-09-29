# cad/cases/case_cylinder.py

from build123d import BuildPart, Cylinder, Mode, Part, add, offset

from cad.cases.case import Case, CasePart
from config import Config


class CaseCylinder(Case):
    def __init__(self):
        self.diameter = Config.Cylinder.DIAMETER
        self.height = Config.Cylinder.HEIGHT
        self.panel_thickness = Config.Cylinder.SHELL_THICKNESS

        # Create the enclosure and external cut shape
        self.casing = self.create_casing()
        self.cut_shape = self.create_cut_shape()

    def create_casing(self) -> BuildPart:
        with BuildPart() as casing:
            # Create the case
            Cylinder(radius=self.diameter / 2, height=self.height)
            # Hollow out the case
            offset(amount=-self.panel_thickness, mode=Mode.SUBTRACT)
        return casing

    def get_parts(self) -> list[Part]:
        # Assign name and color to the part
        self.casing.part.label = CasePart.CASING.value
        self.casing.part.color = Config.Puzzle.TRANSPARENT_CASE_COLOR

        return [self.casing.part]

    def create_cut_shape(self) -> BuildPart:
        # Create a shape around the casing to ensure it cuts the path body properly
        flush_distance_tolerance = 0.4  # Ensure flush with case

        # Inner case sizes to hollow out the outer case
        inner_diameter = (
            self.diameter - 2 * self.panel_thickness - 2 * flush_distance_tolerance
        )
        inner_height = (
            self.height - 2 * self.panel_thickness - 2 * flush_distance_tolerance
        )

        # Create cut shape part, part required for downstream
        with BuildPart() as cut_shape:
            # Extend the outer case sizes to ensure it cuts any external bodies
            cylinder_outer = Cylinder(radius=self.diameter, height=self.height * 2)
            # Cut internals, include panel thickness and tolerance
            box_inner = Cylinder(radius=inner_diameter / 2, height=inner_height)
            # Hollow out the case
            add(cylinder_outer - box_inner, mode=Mode.REPLACE)

        return cut_shape


if __name__ == "__main__":
    CaseCylinder().preview()
