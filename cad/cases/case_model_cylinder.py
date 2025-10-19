# cad/cases/case_model_cylinder.py

from build123d import (
    Axis,
    BuildPart,
    BuildSketch,
    Circle,
    Cylinder,
    GeomType,
    Location,
    Locations,
    Mode,
    Part,
    PolarLocations,
    Select,
    add,
    extrude,
)
from ocp_vscode import show_object

from cad.cases.case_model_base import Case, CasePart
from config import Config


class CaseCylinder(Case):
    def __init__(self):
        # Core config
        self.diameter = Config.Cylinder.DIAMETER
        self.height = Config.Cylinder.HEIGHT
        self.shell_thickness = Config.Cylinder.SHELL_THICKNESS
        self.number_of_mounting_points = Config.Cylinder.NUMBER_OF_MOUNTING_POINTS
        self.node_size = Config.Puzzle.NODE_SIZE

        # Create enclosure & cut shape
        self.casing = self.create_casing()
        self.cut_shape = self.create_cut_shape()
        self.base_parts = self._create_base_parts()

        # Case assembly
        (
            self.base,
            self.base_top,
            self.internal_path_bridges,
        ) = self.create_case_assembly()

    def create_casing(self) -> BuildPart:
        # Simple cylinder with open top and bottom
        with BuildPart() as casing:
            with BuildSketch():
                Circle(radius=self.diameter / 2)
                Circle(
                    radius=self.diameter / 2 - self.shell_thickness,
                    mode=Mode.SUBTRACT,
                )
            extrude(amount=self.height / 2, both=True)
        return casing

    def create_cut_shape(self) -> BuildPart:
        # Shape that ensures the case properly hollows out external bodies
        flush_distance_tolerance = 0.4
        inner_diameter = (
            self.diameter - 2 * self.shell_thickness - 2 * flush_distance_tolerance
        )
        inner_height = (
            self.height - 2 * self.shell_thickness - 2 * flush_distance_tolerance
        )

        with BuildPart() as cut_shape:
            outer = Cylinder(radius=self.diameter, height=self.height * 2)
            inner = Cylinder(radius=inner_diameter / 2, height=inner_height)
            add(outer - inner, mode=Mode.REPLACE)

        return cut_shape

    def create_case_assembly(self) -> list[BuildPart]:
        """ """
        tolerance = 0.5

        # Casing-shaped solid used only to cut an indent in base parts (has tolerance)
        with BuildPart() as indent_casing:
            with BuildSketch():
                Circle(radius=(self.diameter + tolerance) / 2)
                Circle(
                    radius=(self.diameter + tolerance) / 2 - self.shell_thickness,
                    mode=Mode.SUBTRACT,
                )
            extrude(amount=self.height / 2, both=True)

        # Long thin rods
        diameter_long = 0.5 * self.node_size
        r_long = diameter_long / 2
        h_long = (
            self.height - self.node_size
        )  # reduced to make room for top/bottom discs
        pattern_r = (
            self.diameter - 2 * self.shell_thickness
        ) / 2 - 2 * self.node_size  # 28.0  # TODO: tie to actual node pattern

        # Short, thicker rods (at multiple Z levels)
        # TODO Add chamfer to smaller vertical rods for 3D printing
        diameter_short = 0.8 * self.node_size
        r_short = diameter_short / 2
        h_short = 1.5 * self.node_size
        z_planes = [0.0, h_long / 2 - h_short / 2, -h_long / 2 + h_short / 2]

        # Discs
        base_r = (self.diameter + self.node_size) / 2
        base_h = self.node_size
        bottom_z = -h_long / 2 - base_h / 2
        top_z = h_long / 2 + base_h / 2

        # Small radial spokes, mounting and internal path bridges
        small_len = self.node_size
        inner_pattern_r = pattern_r + 0.25 * self.node_size

        # bottom case: long rods + short rods + bottom disc
        with BuildPart() as bottom_case:
            # long rods
            with PolarLocations(radius=pattern_r, count=self.number_of_mounting_points):
                Cylinder(radius=r_long, height=h_long)

            # capture the top planar faces to extend rods upward by 5
            long_top_faces = (
                bottom_case.faces(Select.LAST)
                .filter_by(GeomType.PLANE)
                .sort_by(Axis.Z)[-self.number_of_mounting_points :]
            )
            for f in long_top_faces:
                extrude(to_extrude=f, amount=5, mode=Mode.ADD)

            # short thicker rods across z-planes
            for z in z_planes:
                with Locations((0, 0, z)):
                    with PolarLocations(
                        radius=pattern_r, count=self.number_of_mounting_points
                    ):
                        Cylinder(radius=r_short, height=h_short)

            # bottom disc
            with Locations((0, 0, bottom_z)):
                Cylinder(radius=base_r, height=base_h)

            # External mounting bridge: small radial spokes
            for z in z_planes:
                with Locations((0, 0, z)):
                    with PolarLocations(
                        radius=inner_pattern_r, count=self.number_of_mounting_points
                    ):
                        # rotate cylinder so it points radially
                        with Locations(Location((0, 0, 0), (90, 90, 0))):
                            Cylinder(radius=r_long, height=small_len)

        # Internal path bridges: small radial spokes (separate printable part)
        with BuildPart() as internal_path_bridges:
            for z in z_planes:
                with Locations((0, 0, z)):
                    with PolarLocations(
                        radius=inner_pattern_r + 0.2 * self.node_size,
                        count=self.number_of_mounting_points,
                    ):
                        # rotate cylinder so it points radially
                        with Locations(Location((0, 0, 0), (90, 90, 0))):
                            Cylinder(
                                radius=r_long / 2, height=small_len
                            )  # TODO improve dimensions and modifiers once paths work properly

        # Cut internal path bridges from mounting path bridges
        bottom_case.part -= internal_path_bridges.part

        # Top disc, separate for gluing
        with BuildPart() as top_disc:
            with Locations((0, 0, top_z)):
                Cylinder(radius=base_r, height=base_h)

        # Cut rod clearance holes in top disc, with tolerance for glue
        with BuildPart() as rod_cutter:
            with Locations((0, 0, h_long / 2 + 2.5)):
                with PolarLocations(
                    radius=pattern_r, count=self.number_of_mounting_points
                ):
                    Cylinder(radius=r_long + tolerance, height=5)

        # Apply booleans
        top_disc.part -= rod_cutter.part
        top_disc.part -= indent_casing.part
        bottom_case.part -= indent_casing.part

        # Labels and colors
        self.casing.part.label = CasePart.CASING.value
        self.casing.part.color = Config.Puzzle.TRANSPARENT_CASE_COLOR

        bottom_case.part.label = CasePart.CASE_BOTTOM.value
        bottom_case.part.color = Config.Puzzle.PATH_ACCENT_COLOR

        top_disc.part.label = CasePart.CASE_TOP.value
        top_disc.part.color = Config.Puzzle.PATH_ACCENT_COLOR

        internal_path_bridges.part.label = CasePart.INTERNAL_PATH_BRIDGES.value
        internal_path_bridges.part.color = Config.Puzzle.PATH_COLORS[0]

        return [bottom_case, top_disc, internal_path_bridges]

    def get_parts(self) -> list[Part]:
        return [
            self.casing.part,
            self.base.part,
            self.base_top.part,
            self.internal_path_bridges.part,
        ]

    def get_base_parts(self) -> list[Part]:
        return self.base_parts

    def _create_base_parts(self) -> list[Part]:
        tolerance = 0.5

        with BuildPart() as base:
            with BuildSketch():
                Circle(radius=self.diameter / 2 + self.node_size)
            extrude(amount=-self.node_size * 2, taper=-6)
            with BuildSketch():
                Circle(radius=self.diameter / 2 + tolerance)
            extrude(amount=-self.node_size, mode=Mode.SUBTRACT)

        base.part.position = (0, 0, -self.height * 0.5 + self.node_size)
        base.part.label = CasePart.BASE.value
        base.part.color = Config.Puzzle.PATH_ACCENT_COLOR

        return [base.part]


if __name__ == "__main__":
    case = CaseCylinder()
    show_object(case.get_parts())
