# standalone_finish_box_debug.py

from build123d import *
from ocp_vscode import *

bezier_points = [
    (10.0, -10.0, 10.0),
    (10.0, -30.0, 10.0),
    (10.0, -30.0, 30.0),
]

poly_pts = [
    (10.0, -30.0, 30.0),
    (10.0, -30.0, 45.0),
]

with BuildPart() as segmet:
    with BuildLine() as initial_line:
        Polyline(poly_pts)
        Bezier(bezier_points)
    with BuildLine() as trimmed_line:
        initial_line_wire = Wire(initial_line.line)

        location_before_trim = initial_line.line ^ 1

        add(initial_line_wire.trim(0.8, 1.0))  # <--- Broken
        add(initial_line_wire.edges()[-1].trim(0.8, 1.0))  # <--- Fixed
        location_after_trim = trimmed_line.line ^ 1


print(f"Z before: {location_before_trim.position.Z}")
print(f"Z after: {location_after_trim.position.Z}")

# Visualize
set_defaults(reset_camera=Camera.RESET)
show_all()
