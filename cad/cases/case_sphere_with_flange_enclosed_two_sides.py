# cad/cases/case_sphere_with_flange_enclosed_two_sides.py

import math
from copy import copy

from build123d import (
    Align,
    Axis,
    Box,
    BuildLine,
    BuildPart,
    BuildSketch,
    Circle,
    Cylinder,
    Keep,
    Line,
    Locations,
    Mode,
    Part,
    Plane,
    PolarLocations,
    Rectangle,
    RegularPolygon,
    SortBy,
    ThreePointArc,
    chamfer,
    extrude,
    fillet,
    make_face,
    mirror,
    revolve,
    split,
)

from cad.cases.case import Case, CasePart
from config import Config


class CaseSphereWithFlangeEnclosedTwoSides(Case):
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
        self.mounting_ring_clips_width = 20
        self.mounting_ring_clips_length = 14
        self.mounting_ring_clips_thickness = 1.6

        # Derived variables
        self.sphere_inner_diameter = self.sphere_outer_diameter - (
            2 * self.sphere_thickness
        )
        self.sphere_outer_radius = self.sphere_outer_diameter / 2
        self.sphere_inner_radius = self.sphere_inner_diameter / 2
        self.sphere_flange_radius = self.sphere_flange_diameter / 2
        self.sphere_flange_inner_radius = self.sphere_flange_inner_diameter / 2

        # Create parts
        (
            self.mounting_ring_clips,
            self.mounting_ring,
            self.internal_path_bridges,
            self.start_indicator,
            self.mounting_ring_top,
            self.mounting_ring_bottom,
        ) = self.create_mounting_ring()
        self.dome_top, self.dome_bottom = self.create_domes()
        self.cut_shape = self.create_cut_shape()

    def create_mounting_ring(self):
        with BuildPart() as mounting_ring_bottom:
            # Create the outer ring
            Cylinder(
                radius=self.sphere_flange_radius, height=self.mounting_ring_thickness
            )
            Cylinder(
                radius=self.sphere_outer_radius,
                height=self.mounting_ring_thickness,
                mode=Mode.SUBTRACT,
            )
            Cylinder(
                radius=self.sphere_flange_radius - self.mounting_ring_edge,
                height=self.mounting_ring_inner_height,
                mode=Mode.SUBTRACT,
            )

            # Split and keep one side, which is later copied, and rotated (twice)
            split(bisect_by=Plane.XY, keep=Keep.BOTTOM)

            peg_radius = (
                self.sphere_flange_inner_radius
                + (
                    (self.sphere_flange_radius - self.mounting_ring_edge)
                    - self.sphere_flange_inner_radius
                )
                / 2
            )
            peg_tolerance = 0.1

            # Create pegs with holes
            with PolarLocations(
                radius=peg_radius,
                count=round(self.number_of_mounting_points / 2),
                start_angle=self.sphere_flange_slot_angle,
                angular_range=360,
            ) as peg_with_hole_locations:
                Cylinder(radius=2, height=self.mounting_ring_inner_height)
                Cylinder(
                    radius=1.2 + peg_tolerance,
                    height=self.mounting_ring_inner_height,
                    mode=Mode.SUBTRACT,
                )

            with PolarLocations(
                radius=peg_radius,
                count=round(self.number_of_mounting_points / 2),
                start_angle=-self.sphere_flange_slot_angle
                + 360 / self.number_of_mounting_points,
                angular_range=360,
            ) as peg_with_hole_locations_mirrored:
                Cylinder(radius=2, height=self.mounting_ring_inner_height)
                Cylinder(
                    radius=1.2 + peg_tolerance,
                    height=self.mounting_ring_inner_height,
                    mode=Mode.SUBTRACT,
                )

            # Reduce the height of the pegs
            split(bisect_by=Plane.XY, keep=Keep.BOTTOM)

            # Regular pegs
            with PolarLocations(
                radius=peg_radius,
                count=round(self.number_of_mounting_points / 2),
                start_angle=-self.sphere_flange_slot_angle,
                angular_range=360,
            ) as peg_locations:
                Cylinder(radius=1.2, height=self.mounting_ring_inner_height)

            with PolarLocations(
                radius=peg_radius,
                count=round(self.number_of_mounting_points / 2),
                start_angle=self.sphere_flange_slot_angle
                + 360 / self.number_of_mounting_points,
                angular_range=360,
            ) as peg_locations_mirrored:
                Cylinder(radius=1.2, height=self.mounting_ring_inner_height)

            # Reduce height of the pegs
            height_reduction_plane = Plane(
                mounting_ring_bottom.faces().sort_by(Axis.Z)[-1]
            ).offset(-Config.Manufacturing.LAYER_THICKNESS * 2)
            split(bisect_by=height_reduction_plane, keep=Keep.BOTTOM)

        # Flip the mounting ring and rotate for the next set of pegs/holes
        mounting_ring_top = copy(mounting_ring_bottom)
        mounting_ring_top.part = mounting_ring_top.part.rotate(
            Axis((0, 0, 0), (0, 1, 0)), 180
        )
        mounting_ring_top.part = mounting_ring_top.part.rotate(
            Axis((0, 0, 0), (0, 0, 1)), 360 / self.number_of_mounting_points
        )

        # Add mounting bridges with an outer bridge that connects to
        # the mounting ring and an inner bridge that connects to the path
        # Skip the first location as that is the start area
        num_points = self.number_of_mounting_points
        start_angle = 360 / num_points + 180
        count = num_points - 1
        angle_range = 360 - 360 / num_points
        printing_layer_thickness = Config.Manufacturing.LAYER_THICKNESS
        printing_nozzle_diameter = Config.Manufacturing.NOZZLE_DIAMETER

        # Create the inner mounting ring from different parts
        with BuildPart() as bridge_ring:
            tolerance = 0.2
            Cylinder(
                radius=self.sphere_flange_radius - self.mounting_ring_edge - tolerance,
                height=self.mounting_bridge_height - tolerance,
            )
            Cylinder(
                radius=self.sphere_flange_inner_radius - 0.5,
                height=self.mounting_bridge_height - tolerance,
                mode=Mode.SUBTRACT,
            )

        with BuildPart() as external_bridges:
            with PolarLocations(
                radius=self.mounting_distance / 2,
                count=count,
                start_angle=start_angle,
                angular_range=angle_range,
            ):
                Box(
                    width=self.node_size - Config.Manufacturing.NOZZLE_DIAMETER,
                    length=self.node_size * 2 - 2.1,  # TODO Hardcoded, bad
                    height=self.mounting_bridge_height - tolerance,
                )

        # Create peg holes for later subtraction
        with BuildPart() as peg_holes:
            # Reuse the peg locations to create holes
            hole_locations = (
                peg_locations.locations
                + peg_locations_mirrored.locations
                + peg_with_hole_locations.locations
                + peg_with_hole_locations_mirrored.locations
            )
            with Locations(hole_locations):
                Cylinder(
                    radius=2 + tolerance,
                    height=self.mounting_ring_inner_height - tolerance,
                )

        # Internal path bridges to connect path with bridge material
        with BuildPart() as internal_path_bridges:
            with PolarLocations(
                radius=self.mounting_distance / 2,
                count=count,
                start_angle=start_angle,
                angular_range=angle_range,
            ):
                Box(
                    width=self.node_size - 6 * printing_nozzle_diameter,
                    length=self.node_size * 2 + 4 * printing_nozzle_diameter - 1.3,
                    height=self.mounting_bridge_height - printing_layer_thickness * 8,
                )

        # Cut the ring off the inner path bridges, keep inner bridge shapes
        internal_path_bridges.part = internal_path_bridges.part - bridge_ring.part
        internal_path_bridges.part = Part(
            internal_path_bridges.part.solids().sort_by(SortBy.VOLUME)[-count:]
        )

        # Combine ring and outer bridges
        bridge_ring.part = bridge_ring.part + external_bridges.part

        # Apply fillet, restore bridges we don't want filleted
        bridge_ring.part = fillet(bridge_ring.part.edges().filter_by(Axis.Z), radius=4)
        bridge_ring.part = bridge_ring.part + external_bridges.part

        # Cut out the peg holes
        bridge_ring.part = (
            bridge_ring.part - peg_holes.part - internal_path_bridges.part
        )

        # Start indicator, combine with mounting ring clip at start of puzzle
        with BuildPart() as start_indicator:
            with BuildSketch(Plane.YZ.offset(-self.sphere_flange_radius)):
                with Locations((0, -0.9)):
                    RegularPolygon(radius=3.5, side_count=3, rotation=90)
            extrude(amount=3, both=True)

        # Build the mounting ring clips
        mounting_ring_clips = self.create_mounting_ring_clips(False)
        start_indicator.part = start_indicator.part & mounting_ring_clips.part
        mounting_ring_clips.part = mounting_ring_clips.part - start_indicator.part

        # Cut out the mounting ring clip toleranced part from both the top and bottom mounting rings
        mounting_ring_clips_tolerance_cut_out = self.create_mounting_ring_clips(True)
        mounting_ring_bottom.part = (
            mounting_ring_bottom.part - mounting_ring_clips_tolerance_cut_out.part
        )
        mounting_ring_top.part = (
            mounting_ring_top.part - mounting_ring_clips_tolerance_cut_out.part
        )

        return (
            mounting_ring_clips,
            bridge_ring,
            internal_path_bridges,
            start_indicator,
            mounting_ring_top,
            mounting_ring_bottom,
        )

    def create_mounting_ring_clips(self, use_tolerance: bool):
        """
        Create mounting ring clips for both the physical parts and the cut-out pattern,
        applying an additional clearance tolerance where needed.

        Parameters:
            tolerance (float): Extra tolerance (clearance) to be applied to key dimensions.

        Returns:
            BuildPart: The constructed mounting ring clips.
        """

        # Set tolerance to 0.1 mm, if tolerance is requested,
        # get's multiplied for proper distance where applicable
        if use_tolerance:
            tolerance = 0.1
        else:
            tolerance = 0.0

        mounting_clip_radius = (
            self.sphere_flange_inner_radius + self.sphere_flange_radius
        ) / 2
        mounting_clip_height = (
            self.mounting_ring_thickness + 2 * self.mounting_ring_clips_thickness
        )

        with BuildPart() as mounting_ring_clips:
            # Create blocks placed in in a circular pattern
            with BuildSketch():
                with PolarLocations(
                    radius=mounting_clip_radius, count=self.number_of_mounting_points
                ):
                    # Add tolerance to the clip length if required
                    Rectangle(
                        self.mounting_ring_clips_width,
                        self.mounting_ring_clips_length + 4 * tolerance,
                    )
            # Extrude with extra clearance
            extrude(amount=(mounting_clip_height + 0.8) / 2, both=True)

            # Remove the outer curved shape from the blocks
            with BuildSketch():
                Circle(
                    self.sphere_flange_radius + 5 * self.mounting_ring_clips_thickness
                )
                Circle(
                    self.sphere_flange_radius + self.mounting_ring_clips_thickness,
                    mode=Mode.SUBTRACT,
                )
            extrude(
                amount=mounting_clip_height,
                mode=Mode.SUBTRACT,
                both=True,
            )

            # Cut out the inner area to create a U-shape with chamfered edges
            with BuildSketch(Plane.XZ) as sketch_inner_cut:
                Rectangle(
                    self.sphere_flange_radius,
                    mounting_clip_height
                    - 2 * self.mounting_ring_clips_thickness
                    + 0.8  # Extra clearance
                    - 8 * tolerance,  # Compensate clearance in case of tolerance part
                    align=(Align.MIN, Align.CENTER),
                )
                chamfer(sketch_inner_cut.vertices(), 1.5 + 2 * tolerance)
            revolve(mode=Mode.SUBTRACT)

            # Cut the side of the clip that touch with the domes
            with BuildSketch(Plane.XZ):
                Rectangle(
                    self.sphere_inner_radius,
                    mounting_clip_height * 2,
                    align=(Align.MIN, Align.CENTER),
                )
            revolve(mode=Mode.SUBTRACT)

            # Create internal ridges on both sides
            with BuildSketch(
                Plane.XY.offset(
                    -1 * (mounting_clip_height / 2)
                    + self.mounting_ring_clips_thickness
                    - 0.4
                )
            ):
                with PolarLocations(
                    radius=2 * tolerance
                    + (self.sphere_flange_inner_radius + mounting_clip_radius) / 2,
                    count=self.number_of_mounting_points,
                ):
                    Rectangle(2 + 4 * tolerance, 7 + 4 * tolerance)
            extrude(amount=5, taper=45)
            mirror(about=Plane.XY)

        return mounting_ring_clips

    def create_domes(self):
        angle_45 = math.radians(45)
        x_mid_inner = self.sphere_inner_radius * math.cos(angle_45)
        x_start_outer = math.sqrt(
            self.sphere_outer_radius**2 - self.sphere_thickness**2
        )
        y_start_outer = self.sphere_thickness
        theta_start = math.asin(y_start_outer / self.sphere_outer_radius)
        theta_mid_outer = (theta_start + math.pi / 2) / 2
        x_mid_outer = self.sphere_outer_radius * math.cos(theta_mid_outer)
        y_mid_outer = self.sphere_outer_radius * math.sin(theta_mid_outer)

        with BuildPart() as dome_top:
            # Create half dome (top) with flange
            with BuildSketch(Plane.XZ):
                with BuildLine(Plane.XZ):
                    Line((0, self.sphere_outer_radius), (0, self.sphere_inner_radius))
                    ThreePointArc(
                        (0, self.sphere_inner_radius),
                        (x_mid_inner, self.sphere_inner_radius * math.sin(angle_45)),
                        (self.sphere_inner_radius, 0),
                    )
                    Line(
                        (self.sphere_inner_radius, 0),
                        (self.sphere_flange_radius - self.mounting_ring_edge, 0),
                    )
                    Line(
                        (self.sphere_flange_radius - self.mounting_ring_edge, 0),
                        (
                            self.sphere_flange_radius - self.mounting_ring_edge,
                            self.sphere_thickness,
                        ),
                    )
                    Line(
                        (
                            self.sphere_flange_radius - self.mounting_ring_edge,
                            self.sphere_thickness,
                        ),
                        (x_start_outer, y_start_outer),
                    )
                    ThreePointArc(
                        (x_start_outer, y_start_outer),
                        (x_mid_outer, y_mid_outer),
                        (0, self.sphere_outer_radius),
                    )
                make_face()
            revolve()

            # Create partial holes in two sets of patterned locations
            with PolarLocations(
                radius=(self.sphere_outer_radius + self.sphere_flange_radius) / 2 - 0.5,
                count=self.mounting_hole_amount,
                start_angle=self.sphere_flange_slot_angle,
                angular_range=360,
            ):
                Cylinder(
                    radius=self.mounting_hole_diameter / 2,
                    height=self.sphere_thickness * 2,
                    mode=Mode.SUBTRACT,
                )

            with PolarLocations(
                radius=(self.sphere_outer_radius + self.sphere_flange_radius) / 2 - 0.5,
                count=self.mounting_hole_amount,
                start_angle=-self.sphere_flange_slot_angle,
                angular_range=360,
            ):
                Cylinder(
                    radius=self.mounting_hole_diameter / 2,
                    height=self.sphere_thickness * 2,
                    mode=Mode.SUBTRACT,
                )
            fillet(dome_top.edges().filter_by(Axis.Z), radius=2)

        # Move dome to make space for the mounting ring and create bottom dome
        dome_top.part.position = (0, 0, 0.5 * self.mounting_bridge_height)
        dome_bottom = copy(dome_top)
        dome_bottom.part = dome_bottom.part.mirror(Plane.XY)

        return dome_top, dome_bottom

    def get_parts(self):
        # Prepare the mounting ring clips as separate parts for manufacturing
        mounting_ring_clip_start = copy(self.mounting_ring_clips)
        mounting_ring_clip_single = copy(self.mounting_ring_clips)

        # Get the clip with the lowest volume (start indicator hole)
        mounting_ring_clip_start.part = Part(
            self.mounting_ring_clips.part.solids().sort_by(SortBy.VOLUME)[0:1]
        )
        mounting_ring_clip_start.part.label = CasePart.MOUNTING_RING_CLIP_START.value
        mounting_ring_clip_start.part.color = Config.Puzzle.MOUNTING_RING_COLOR

        # Single clip for printing
        mounting_ring_clip_single.part = Part(
            self.mounting_ring_clips.part.solids().sort_by(SortBy.VOLUME)[-1:]
        )
        mounting_ring_clip_single.part.label = CasePart.MOUNTING_RING_CLIP_SINGLE.value
        mounting_ring_clip_single.part.color = Config.Puzzle.MOUNTING_RING_COLOR

        # Remaining clips after extracting first and last
        self.mounting_ring_clips.part = Part(
            self.mounting_ring_clips.part.solids().sort_by(SortBy.VOLUME)[1:-1]
        )
        self.mounting_ring_clips.part.label = CasePart.MOUNTING_RING_CLIPS.value
        self.mounting_ring_clips.part.color = Config.Puzzle.MOUNTING_RING_COLOR

        # Assign labels and colors to other parts
        self.dome_top.part.label = CasePart.DOME_TOP.value
        self.dome_top.part.color = Config.Puzzle.TRANSPARENT_CASE_COLOR

        self.dome_bottom.part.label = CasePart.DOME_BOTTOM.value
        self.dome_bottom.part.color = Config.Puzzle.TRANSPARENT_CASE_COLOR

        self.mounting_ring.part.label = CasePart.MOUNTING_RING.value
        self.mounting_ring.part.color = Config.Puzzle.MOUNTING_RING_COLOR

        self.mounting_ring_top.part.label = CasePart.MOUNTING_RING_TOP.value
        self.mounting_ring_top.part.color = Config.Puzzle.MOUNTING_RING_COLOR

        self.mounting_ring_bottom.part.label = CasePart.MOUNTING_RING_BOTTOM.value
        self.mounting_ring_bottom.part.color = Config.Puzzle.MOUNTING_RING_COLOR

        self.start_indicator.part.label = CasePart.START_INDICATOR.value
        self.start_indicator.part.color = Config.Puzzle.TEXT_COLOR

        self.internal_path_bridges.part.label = CasePart.INTERNAL_PATH_BRIDGES.value
        self.internal_path_bridges.part.color = Config.Puzzle.PATH_COLORS[0]
        # Return parts
        return [
            self.dome_top.part,
            self.dome_bottom.part,
            self.mounting_ring.part,
            self.mounting_ring_top.part,
            self.mounting_ring_bottom.part,
            mounting_ring_clip_start.part,
            self.mounting_ring_clips.part,
            mounting_ring_clip_single.part,
            self.start_indicator.part,
            self.internal_path_bridges.part,
        ]

    def create_cut_shape(self):
        flush_distance_tolerance = 0.5
        radius_outer = self.sphere_flange_diameter * 0.7
        radius_inner = self.sphere_flange_inner_radius - flush_distance_tolerance
        mid_outer_x = radius_outer / math.sqrt(2)
        mid_outer_y = radius_outer / math.sqrt(2)
        mid_inner_x = radius_inner / math.sqrt(2)
        mid_inner_y = radius_inner / math.sqrt(2)

        with BuildPart() as cut_shape_cylinder:
            Cylinder(
                radius=self.sphere_flange_diameter * 0.75,
                height=self.mounting_bridge_height,
            )
            internal_cut_out_radius = self.sphere_flange_inner_diameter / 2 + (
                (
                    self.sphere_flange_diameter / 2
                    - self.sphere_flange_inner_diameter / 2
                )
                * 0.5
            )
            Cylinder(
                radius=internal_cut_out_radius,
                height=self.mounting_bridge_height,
                mode=Mode.SUBTRACT,
            )

        with BuildPart() as cut_shape_sphere:
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
                0.5 * self.mounting_bridge_height
            ) - 0.33333 * self.mounting_bridge_height
            cut_shape_sphere.part.position = (0, 0, -translation_z)
            mirror(about=Plane.XY)

        cut_shape_cylinder.part = cut_shape_cylinder.part + cut_shape_sphere.part

        cut_shape = cut_shape_cylinder

        return cut_shape


if __name__ == "__main__":
    CaseSphereWithFlangeEnclosedTwoSides().preview()
