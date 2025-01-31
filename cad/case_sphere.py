# cad/case_sphere.py

from build123d import *

from .case_base import CaseBase
from config import Config

class CaseSphere(CaseBase):
    def __init__(self):
        self.diameter = Config.Sphere.SPHERE_DIAMETER
        self.shell_thickness = Config.Sphere.SHELL_THICKNESS
        self.inner_radius = (self.diameter / 2) - self.shell_thickness
        self.outer_radius = self.diameter / 2

        # Create the sphere casing
        self.casing = self.create_casing()
        self.cut_shape = self.create_cut_shape()

    def create_casing(self):
        # Create the casing
        with BuildPart() as casing:
            # Create an initial sphere
            Sphere(self.outer_radius)
            # Hollow out the sphere
            offset(amount=-Config.Sphere.SHELL_THICKNESS, mode=Mode.SUBTRACT)

        return casing

    def get_cad_objects(self):
        return {
            "Casing": (self.casing, {"alpha": 0.05, "color": (1, 1, 1)}),
        }

    def create_cut_shape(self):
        # Add small distance for tolerances
        flush_distance_tolerance = 0.0

        # Create the cross-sectional profile of the hollow sphere
        with BuildPart() as cut_shape:
            with BuildSketch(Plane.XZ):
                with BuildLine(Plane.XZ):
                    # Create the cross-sectional profile, shaped like a C
                    Line((0, self.inner_radius + flush_distance_tolerance), (0, self.outer_radius * 2))
                    ThreePointArc((0, self.outer_radius * 2), (-self.outer_radius * 2, 0), (0, -self.outer_radius * 2))
                    Line((0, -self.outer_radius * 2), (0, -self.inner_radius + flush_distance_tolerance))
                    ThreePointArc((0, -self.inner_radius + flush_distance_tolerance), (-self.inner_radius + flush_distance_tolerance, 0), (0, self.inner_radius - flush_distance_tolerance))
                make_face()
            revolve()

        return cut_shape