from build123d import (
    Axis,
    BuildPart,
    BuildSketch,
    Circle,
    Mode,
    Sphere,
    chamfer,
    extrude,
)

import config

sphere_diameter = config.Sphere.SPHERE_DIAMETER
extrusion_amount = -1 * (sphere_diameter / 2 + 5)


# Create a basic circular base with a sphere cut out based on enclosure size
def create_circular_base():
    with BuildPart() as base:
        # Base cylinder
        with BuildSketch():
            Circle(radius=30)
        extrude(amount=extrusion_amount)
        # Hold in cylinder
        with BuildSketch():
            Circle(radius=15)
        extrude(amount=extrusion_amount, mode=Mode.SUBTRACT)
        Sphere(radius=sphere_diameter / 2, mode=Mode.SUBTRACT)
        chamfer(base.edges().group_by(Axis.Z)[0], length=2)

        base.part.label = "Base"
        base.part.color = config.Puzzle.PATH_COLORS[0]

    return base.part
