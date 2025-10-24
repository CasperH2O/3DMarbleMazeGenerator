# collision_check.py
from build123d import (
    Bezier,
    Box,
    BuildLine,
    BuildPart,
    BuildSketch,
    Polyline,
    Pos,
    Rectangle,
    add,
    sweep,
)
from ocp_vscode import show

node_size = 10

# Build obstacle with polyline and bezier
with BuildLine() as start:
    Polyline((0, -node_size, 0), (0, 0, 0))

with BuildLine() as bez:
    size = 4
    Bezier(
        (0, 0, 0),
        (0, size * node_size, 0.5 * node_size),
        (size * node_size, size * node_size, 1.0 * node_size),
        (size * node_size, 0, 1.5 * node_size),
        (0, 0, 2 * node_size),
    )

with BuildLine() as end:
    Polyline((0, 0, 2 * node_size), (-node_size, 0, 2 * node_size))

with BuildLine() as path:
    add(start)
    add(bez)
    add(end)
path_wire = path.line

# Sweep
with BuildPart() as obstacle:
    with BuildSketch(path_wire ^ 0) as s_start:
        Rectangle(9.9, 9.9)
    with BuildSketch(path_wire ^ 1) as s_end:
        Rectangle(9.9, 9.9)
    sweep(
        sections=[s_start.sketch, s_end.sketch],
        multisection=True,
        path=path_wire,
        is_frenet=True,
    )

obstacle_solid = obstacle.part
obstacle_solid.label = "Obstacle Solid"
print(f"Obstacle valid: {obstacle_solid.is_valid()}")

# Cubes
base = Box(node_size, node_size, node_size)
cubes = [
    (Pos(-3 * node_size, 0, node_size) * base, "Box (-30,0,10)"),
    (Pos(-1 * node_size, 0, node_size) * base, "Box (-10,0,10)"),
    (Pos(0, 0, 0) * base, "Box (0,0,0)"),
    (Pos(0, 0, node_size) * base, "Box (0,0,-10)"),
    (Pos(2 * node_size, 0, 0) * base, "Box (20,0,0)"),
]

# Colors
green = (0.1, 0.7, 0.1)
red = (0.8, 0.1, 0.1)
grey = (0.8, 0.8, 0.8)

objects = [obstacle_solid]
names = [obstacle_solid.label]
colors = [grey]

for cube, name in cubes:
    inter = cube & obstacle_solid
    has_solids = False
    if inter is not None:
        has_solids = bool(inter.solids())
    objects.append(cube)
    names.append(name)
    colors.append(red if has_solids else green)

# Show
show(*objects, names=names, colors=colors, reset_camera=False)
