from build123d import *
from ocp_vscode import show

# --- Params ---
DIAMETER_LONG = 5.0
R_LONG = DIAMETER_LONG / 2
HEIGHT = 200.0
PATTERN_R = 27.0

DIAMETER_SHORT = 8.0
R_SHORT = DIAMETER_SHORT / 2
HEIGHT_SHORT = 20
Z_PLANES = [0.0, HEIGHT / 2 - 10.0, -HEIGHT / 2 + 10.0]

# Top & bottom discs
BASE_R = 50.0
BASE_H = 10.0
BOTTOM_Z = -HEIGHT / 2 - BASE_H / 2
TOP_Z = HEIGHT / 2 + BASE_H / 2

# Small radial rods
SMALL_LEN = 10.0
INNER_PATTERN_R = PATTERN_R + 5.0

with BuildPart() as rods:
    # Long rods (3x vertical)
    with PolarLocations(radius=PATTERN_R, count=3):
        Cylinder(radius=R_LONG, height=HEIGHT)

    # Short thicker rods (3 circles × 3 rods, vertical)
    for z in Z_PLANES:
        with Locations((0, 0, z)):
            with PolarLocations(radius=PATTERN_R, count=3):
                Cylinder(radius=R_SHORT, height=HEIGHT_SHORT)

    # Bottom & top discs
    with Locations((0, 0, BOTTOM_Z)):
        Cylinder(radius=BASE_R, height=BASE_H)
    with Locations((0, 0, TOP_Z)):
        Cylinder(radius=BASE_R, height=BASE_H)

    # Small "spokes" for path bridges
    for z in Z_PLANES:
        with Locations((0, 0, z)):
            with PolarLocations(
                radius=INNER_PATTERN_R, count=3
            ):  # rotate=True (default)
                with Locations(Location((0, 0, 0), (90, 90, 0))):
                    Cylinder(radius=R_LONG, height=SMALL_LEN)

show(rods)
