# shapes/case_sphere.py

from .case_base import CaseBase
import cadquery as cq
import math


class CaseSphere(CaseBase):
    def __init__(self, config):
        self.diameter = config.SPHERE_DIAMETER
        self.shell_thickness = config.SHELL_THICKNESS
        self.inner_radius = (self.diameter / 2) - self.shell_thickness
        self.outer_radius = self.diameter / 2

        # Create the sphere casing
        self.casing = self.create_casing()

    def create_casing(self):
        # Create the outer sphere
        outer_sphere = cq.Workplane("XY").sphere(self.outer_radius)

        # Create the inner sphere to hollow out the outer sphere
        inner_sphere = cq.Workplane("XY").sphere(self.inner_radius)

        # Subtract the inner sphere from the outer sphere
        casing = outer_sphere.cut(inner_sphere)
        return casing

    def get_cad_objects(self):
        return {
            "casing": (self.casing, {"alpha": 0.9, "color": (1, 1, 1)}),
        }
