from build123d import *
from ocp_vscode import show

# Create a curved edge (helix in this case)
edge = Edge.make_helix(pitch=10, height=30, radius=5)

# Define a sweep profile (circle) at 5mm along the edge
with BuildSketch(edge ^ 5) as profile:
    Circle(1)  # 1mm radius circular profile

# Perform the sweep along the edge
with BuildPart() as swept_part:
    sweep(profile.sketch, edge)

# Display the result (if using ocp_vscode viewer)
from ocp_vscode import show
show(swept_part.part)
