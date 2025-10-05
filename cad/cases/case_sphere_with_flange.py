# cad/cases/case_sphere_with_flange.py

import math
from copy import copy

from build123d import (
    Axis,
    Box,
    BuildLine,
    BuildPart,
    BuildSketch,
    Circle,
    Cylinder,
    Line,
    Locations,
    Mode,
    Part,
    Plane,
    PolarLocations,
    Text,
    ThreePointArc,
    extrude,
    make_face,
    mirror,
    revolve,
)

from cad.cases.case import Case, CasePart
from config import Config


class CaseSphereWithFlange(Case):
    def __init__(self):
        # Config
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
        self.sphere_inner_diameter = self.sphere_outer_diameter - (
            2 * self.sphere_thickness
        )
        self.sphere_outer_radius = self.sphere_outer_diameter / 2
        self.sphere_inner_radius = self.sphere_inner_diameter / 2
        self.sphere_flange_radius = self.sphere_flange_diameter / 2

        # Create parts
        self.base_parts = self._create_circular_base_parts(
            sphere_diameter=self.sphere_outer_diameter,
            top_color=Config.Puzzle.PATH_COLORS[0],
            bottom_color=Config.Puzzle.MOUNTING_RING_COLOR,
            edge_color=Config.Puzzle.PATH_ACCENT_COLOR,
        )
        self.mounting_ring, self.path_bridges, self.start_text = (
            self.create_mounting_ring()
        )
        self.dome_top, self.dome_bottom = self.create_domes()
        self.cut_shape = self.create_cut_shape()
        self.cut_mounting_holes()

    def create_mounting_ring(self):
        # Create mounting ring
        with BuildPart() as mounting_ring:
            Cylinder(self.sphere_flange_radius, self.mounting_ring_thickness)
            Cylinder(
                self.sphere_inner_radius,
                self.mounting_ring_thickness,
                mode=Mode.SUBTRACT,
            )

        # Add start text
        with BuildPart() as start_text:
            # Position the text at the top surface of the mounting ring
            with BuildSketch(Plane.XY.offset(0.5 * self.mounting_ring_thickness)):
                text_radius = (self.sphere_outer_radius + self.sphere_flange_radius) / 2
                text_path = (
                    Circle(text_radius, mode=Mode.PRIVATE)
                    .edge()
                    .rotate(Axis((0, 0, 0), (0, 0, 1)), 180)
                )
                Text(txt="START", font_size=8, path=text_path)
            extrude(amount=-1)

        # Subtract the text from the mounting ring
        mounting_ring.part = mounting_ring.part - start_text.part

        # Add mounting bridges with an outer bridge that connects to
        # the mounting ring and an inner bridge that connects to the path
        # Skip the first location as that is the start area
        num_points = self.number_of_mounting_points
        start_angle = 360 / num_points + 180
        count = num_points - 1
        angle_range = 360 - 360 / num_points

        printing_layer_thickness = Config.Manufacturing.LAYER_THICKNESS
        printing_nozzle_diameter = Config.Manufacturing.NOZZLE_DIAMETER

        bridge_locations = list(
            PolarLocations(
                radius=self.mounting_distance / 2,
                count=count,
                start_angle=start_angle,
                angular_range=angle_range,
            )
        )

        with BuildPart() as mounting_ring_bridges:
            with Locations(bridge_locations):
                Box(
                    width=self.node_size,
                    length=self.node_size * 2,
                    height=self.mounting_ring_thickness,
                )

        with BuildPart() as path_bridges:
            with Locations(bridge_locations):
                Box(
                    width=self.node_size - 4 * printing_nozzle_diameter,
                    length=self.node_size * 2 + 4 * printing_nozzle_diameter,
                    height=self.mounting_ring_thickness - printing_layer_thickness * 8,
                )

        # Combine path bridges and mounting ring
        path_bridges.part = path_bridges.part - mounting_ring.part
        mounting_ring.part = mounting_ring.part + (
            mounting_ring_bridges.part - path_bridges.part
        )

        return mounting_ring, path_bridges, start_text

    def create_domes(self):
        # Calculate the intermediate point at 45 degrees (π/4 radians)
        angle_45 = math.radians(45)

        # Intermediate points for the inner arc
        x_mid_inner = self.sphere_inner_radius * math.cos(angle_45)

        # Calculate the adjusted start point for the outer arc
        x_start_outer = math.sqrt(
            self.sphere_outer_radius**2 - self.sphere_thickness**2
        )

        # Calculate angle for adjusted starting point
        y_start_outer = self.sphere_thickness
        theta_start = math.asin(y_start_outer / self.sphere_outer_radius)

        # Calculate intermediate point for the outer arc
        theta_mid_outer = (theta_start + math.pi / 2) / 2
        x_mid_outer = self.sphere_outer_radius * math.cos(theta_mid_outer)
        y_mid_outer = self.sphere_outer_radius * math.sin(theta_mid_outer)

        # Create dome top
        with BuildPart() as dome_top:
            with BuildSketch(Plane.XZ):
                with BuildLine(Plane.XZ):
                    Line((0, self.sphere_outer_radius), (0, self.sphere_inner_radius))
                    ThreePointArc(
                        (0, self.sphere_inner_radius),
                        (x_mid_inner, self.sphere_inner_radius * math.sin(angle_45)),
                        (self.sphere_inner_radius, 0),
                    )
                    Line((self.sphere_inner_radius, 0), (self.sphere_flange_radius, 0))
                    Line(
                        (self.sphere_flange_radius, 0),
                        (self.sphere_flange_radius, self.sphere_thickness),
                    )
                    Line(
                        (self.sphere_flange_radius, self.sphere_thickness),
                        (x_start_outer, y_start_outer),
                    )
                    ThreePointArc(
                        (x_start_outer, y_start_outer),
                        (x_mid_outer, y_mid_outer),
                        (0, self.sphere_outer_radius),
                    )
                make_face()
            revolve()

        # Move to make space for the mounting ring
        dome_top.part.position = (0, 0, 0.5 * self.mounting_ring_thickness)
        dome_bottom = copy(dome_top)
        dome_bottom.part = dome_bottom.part.mirror(Plane.XY)

        return dome_top, dome_bottom

    def cut_mounting_holes(self):
        hole_pattern_radius = (self.sphere_outer_radius + self.sphere_flange_radius) / 2

        # Create the holes to cut in a circulat pattern
        with BuildPart() as holes:
            with PolarLocations(
                radius=hole_pattern_radius,
                count=self.mounting_hole_amount,
                start_angle=45,
                angular_range=360,
            ):
                Cylinder(
                    radius=self.mounting_hole_diameter / 2,
                    height=self.sphere_thickness * 2 + self.mounting_ring_thickness,
                )

        # Subtract the holes from the parts
        self.mounting_ring.part = self.mounting_ring.part - holes.part
        self.dome_top.part = self.dome_top.part - holes.part
        self.dome_bottom.part = self.dome_bottom.part - holes.part

    def get_parts(self) -> list[Part]:
        # Assign names and colors to the parts
        self.mounting_ring.part.label = CasePart.MOUNTING_RING.value
        self.mounting_ring.part.color = Config.Puzzle.MOUNTING_RING_COLOR

        self.dome_top.part.label = CasePart.CASE_TOP.value
        self.dome_top.part.color = Config.Puzzle.TRANSPARENT_CASE_COLOR

        self.dome_bottom.part.label = CasePart.CASE_BOTTOM.value
        self.dome_bottom.part.color = Config.Puzzle.TRANSPARENT_CASE_COLOR

        self.path_bridges.part.label = CasePart.INTERNAL_PATH_BRIDGES.value
        self.path_bridges.part.color = Config.Puzzle.PATH_COLORS[0]

        self.start_text.part.label = CasePart.START_INDICATOR.value
        self.start_text.part.color = Config.Puzzle.TEXT_COLOR

        # Return parts
        return [
            self.mounting_ring.part,
            self.dome_top.part,
            self.dome_bottom.part,
            self.path_bridges.part,
            self.start_text.part,
        ]

    def get_base_parts(self) -> list[Part]:
        return self.base_parts

    def create_cut_shape(self) -> BuildPart:
        flush_distance_tolerance = 0.0
        radius_outer = self.sphere_flange_diameter
        radius_inner = self.sphere_inner_radius - flush_distance_tolerance
        mid_outer_x = radius_outer / math.sqrt(2)
        mid_outer_y = radius_outer / math.sqrt(2)
        mid_inner_x = radius_inner / math.sqrt(2)
        mid_inner_y = radius_inner / math.sqrt(2)

        with BuildPart() as cut_shape:
            with BuildSketch(Plane.XZ):
                with BuildLine(Plane.XZ):
                    ThreePointArc(
                        (0, radius_outer), (mid_outer_x, mid_outer_y), (radius_outer, 0)
                    )
                    Line((radius_outer, 0), (radius_inner, 0))
                    ThreePointArc(
                        (radius_inner, 0), (mid_inner_x, mid_inner_y), (0, radius_inner)
                    )
                    Line((0, radius_inner), (0, radius_outer))
                make_face()
            revolve()
            translation_z = (
                0.5 * self.mounting_ring_thickness
                - 1 / 3 * self.mounting_ring_thickness
            )
            cut_shape.part.position = (0, 0, -translation_z)
            mirror(about=Plane.XY)

        return cut_shape


if __name__ == "__main__":
    CaseSphereWithFlange().preview()
