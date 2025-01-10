# cad/case_sphere_with_flange_enclosed_two_sides.py

from .case_base import CaseBase
from build123d import *
import math
from ocp_vscode import *
from copy import deepcopy, copy

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
        self.mounting_ring, self.path_bridges, self.start_text = self.create_mounting_ring()
        self.dome_top, self.dome_bottom = self.create_domes()
        self.cut_shape = self.create_cut_shape()
        self.cut_mounting_holes()

    def create_mounting_ring(self):
        
        # Build the mounting ring
        with BuildPart() as mounting_ring:
            Cylinder(self.sphere_flange_radius, self.mounting_ring_thickness) # Outer circle
            Cylinder(self.sphere_inner_radius, self.mounting_ring_thickness, mode=Mode.SUBTRACT) # Inner circle

        # Build the start indicator
        with BuildPart() as start_indicator:
            # Start indicator, generate a triangle in the start area funnel
            pass

        # Add mounting bridges with an outer bridge that connects to 
        # the mounting ring and an inner bridge that connects to the path
        # Skip the first location as that is the start area
        num_points = self.number_of_mounting_points
        start_angle = 360 / num_points + 180   
        count = num_points - 1                  
        angle_range = 360 - 360 / num_points

        printing_layer_thickness = Config.Manufacturing.LAYER_THICKNESS
        printing_nozzle_diameter = Config.Manufacturing.NOZZLE_DIAMETER

        # Build the external mounting ring bridges
        with BuildPart() as mounting_ring_bridges:
            with PolarLocations(radius=self.mounting_distance/2, 
                                count=count, 
                                start_angle=start_angle, 
                                angular_range=angle_range):
                Box(
                    width=self.node_size,
                    length=self.node_size * 2,
                    height=self.mounting_ring_thickness
                )

        # Build the internal path bridges
        with BuildPart() as path_bridges:
            with PolarLocations(radius=self.mounting_distance/2, 
                                count=count, 
                                start_angle=start_angle, 
                                angular_range=angle_range):
                Box(
                    width=self.node_size - 4 * printing_nozzle_diameter,
                    length=self.node_size * 2 + 4 * printing_nozzle_diameter,
                    height=self.mounting_ring_thickness - printing_layer_thickness * 8
                )

        # Combine the mounting ring with the external bridge, cut out internal path bridge
        path_bridges.part = path_bridges.part - mounting_ring.part
        mounting_ring.part = mounting_ring.part + (mounting_ring_bridges.part - path_bridges.part)

        return mounting_ring, path_bridges, start_indicator

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
        dome_top.part.position = (0, 0, 0.5 * self.mounting_ring_thickness)

        # Mirror the dome for the other side
        dome_bottom = copy(dome_top)
        dome_bottom.part = dome_bottom.part.mirror(Plane.XY)
        
        return dome_top, dome_bottom

    def cut_mounting_holes(self):
        # Calculate the hole pattern radius
        hole_pattern_radius = (self.sphere_outer_radius + self.sphere_flange_radius) / 2

        # Create the holes as a separate BuildPart
        with BuildPart() as holes:
            # Set up polar locations at the given radius and start angle
            with PolarLocations(radius=hole_pattern_radius,
                                count=self.mounting_hole_amount,
                                start_angle=45,     # start from 45 degrees as per the original code
                                angular_range=360):
                Cylinder(radius=self.mounting_hole_diameter / 2, height=self.sphere_thickness * 2 + self.mounting_ring_thickness)

        # Now subtract the holes from the existing parts
        self.mounting_ring.part = self.mounting_ring.part - holes.part
        self.dome_top.part = self.dome_top.part - holes.part
        self.dome_bottom.part = self.dome_bottom.part - holes.part

    def get_cad_objects(self):
        return {
            "Mounting Ring": (self.mounting_ring, {"alpha": 0.0, "color": Config.Puzzle.MOUNTING_RING_COLOR}),
            "Dome Top": (self.dome_top, {"alpha": 0.05, "color":(1, 1, 1)}),
            "Dome Bottom": (self.dome_bottom, {"alpha": 0.05, "color": (1, 1, 1)}),
            "Path Bridge": (self.path_bridges, {"color": Config.Puzzle.PATH_COLOR}),
            "Start Indicator": (self.start_text, {"color": Config.Puzzle.TEXT_COLOR}),
        }

    def create_cut_shape(self):
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

        with BuildPart() as cut_shape:
            with BuildSketch(Plane.XZ):
                with BuildLine(Plane.XZ):
                    # Outer arc
                    ThreePointArc((0, R_outer), (mid_outer_x, mid_outer_y), (R_outer, 0))
                    # Vertical line down to inner radius
                    Line((R_outer, 0), (R_inner, 0))
                    # Inner arc
                    ThreePointArc((R_inner, 0), (mid_inner_x, mid_inner_y), (0, R_inner))
                    # Close the loop by connecting back to (0,R_outer)
                    Line((0, R_inner), (0, R_outer))
                make_face()
            # Revolve the profile to create the hollow half sphere solid
            revolve()
            # Move to create gap, leave a small gap to create connection with start area
            translation_z = (0.5 * self.mounting_ring_thickness) - 0.33333 * self.mounting_ring_thickness
            cut_shape.part.position = (0, 0, -translation_z)
            # Mirror the top half to create the bottom half
            mirror(about=Plane.XY)           

        return cut_shape
