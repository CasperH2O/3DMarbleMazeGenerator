from build123d import BuildLine, Polyline, Wire
from ocp_vscode import show

# Define three separate polylines
with BuildLine() as line_1:
    Polyline([(0, 0, 0), (40, 0, 0), (40, 0, 40), (0, 0, 40)])

with BuildLine() as line_2:
    Polyline([(0, 0, 40), (-40, 0, 40), (-40, -40, 40)])

with BuildLine() as line_3:
    Polyline([(-40, -40, 40), (-40, -45, 40), (0, -45, 40), (0, -45, 90)])

# List of wires
line_segments = [line_1.line, line_2.line, line_3.line]

# Combine all edges from each line into a single wire
all_edges = []
for segment in line_segments:
    all_edges.extend(segment.edges())

combined_wire = Wire._make_wire(all_edges)

# Visualize the result
show(combined_wire)
