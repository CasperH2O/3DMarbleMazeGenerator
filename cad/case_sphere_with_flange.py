# cad/case_sphere_with_flange.py

from .case_base import CaseBase
from build123d import *
import math
from ocp_vscode import *

from config import Config

class CaseSphereWithFlange(CaseBase):
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
        self.mounting_ring, self.path_bridges, self.start_text = self.create_mounting_ring()
        self.dome_top, self.dome_bottom = self.create_domes()
        #self.add_mounting_holes()

    def create_mounting_ring(self):
        
        # Build the mounting ring
        with BuildPart() as mounting_ring:
            Cylinder(self.sphere_flange_radius, self.mounting_ring_thickness) # Outer circle
            Cylinder(self.sphere_inner_radius, self.mounting_ring_thickness, mode=Mode.SUBTRACT) # Inner circle

        # Build the start text
        with BuildPart() as start_text:
            with BuildSketch():
                text_radius = (self.sphere_outer_radius + self.sphere_flange_radius) / 2
                text_path = Circle(text_radius, mode=Mode.PRIVATE).edge().rotate(Axis((0, 0, 0), (0, 0, 1)), 180)
                Text(txt="START", font_size=8, path=text_path)
            extrude(amount=-1)

        # Position the text at the top surface of the ring
        start_text.part.position = (0, 0, 0.5 * self.mounting_ring_thickness)

        # Subtract the text from the mounting ring
        mounting_ring.part = mounting_ring.part - start_text.part

        show_all()  

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

        return mounting_ring, path_bridges, start_text

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

        # Create dome top part
        with BuildPart() as dome_top:
            with BuildSketch(Plane.XZ):
                with BuildLine(Plane.XZ):
                    l1 = Line((0, self.sphere_outer_radius), (0, self.sphere_inner_radius))
                    l2 = ThreePointArc((0, self.sphere_inner_radius),(x_mid_inner, self.sphere_inner_radius * math.sin(angle_45)), (self.sphere_inner_radius, 0))
                    l3 = Line((self.sphere_inner_radius, 0), (self.sphere_flange_radius, 0))
                    l4 = Line((self.sphere_flange_radius, 0), (self.sphere_flange_radius, self.sphere_thickness))
                    l5 = Line((self.sphere_flange_radius, self.sphere_thickness), (x_start_outer, y_start_outer))
                    l6 = ThreePointArc((x_start_outer, y_start_outer), (x_mid_outer, y_mid_outer), (0, self.sphere_outer_radius))
                make_face()
            revolve()
        
        # Move to make place for mounting ring
        # Add small distance to prevent overlap artifacts during rendering with transparency
        dome_top.part.position = (0, 0, 0.5 * self.mounting_ring_thickness + 0.000)

        # Mirror the dome for the other side
        dome_bottom = dome_top
        dome_bottom = dome_bottom.part.mirror(Plane.XY)

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
            .extrude(self.sphere_thickness + self.mounting_ring_thickness / 2, both=True)  # Extrude length sufficient to cut through the bodies
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
            "Start Text": (self.start_text, {"color": Config.Puzzle.TEXT_COLOR}),
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
