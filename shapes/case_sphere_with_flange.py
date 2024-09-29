# shapes/case_sphere_with_flange.py

from .case_base import CaseBase
import cadquery as cq
import math


class CaseSphereWithFlange(CaseBase):
    def __init__(self, config):
        self.sphere_outer_diameter = config.SPHERE_DIAMETER
        self.sphere_flange_diameter = config.SPHERE_FLANGE_DIAMETER
        self.sphere_thickness = config.SHELL_THICKNESS
        self.ring_thickness = config.RING_THICKNESS
        self.ball_diameter = config.BALL_DIAMETER
        self.mounting_hole_diameter = config.MOUNTING_HOLE_DIAMETER
        self.mounting_hole_amount = config.MOUNTING_HOLE_AMOUNT

        # Derived variables
        self.sphere_inner_diameter = self.sphere_outer_diameter - (2 * self.sphere_thickness)
        self.sphere_outer_radius = self.sphere_outer_diameter / 2
        self.sphere_inner_radius = self.sphere_inner_diameter / 2
        self.sphere_flange_radius = self.sphere_flange_diameter / 2

        # Create the components
        self.mounting_ring = self.create_mounting_ring()
        self.dome_top, self.dome_bottom = self.create_domes()
        self.add_mounting_holes()

    def create_mounting_ring(self):
        # Create the mounting ring as a difference between two circles, then extrude symmetrically
        mounting_ring = (
            cq.Workplane("XY")
            .circle(self.sphere_flange_radius)          # Outer circle
            .circle(self.sphere_inner_radius)          # Inner circle (hole)
            .extrude(self.sphere_thickness)   # Extrude thickness
        )
        # Move to center
        mounting_ring = mounting_ring.translate((0, 0, -0.5 * self.sphere_thickness))
        return mounting_ring

    def create_domes(self):
        # Calculate the intermediate point at 45 degrees (π/4 radians)
        angle_45 = math.radians(45)

        # Intermediate points for inner arc
        x_mid_inner = self.sphere_inner_radius * math.cos(angle_45)

        # Calculate adjusted starting point for outer arc
        x_start_outer = math.sqrt(self.sphere_outer_radius**2 - self.sphere_thickness**2)
        y_start_outer = self.sphere_thickness  # Given

        # Calculate angle for adjusted starting point
        theta_start = math.asin(y_start_outer / self.sphere_outer_radius)

        # Calculate intermediate point for outer arc
        theta_mid_outer = (theta_start + math.pi / 2) / 2
        x_mid_outer = self.sphere_outer_radius * math.cos(theta_mid_outer)
        y_mid_outer = self.sphere_outer_radius * math.sin(theta_mid_outer)

        # Create the profile on the XZ plane
        dome_profile = (
            cq.Workplane("XZ")
            # Start at the outer circle top
            .moveTo(0, self.sphere_outer_radius)  # Point A
            .lineTo(0, self.sphere_inner_radius)  # Line down to Point B
            .threePointArc((x_mid_inner, self.sphere_inner_radius * math.sin(angle_45)), (self.sphere_inner_radius, 0))  # Inner arc to Point C
            .lineTo(self.sphere_flange_radius, 0)  # Line to Point D
            .lineTo(self.sphere_flange_radius, self.sphere_thickness)  # Line up to Point E
            .lineTo(x_start_outer, y_start_outer)  # Line to adjusted starting point for outer arc (Point F)
            .threePointArc((x_mid_outer, y_mid_outer), (0, self.sphere_outer_radius))  # Outer arc back to Point A
            .close()
        )

        # Revolve the dome profile
        dome_bottom = dome_profile.revolve(angleDegrees=360, axisStart=(0, 0, 0), axisEnd=(0, 1, 0))

        # Move to make place for mounting ring
        # Add small distance to prevent overlap artifacts during rendering
        dome_bottom = dome_bottom.translate((0, 0, 0.5 * self.ring_thickness + 0.01))

        # Mirror the dome for the other side
        dome_top = dome_bottom.mirror(mirrorPlane="XY")

        return dome_top, dome_bottom

    def add_mounting_holes(self):
        # Calculate the hole pattern radius
        hole_pattern_radius = (self.sphere_outer_radius + self.sphere_flange_radius) / 2  # Average radius

        # Create a work plane on the XY plane
        wp = cq.Workplane("XY")

        # Define the hole pattern
        holes = (
            wp
            .workplane()
            .polarArray(hole_pattern_radius, 0, 360, self.mounting_hole_amount, fill=True)
            .circle(self.mounting_hole_diameter / 2)
            .extrude(3 * self.sphere_thickness, both=True)  # Extrude length sufficient to cut through the bodies
        )

        # Cut the holes in applicable bodies
        self.mounting_ring = self.mounting_ring.cut(holes)
        self.dome_top = self.dome_top.cut(holes)
        self.dome_bottom = self.dome_bottom.cut(holes)

    def get_cad_objects(self):
        return {
            "Mounting Ring": self.mounting_ring,
            "Dome Top": (self.dome_top, {"alpha": 0.9, "color": (1, 1, 1)}),
            "Dome Bottom": (self.dome_bottom, {"alpha": 0.9, "color": (1, 1, 1)}),
        }
