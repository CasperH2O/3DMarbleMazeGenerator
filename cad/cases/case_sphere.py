# cad/cases/case_sphere.py

from build123d import (
    BuildLine,
    BuildPart,
    BuildSketch,
    Line,
    Mode,
    Plane,
    Sphere,
    ThreePointArc,
    make_face,
    offset,
    revolve,
)

from config import Config

from .case_base import CaseBase


class CaseSphere(CaseBase):
    def __init__(self):
        self.diameter = Config.Sphere.SPHERE_DIAMETER
        self.shell_thickness = Config.Sphere.SHELL_THICKNESS
        self.inner_radius = (self.diameter / 2) - self.shell_thickness
        self.outer_radius = self.diameter / 2

        self.casing = self.create_casing()
        self.cut_shape = self.create_cut_shape()

    def create_casing(self):
        with BuildPart() as casing:
            # Create an initial sphere
            Sphere(self.outer_radius)
            # Hollow out the sphere
            offset(amount=-Config.Sphere.SHELL_THICKNESS, mode=Mode.SUBTRACT)
        return casing

    def get_parts(self):
        # Assign name and color to the casing part
        self.casing.part.name = "Casing"
        self.casing.part.color = "#FFFFFF0D"  # (1,1,1) with alpha 0.05

        return {
            "Casing": self.casing.part,
        }

    def create_cut_shape(self):
        flush_distance_tolerance = (
            0.0  # Small distance to ensure the cut shape is flush with the casing
        )
        with BuildPart() as cut_shape:
            # Create the cross-sectional profile, shaped like a C
            with BuildSketch(Plane.XZ):
                with BuildLine(Plane.XZ):
                    Line(
                        (0, self.inner_radius + flush_distance_tolerance),
                        (0, self.outer_radius * 2),
                    )
                    ThreePointArc(
                        (0, self.outer_radius * 2),
                        (-self.outer_radius * 2, 0),
                        (0, -self.outer_radius * 2),
                    )
                    Line(
                        (0, -self.outer_radius * 2),
                        (0, -self.inner_radius + flush_distance_tolerance),
                    )
                    ThreePointArc(
                        (0, -self.inner_radius + flush_distance_tolerance),
                        (-self.inner_radius + flush_distance_tolerance, 0),
                        (0, self.inner_radius - flush_distance_tolerance),
                    )
                make_face()
            revolve()

        return cut_shape
