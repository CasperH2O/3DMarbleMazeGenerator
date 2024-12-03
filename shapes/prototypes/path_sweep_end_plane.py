import cadquery as cq
from ocp_vscode import *


# Points for path
pts = [
    (0, 0, 0),
    (40, 0, 0),
    (40, 0, 40),
    (0, 0, 40),
]

# u shape profile
adjusted_width = adjusted_height = 10 - 0.0001
wall_thickness = 1.2

half_width = adjusted_width / 2
half_height = adjusted_height / 2
inner_half_width = half_width - wall_thickness
inner_half_height = half_height - wall_thickness

u_shape = (
    cq.Workplane("YZ")
    .moveTo(-half_width, half_height)               # 1 Start at top-left corner of outer rectangle
    .lineTo(-inner_half_width, half_height)         # 2 Move to top-left inner corner
    .lineTo(-inner_half_width, -inner_half_height)  # 3 Down inner left wall
    .lineTo(inner_half_width, -inner_half_height)   # 4 Across bottom inner
    .lineTo(inner_half_width, half_height)          # 5 Up inner right wall
    .lineTo(half_width, half_height)                # 6 Move to top-right outer corner
    .lineTo(half_width, -half_height)               # 7 Down outer right wall
    .lineTo(-half_width, -half_height)              # 8 Across bottom outer
    .close()
)

# Create a path for the sweep
path = cq.Workplane("XY").polyline(pts)

# Sweep the profile along the path
swept_shape = u_shape.sweep(path, transition='right')

# Display the results
show_object(u_shape)
show_object(path)
show_object(swept_shape)