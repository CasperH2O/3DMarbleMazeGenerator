# cad/case_sphere_with_flange_enclosed_two_sides.py

from .case_base import CaseBase
from build123d import *
import math
from ocp_vscode import *
from copy import copy

from config import Config


class CaseSphereWithFlangeEnclosedTwoSides(CaseBase):
    def __init__(self):
        self.sphere_outer_diameter = Config.Sphere.SPHERE_DIAMETER
        self.sphere_flange_diameter = Config.Sphere.SPHERE_FLANGE_DIAMETER
        self.sphere_flange_inner_diameter = Config.Sphere.SPHERE_FLANGE_INNER_DIAMETER
        self.sphere_flange_slot_angle = Config.Sphere.SPHERE_FLANGE_SLOT_ANGLE
        self.sphere_thickness = Config.Sphere.SHELL_THICKNESS
        self.mounting_ring_thickness = Config.Sphere.MOUNTING_RING_THICKNESS
        self.mounting_ring_edge = Config.Sphere.MOUNTING_RING_EDGE
        self.mounting_ring_inner_height = Config.Sphere.MOUNTING_RING_INNER_HEIGHT
        self.ball_diameter = Config.Puzzle.BALL_DIAMETER
        self.mounting_hole_diameter = Config.Sphere.MOUNTING_HOLE_DIAMETER
        self.mounting_hole_amount = Config.Sphere.MOUNTING_HOLE_AMOUNT
        self.node_size = Config.Puzzle.NODE_SIZE
        self.number_of_mounting_points = Config.Sphere.NUMBER_OF_MOUNTING_POINTS
        self.mounting_bridge_height = Config.Sphere.MOUNTING_BRIDGE_HEIGHT
        self.mounting_distance = Config.Sphere.SPHERE_DIAMETER - Config.Puzzle.NODE_SIZE

        # Derived variables
        self.sphere_inner_diameter = self.sphere_outer_diameter - (2 * self.sphere_thickness)
        self.sphere_outer_radius = self.sphere_outer_diameter / 2
        self.sphere_inner_radius = self.sphere_inner_diameter / 2
        self.sphere_flange_radius = self.sphere_flange_diameter / 2
        self.sphere_flange_inner_radius = self.sphere_flange_inner_diameter / 2

        # Create the components
        self.mounting_ring, self.path_bridges, self.start_indcator = self.create_mounting_ring()
        self.dome_top, self.dome_bottom = self.create_domes()
        self.cut_shape = self.create_cut_shape()

    def create_mounting_ring(self):
        
        # Build the mounting ring
        with BuildPart() as mounting_ring_bottom:
            
            # Create the outer ring
            Cylinder(radius=self.sphere_flange_radius, height=self.mounting_ring_thickness)
            Cylinder(radius=self.sphere_flange_inner_radius, height=self.mounting_ring_thickness, mode=Mode.SUBTRACT)
            Cylinder(radius=self.sphere_flange_radius - self.mounting_ring_edge, height=self.mounting_ring_inner_height, mode=Mode.SUBTRACT)
            
            split(bisect_by=Plane.XY, keep=Keep.BOTTOM) # Split and keep one side, which is later copied and rotated (twice)

            # Create pegs
            peg_radius = self.sphere_flange_inner_radius + ((self.sphere_flange_radius - self.mounting_ring_edge) - self.sphere_flange_inner_radius) / 2
            peg_tolerance = 0.1

            # Pegs with holes
            with PolarLocations(radius=peg_radius, 
                                count=round(self.number_of_mounting_points / 2), 
                                start_angle=self.sphere_flange_slot_angle, 
                                angular_range=360) as peg_with_hole_locations:
                Cylinder(
                    radius=2,
                    height=self.mounting_ring_inner_height
                )

                Cylinder(
                    radius=1.2 + peg_tolerance,
                    height=self.mounting_ring_inner_height,
                    mode=Mode.SUBTRACT
                )

            with PolarLocations(radius=peg_radius, 
                                count=round(self.number_of_mounting_points / 2), 
                                start_angle=-self.sphere_flange_slot_angle + 360 / self.number_of_mounting_points, 
                                angular_range=360) as peg_with_hole_locations_mirrored:
                Cylinder(
                    radius=2,
                    height=self.mounting_ring_inner_height
                )

                Cylinder(
                    radius=1.2 + peg_tolerance,
                    height=self.mounting_ring_inner_height,
                    mode=Mode.SUBTRACT
                )     

            # Reduce height of pegs with holes
            split(bisect_by=Plane.XY, keep=Keep.BOTTOM)

            # Regular pegs
            with PolarLocations(radius=peg_radius, 
                                count=round(self.number_of_mounting_points / 2), 
                                start_angle=-self.sphere_flange_slot_angle, 
                                angular_range=360) as peg_locations:
                Cylinder(
                    radius=1.2,
                    height=self.mounting_ring_inner_height
                )

            with PolarLocations(radius=peg_radius, 
                                count=round(self.number_of_mounting_points / 2), 
                                start_angle=self.sphere_flange_slot_angle + 360 / self.number_of_mounting_points, 
                                angular_range=360) as peg_locations_mirrored:
                Cylinder(
                    radius=1.2,
                    height=self.mounting_ring_inner_height
                )               

            # Reduce height of the pegs
            height_reduction_plane = Plane(mounting_ring_bottom.faces().sort_by(Axis.Z)[-1]).offset(-Config.Manufacturing.LAYER_THICKNESS * 2)
            split(bisect_by=height_reduction_plane, keep=Keep.BOTTOM)

        # Flip mounting ring and rotate for the next set of peg/hole
        mounting_ring_top = copy(mounting_ring_bottom)
        mounting_ring_top.part = mounting_ring_top.part.rotate(Axis((0, 0, 0), (0, 1, 0)), 180) # Flip upside down
        mounting_ring_top.part = mounting_ring_top.part.rotate(Axis((0, 0, 0), (0, 0, 1)), 360 / self.number_of_mounting_points) # Rotate to next set

        #show_all()

        mounting_ring = copy(mounting_ring_bottom)
        mounting_ring.part = mounting_ring_top.part + mounting_ring_bottom.part

        # Export
        #export_stl(to_export=mounting_ring_bottom.part,file_path="MountingRingBottom.stl")

        # Build the start indicator
        with BuildPart() as start_indicator:
            with BuildSketch():
                text_radius = (self.sphere_outer_radius + self.sphere_flange_radius) / 2
                text_path = Circle(text_radius, mode=Mode.PRIVATE).edge().rotate(Axis((0, 0, 0), (0, 0, 1)), 180)
                Text(txt="^", font_size=8, path=text_path)
            extrude(amount=-1)

        # Add mounting bridges with an outer bridge that connects to 
        # the mounting ring and an inner bridge that connects to the path
        # Skip the first location as that is the start area
        num_points = self.number_of_mounting_points
        start_angle = 360 / num_points + 180   
        count = num_points - 1                  
        angle_range = 360 - 360 / num_points

        printing_layer_thickness = Config.Manufacturing.LAYER_THICKNESS
        printing_nozzle_diameter = Config.Manufacturing.NOZZLE_DIAMETER

        # Build the external bridge ring
        with BuildPart() as bridge_ring:
            tolerance = 0.2

            # Build an external ring
            Cylinder(radius=self.sphere_flange_radius - self.mounting_ring_edge - tolerance, height=self.mounting_bridge_height - tolerance)
            Cylinder(radius=self.sphere_flange_inner_radius, height=self.mounting_bridge_height - tolerance, mode=Mode.SUBTRACT)

        # Build the external bridges
        with BuildPart() as external_bridges:          
            with PolarLocations(radius=self.mounting_distance/2, 
                                count=count, 
                                start_angle=start_angle, 
                                angular_range=angle_range):
                Box(
                    width=self.node_size,
                    length=self.node_size * 2,
                    height=self.mounting_bridge_height - tolerance
                )

        # Create peg holes for later subtraction
        with BuildPart() as peg_holes:
            # Reusing the peg coordinates
            hole_locations = peg_locations.locations + peg_locations_mirrored.locations + peg_with_hole_locations.locations + peg_with_hole_locations_mirrored.locations

            with Locations(hole_locations):
                Cylinder(
                    radius=2 + tolerance,
                    height=self.mounting_ring_inner_height - tolerance,
                )

        # Build the internal path bridges
        with BuildPart() as internal_path_bridges:
            with PolarLocations(radius=self.mounting_distance/2, 
                                count=count, 
                                start_angle=start_angle, 
                                angular_range=angle_range):
                Box(
                    width=self.node_size - 4 * printing_nozzle_diameter,
                    length=self.node_size * 2 + 4 * printing_nozzle_diameter,
                    height=self.mounting_bridge_height - printing_layer_thickness * 8
                )

        # Cut the ring off the inner path bridges, keep inner bridge shapes
        internal_path_bridges.part = internal_path_bridges.part - bridge_ring.part
        internal_path_bridges.part = internal_path_bridges.part.solids().sort_by(SortBy.VOLUME)[-count:]

        # Combine ring and outer bridges
        bridge_ring.part = bridge_ring.part + external_bridges.part

        # Apply fillet, restore bridges we don't want filleted
        bridge_ring.part = fillet(bridge_ring.part.edges().filter_by(Axis.Z), radius=4)      
        bridge_ring.part = bridge_ring.part + external_bridges.part

        # Cut out peg holes
        bridge_ring.part = bridge_ring.part - peg_holes.part - internal_path_bridges.part

        # Build the mounting ring clips
        mounting_clip_radius = self.sphere_flange_inner_radius + (self.sphere_flange_radius - self.sphere_flange_inner_radius) / 2
        
        with BuildPart() as mounting_ring_clips:
            with PolarLocations(
                    radius=mounting_clip_radius, 
                    count=num_points, 
                    start_angle=start_angle, 
                    angular_range=360):
                Box(
                    width=14,
                    length=20, # Get's cut off at both sides
                    height=self.mounting_ring_thickness + 2 * 1.6 # TODO turn 1.6 into config variable
                )
            # Subtract the inside part out of the clip
            Cylinder(self.sphere_flange_radius, self.mounting_ring_thickness, mode=Mode.SUBTRACT)

            # Subtract the side of the clip that is against the domes
            Cylinder(self.sphere_flange_inner_radius, self.mounting_ring_thickness + 2 * 1.6, mode=Mode.SUBTRACT)

        # Build the shape to cut off from the outside of the mounting ring clips
        with BuildPart() as mounting_ring_clips_outer_cut:
            Cylinder(self.sphere_flange_radius + 5 * 1.6, self.mounting_ring_thickness + 2 * 1.6) # Outer circle
            Cylinder(self.sphere_flange_radius + 1.6, self.mounting_ring_thickness + 2 * 1.6, mode=Mode.SUBTRACT) # Inner circle

        mounting_ring_clips.part = mounting_ring_clips.part - mounting_ring_clips_outer_cut.part

        return mounting_ring, internal_path_bridges, start_indicator

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
                    Line((0, self.sphere_outer_radius), (0, self.sphere_inner_radius))
                    ThreePointArc((0, self.sphere_inner_radius),(x_mid_inner, self.sphere_inner_radius * math.sin(angle_45)), (self.sphere_inner_radius, 0))
                    Line((self.sphere_inner_radius, 0), (self.sphere_flange_radius - self.mounting_ring_edge , 0))
                    Line((self.sphere_flange_radius - self.mounting_ring_edge , 0), (self.sphere_flange_radius - self.mounting_ring_edge , self.sphere_thickness))
                    Line((self.sphere_flange_radius - self.mounting_ring_edge , self.sphere_thickness), (x_start_outer, y_start_outer))
                    ThreePointArc((x_start_outer, y_start_outer), (x_mid_outer, y_mid_outer), (0, self.sphere_outer_radius))
                make_face()
            revolve()

            # Create the holes with fillets
            # Calculate the hole pattern radius
            hole_pattern_radius = (self.sphere_outer_radius + self.sphere_flange_radius) / 2 + 1

            # Set up polar locations at the given radius and start angle
            with PolarLocations(radius=hole_pattern_radius,
                                count=self.mounting_hole_amount,
                                start_angle=self.sphere_flange_slot_angle,     # start from 45 degrees as per the original code
                                angular_range=360):
                Cylinder(radius=self.mounting_hole_diameter / 2, height=self.sphere_thickness * 2, mode=Mode.SUBTRACT)
              
            # Mirored set of polar locations at the given radius and start angle
            with PolarLocations(radius=hole_pattern_radius,
                                count=self.mounting_hole_amount,
                                start_angle=-self.sphere_flange_slot_angle,     # start from 45 degrees as per the original code
                                angular_range=360):
                Cylinder(radius=self.mounting_hole_diameter / 2, height=self.sphere_thickness * 2, mode=Mode.SUBTRACT)     

            fillet(dome_top.edges().filter_by(Axis.Z), radius=2)
       
        # Move to make place for mounting ring
        dome_top.part.position = (0, 0, 0.5 * self.mounting_bridge_height)

        # Mirror the dome for the other side
        dome_bottom = copy(dome_top)
        dome_bottom.part = dome_bottom.part.mirror(Plane.XY)

        return dome_top, dome_bottom


    def get_cad_objects(self):
        return {
            "Mounting Ring": (self.mounting_ring, {"alpha": 0.0, "color": Config.Puzzle.MOUNTING_RING_COLOR}),
            "Dome Top": (self.dome_top, {"alpha": 0.05, "color":(1, 1, 1)}),
            "Dome Bottom": (self.dome_bottom, {"alpha": 0.05, "color": (1, 1, 1)}),
            "Path Bridge": (self.path_bridges, {"color": Config.Puzzle.PATH_COLOR}),
            "Start Indicator": (self.start_indcator, {"color": Config.Puzzle.TEXT_COLOR}),
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

