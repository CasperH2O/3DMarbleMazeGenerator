# shapes/case_sphere_with_flange_enclosed_two_sides.py

from .case_base import CaseBase
import cadquery as cq
import math
from config import Config


class CaseSphereWithFlangeEnclosedTwoSides(CaseBase):
    def __init__(self):
        self.sphere_outer_diameter = Config.Sphere.SPHERE_DIAMETER
        self.sphere_flange_diameter = Config.Sphere.SPHERE_FLANGE_DIAMETER
        self.sphere_thickness = Config.Sphere.SHELL_THICKNESS
        self.mounting_ring_thickness = Config.Sphere.MOUNTING_RING_THICKNESS
        self.ball_diameter = Config.Puzzle.BALL_DIAMETER
        self.mounting_hole_diameter = Config.Sphere.MOUNTING_HOLE_DIAMETER
        self.mounting_hole_amount = Config.Sphere.MOUNTING_HOLE_AMOUNT
        self.node_size = Config.Puzzle.NODE_SIZE
        self.number_of_mounting_points = Config.Sphere.NUMBER_OF_MOUNTING_POINTS
        self.mounting_distance = Config.Sphere.SPHERE_DIAMETER - Config.Puzzle.NODE_SIZE

        # Derived variables
        self.sphere_inner_diameter = self.sphere_outer_diameter - (2 * self.sphere_thickness)
        self.sphere_outer_radius = self.sphere_outer_diameter / 2
        self.sphere_inner_radius = self.sphere_inner_diameter / 2
        self.sphere_flange_radius = self.sphere_flange_diameter / 2

        # Create the components
        self.mounting_ring, self.path_bridges = self.create_mounting_ring()
        self.dome_top, self.dome_bottom = self.create_domes()
        self.add_mounting_holes()

    def create_mounting_ring(self):
        # Create the mounting ring
        mounting_ring = (
            cq.Workplane("XY")
            .circle(self.sphere_flange_radius)  # Outer circle
            .circle(self.sphere_inner_radius)  # Inner circle (hole)
            .extrude(self.mounting_ring_thickness)  # Extrude thickness
        )
        # Move to center in Z
        mounting_ring = mounting_ring.translate((0, 0, -0.5 * self.mounting_ring_thickness))

        # Add rectangular mounting bridges for the mounting ring, skipping the first one and rotating 180 degrees
        mounting_ring_bridges = (
            cq.Workplane("XY")
            .polarArray(self.mounting_distance / 2, 180, 360, self.number_of_mounting_points)[1:]  # Skip the first rectangle and start at 180 degrees
            .rect(self.node_size * 2, self.node_size)  # Define the rectangle
            .extrude(self.mounting_ring_thickness / 2, both=True)  # Extrude symmetrically
        )

        # Add rectangular mounting bridges for the path within, skipping the first one and rotating 180 degrees
        printing_layer_thickness = Config.Manufacturing.LAYER_THICKNESS
        printing_nozzle_diameter = Config.Manufacturing.NOZZLE_DIAMETER

        path_bridges = (
            cq.Workplane("XY")
            .polarArray(self.mounting_distance / 2, 180, 360, self.number_of_mounting_points)[1:]  # Skip the first rectangle and start at 180 degrees
            .rect(self.node_size * 2 + 4 * printing_nozzle_diameter, self.node_size - 4 * printing_nozzle_diameter)  # Define the rectangle
            .extrude(self.mounting_ring_thickness / 2 - printing_layer_thickness * 4, both=True)  # Extrude symmetrically
        )

        # Combine the ring and the nodes, cut out path bridge
        path_bridges = path_bridges.cut(mounting_ring)
        mounting_ring = mounting_ring.union(mounting_ring_bridges.cut(path_bridges))

        return mounting_ring, path_bridges

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
        dome_top = dome_profile.revolve(angleDegrees=360, axisStart=(0, 0, 0), axisEnd=(0, 1, 0))

        # Move to make place for mounting ring
        # Add small distance to prevent overlap artifacts during rendering
        dome_top = dome_top.translate((0, 0, 0.5 * self.mounting_ring_thickness + 0.01))

        # Mirror the dome for the other side
        dome_bottom = dome_top.mirror(mirrorPlane="XY")

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
            .polarArray(hole_pattern_radius, 45, 360, self.mounting_hole_amount, fill=True)
            .circle(self.mounting_hole_diameter / 2)
            .extrude(3 * self.sphere_thickness, both=True)  # Extrude length sufficient to cut through the bodies
        )

        # Cut the holes in applicable bodies
        self.mounting_ring = self.mounting_ring.cut(holes)
        self.dome_top = self.dome_top.cut(holes)
        self.dome_bottom = self.dome_bottom.cut(holes)

    def get_cad_objects(self):
        return {
            "Mounting Ring": (self.mounting_ring, {"alpha": 0.0, "color": Config.Puzzle.MOUNTING_RING_COLOR}),
            "Dome Top": (self.dome_top, {"alpha": 0.05, "color":(1, 1, 1)}),
            "Dome Bottom": (self.dome_bottom, {"alpha": 0.05, "color": (1, 1, 1)}),
            "Path Bridge": (self.path_bridges, {"color": Config.Puzzle.PATH_COLOR}),
        }

    def get_cut_shape(self):
        # Add small distance for tolerances
        flush_distance_tolerance = 0.0

        # Define the outer and inner radii
        R_outer = self.sphere_flange_diameter
        R_inner = self.sphere_inner_radius - flush_distance_tolerance

        # Calculate the midpoint for the outer arc
        mid_outer_x = R_outer / math.sqrt(2)
        mid_outer_y = R_outer / math.sqrt(2)

        # Calculate the midpoint for the inner arc
        mid_inner_x = R_inner / math.sqrt(2)
        mid_inner_y = R_inner / math.sqrt(2)

        # Create the cross-sectional profile of the hollow sphere
        hollow_sphere_profile = (
            cq.Workplane("XZ")
            # Start at point A: (0, R_outer)
            .moveTo(0, R_outer)
            # Draw the outer quarter-circle arc from A to B: (R_outer, 0), via midpoint
            .threePointArc((mid_outer_x, mid_outer_y), (R_outer, 0))
            # Draw a vertical line down to the inner radius at point C: (R_outer, R_inner)
            .lineTo(R_inner, 0)
            # Draw the inner quarter-circle arc from C to D: (0, R_inner), via midpoint
            .threePointArc((mid_inner_x, mid_inner_y), (0, R_inner))
            # Close the profile
            .close()
        )

        # Revolve the profile to create the hollow sphere solid
        hollow_sphere_top = hollow_sphere_profile.revolve(angleDegrees=360, axisStart=(0, 0, 0), axisEnd=(0, 1, 0))

        # Mirror the sphere for the other side
        hollow_sphere_bottom = hollow_sphere_top.mirror(mirrorPlane="XY")

        # Compensate for the original translation amount in create_domes
        translation_z = (0.5 * self.mounting_ring_thickness + 0.01) - 0.33333 * self.mounting_ring_thickness

        # Adjust the domes by translating them along the Z-axis
        hollow_sphere_top = hollow_sphere_top.translate((0, 0, translation_z))
        hollow_sphere_bottom = hollow_sphere_bottom.translate((0, 0, -translation_z))

        # Combine the domes using union
        cut_shape = hollow_sphere_top.union(hollow_sphere_bottom)

        return cut_shape
