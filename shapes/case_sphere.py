# shapes/case_sphere.py

from .case_base import CaseBase
import cadquery as cq
from config import Config

class CaseSphere(CaseBase):
    def __init__(self):
        self.diameter = Config.Sphere.SPHERE_DIAMETER
        self.shell_thickness = Config.Sphere.SHELL_THICKNESS
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
            "Casing": (self.casing, {"alpha": 0.9, "color": (1, 1, 1)}),
        }

    def get_cut_shape(self):
        # Add small distance for tolerances
        flush_distance_tolerance = 0.0

        # Create the cross-sectional profile of the hollow sphere
        hollow_sphere_profile = (
            cq.Workplane("XZ")
            .moveTo(0, self.outer_radius * 2)
            .threePointArc((-self.outer_radius * 2, 0), (0, -self.outer_radius * 2))
            .lineTo(0, -self.inner_radius + flush_distance_tolerance)
            .threePointArc((-self.inner_radius + flush_distance_tolerance, 0), (0, self.inner_radius - flush_distance_tolerance))
            .close()
        )

        # Revolve the profile to create the hollow sphere solid
        hollow_sphere = hollow_sphere_profile.revolve(angleDegrees=360)
        return hollow_sphere
