from build123d import *
from ocp_vscode import show

diameter = 100
height = 200
shell_thickness = 2.5
tolerance = 0.5

# Create casing to create indent in base
with BuildPart() as casing:
    with BuildSketch():
        Circle(radius=(diameter + tolerance) / 2)
        Circle(
            radius=(diameter + tolerance) / 2 - shell_thickness,
            mode=Mode.SUBTRACT,
        )
    extrude(amount=height / 2, both=True)

# discs
base_r = 55.0
base_h = 20.0
bottom_z = -height / 2 - base_h / 2
top_z = height / 2 + base_h / 2

# base
with BuildPart() as base:
    # bottom disc
    with Locations((0, 0, bottom_z)):
        Cylinder(radius=base_r, height=base_h)

# Separate top disc for later glueing
with BuildPart() as top_disc:
    with Locations((0, 0, top_z)):
        Cylinder(radius=base_r, height=base_h)

# Carve disc recess with casing
top_disc.part -= casing.part
base.part -= casing.part

# Center rod
core_r = 7.5
core_h = height
with BuildPart() as core:
    Cylinder(radius=core_r, height=core_h)
core.part.color = "#00FF00FF"

# Tapered bosses
boss_base_r = core_r + 8.0  # base radius on disc surface (bigger than rod)
boss_taper_deg = 8.0
boss_len = 20

# Top boss
top_inner_face = top_disc.part.faces().sort_by(Axis.Z)[0]
with BuildPart() as top_boss:
    with BuildSketch(top_inner_face):
        Circle(radius=boss_base_r)
    extrude(amount=boss_len, taper=boss_taper_deg)
top_disc.part += top_boss.part

# Bottom boss
base_inner_face = base.part.faces().sort_by(Axis.Z)[-1]
with BuildPart() as bottom_boss:
    with BuildSketch(base_inner_face):
        Circle(radius=boss_base_r)
    extrude(amount=boss_len, taper=boss_taper_deg)
base.part += bottom_boss.part

# Colors
base.part.color = top_disc.part.color = "#000000FF"
casing.part.color = "#FFFFFF1C"

# View
show(base, top_disc, casing, core)
