# cad/cases/case_sphere.py

from build123d import (
    BuildPart,
    Mode,
    Part,
    Sphere,
    add,
    offset,
)

from cad.cases.case import Case, CasePart
from config import Config


class CaseSphere(Case):
    def __init__(self):
        self.diameter = Config.Sphere.SPHERE_DIAMETER
        self.shell_thickness = Config.Sphere.SHELL_THICKNESS

        self.inner_radius = (self.diameter / 2) - self.shell_thickness
        self.outer_radius = self.diameter / 2

        self.casing = self.create_casing()
        self.cut_shape = self.create_cut_shape()
        self.base_parts = self._create_circular_base_parts(
            sphere_diameter=self.diameter,
            top_color=Config.Puzzle.PATH_COLORS[0],
            bottom_color=Config.Puzzle.MOUNTING_RING_COLOR,
            edge_color=Config.Puzzle.PATH_ACCENT_COLOR,
        )

    def create_casing(self) -> BuildPart:
        with BuildPart() as casing:
            # Create an initial sphere
            Sphere(self.outer_radius)
            # Hollow out the sphere
            offset(amount=-self.shell_thickness, mode=Mode.SUBTRACT)
        return casing

    def get_parts(self) -> list[Part]:
        # Assign name and color to the casing part
        self.casing.part.label = CasePart.CASING.value
        self.casing.part.color = Config.Puzzle.TRANSPARENT_CASE_COLOR

        return [self.casing.part]

    def get_base_parts(self) -> list[Part]:
        return self.base_parts

    def create_cut_shape(self) -> BuildPart:
        flush_distance_tolerance = 0.4  # Ensure flush with case

        with BuildPart() as cut_shape:
            # Larger outer sphere to cut off excess bodies
            sphere_outer = Sphere(self.outer_radius * 2)
            sphere_inner = Sphere(self.inner_radius - flush_distance_tolerance)
            # Hollow out the sphere
            add(sphere_outer - sphere_inner, mode=Mode.REPLACE)

        return cut_shape


if __name__ == "__main__":
    CaseSphere().preview()
