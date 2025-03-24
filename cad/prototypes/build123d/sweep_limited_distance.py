from math import pi

from build123d import *
from ocp_vscode import show_all

# Create a smooth Bezier curve as the edge
edge = Bezier((0, 0, 0), (10, 20, 0), (20, 20, 10), (30, 0, 10))

# Define the distance we want to move along the edge
distance = 5  # mm

# Get the location at that exact distance along the curve
location = edge.location_at(distance, position_mode=PositionMode.LENGTH)

# Alternative: Move using parametric distance (not as precise for arc length)
l2 = edge ^ (distance / edge.length)  # Normalized parametric movement

# Trim the edge to keep only the first 5mm
trimmed_edge = edge.trim_to_length(0, distance)

# Create a small profile (circle) and move it to the start of the trimmed edge
profile = (trimmed_edge ^ 1) * Circle(0.1)

# Sweep the profile along the trimmed edge
swept_shape = sweep(profile, trimmed_edge)

# Display the result
show_all()
