from build123d import (
    Align,
    Axis,
    BuildPart,
    BuildSketch,
    Circle,
    Cylinder,
    Keep,
    Mode,
    Part,
    Plane,
    Rectangle,
    Sphere,
    chamfer,
    extrude,
    split,
)
from ocp_vscode import show

import config

# TODO, the methods here could be made part
# of the various case classes or part of the
# case class, use inheritance but be mindful
# of circular imports with config

sphere_diameter = config.Sphere.SPHERE_DIAMETER
extrusion_amount = -1 * (sphere_diameter / 2 + 7)


# Create a circular base with a sphere cut out based on enclosure size
def create_circular_base() -> list[Part]:
    with BuildPart() as base:
        # Base cylinder, aligned so its MAX-Z face is at Z=0
        Cylinder(
            radius=30,
            height=-extrusion_amount,
            align=(Align.CENTER, Align.CENTER, Align.MAX),
        )
        # Hole in cylinder, same alignment, subtractive
        Cylinder(
            radius=15,
            height=-extrusion_amount,
            align=(Align.CENTER, Align.CENTER, Align.MAX),
            mode=Mode.SUBTRACT,
        )
        # Subtract the puzzle casing sphere
        Sphere(radius=sphere_diameter / 2, mode=Mode.SUBTRACT)
        chamfer(base.edges().group_by(Axis.Z)[0], length=2)
        chamfer(base.edges().group_by(Axis.Z)[-1], length=2)

    base_foot = split(
        objects=base.part,
        bisect_by=Plane.XY.offset(extrusion_amount + 5),
        keep=Keep.BOTTOM,
    )
    base_edge = split(
        objects=base.part,
        bisect_by=Plane.XY.offset(extrusion_amount + 6.5),
        keep=Keep.BOTTOM,
    )

    # Subtract from one another
    base.part -= base_foot
    base.part -= base_edge
    base_edge -= base_foot

    # Colors and labels
    base.part.label = "Base Top"
    base.part.color = config.Puzzle.PATH_COLORS[0]

    base_foot.label = "Base Bottom"
    base_foot.color = config.Puzzle.MOUNTING_RING_COLOR

    base_edge.label = "Base Edge"
    base_edge.color = config.Puzzle.PATH_ACCENT_COLOR

    return [base.part, base_foot, base_edge]


# Create a rectangular base, based on puzzle dimensions
def create_box_base() -> list[Part]:
    node_size = config.Puzzle.NODE_SIZE
    length = config.Box.LENGTH
    width = config.Box.WIDTH
    tolerance = 0.5

    with BuildPart() as base:
        with BuildSketch():
            Rectangle(
                height=length + node_size,
                width=width + node_size,
            )
        extrude(amount=-node_size * 2, taper=-6)
        with BuildSketch():
            Rectangle(
                height=length + tolerance,
                width=width + tolerance,
            )
        extrude(amount=-node_size, mode=Mode.SUBTRACT)

    base.part.position = (0, 0, -config.Box.HEIGHT * 0.5 + node_size)
    base.part.label = "Base"
    base.part.color = config.Puzzle.PATH_COLORS[0]

    return [base.part]


# Create a cylinder base, based on puzzle dimensions
def create_cylinder_base() -> list[Part]:
    node_size = config.Puzzle.NODE_SIZE
    height = config.Cylinder.HEIGHT
    diameter = config.Cylinder.DIAMETER
    tolerance = 0.5

    with BuildPart() as base:
        with BuildSketch():
            Circle(radius=diameter / 2 + node_size)
        extrude(amount=-node_size * 2, taper=-6)
        with BuildSketch():
            Circle(
                radius=diameter / 2 + tolerance,
            )
        extrude(amount=-node_size, mode=Mode.SUBTRACT)

    base.part.position = (0, 0, -height * 0.5 + node_size)
    base.part.label = "Base"
    base.part.color = config.Puzzle.PATH_ACCENT_COLOR

    return [base.part]


if __name__ == "__main__":
    base = create_cylinder_base()
    show(base)
