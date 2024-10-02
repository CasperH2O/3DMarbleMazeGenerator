# shapes/case_sphere.py

from .case_base import CaseBase
import cadquery as cq

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

    def get_cut_shape(self):
        # Create the cross-sectional profile of the hollow sphere
        hollow_sphere_profile = (
            cq.Workplane("XZ")
            .moveTo(0, self.outer_radius * 2)
            .threePointArc((-self.outer_radius * 2, 0), (0, -self.outer_radius * 2))
            .lineTo(0, -self.inner_radius)
            .threePointArc((-self.inner_radius, 0), (0, self.inner_radius))
            .close()
        )

        # Revolve the profile to create the hollow sphere solid
        hollow_sphere = hollow_sphere_profile.revolve(angleDegrees=360)
        return hollow_sphere
