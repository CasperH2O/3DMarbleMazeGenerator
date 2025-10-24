from build123d import RadiusArc, Vector, Vertex
from ocp_vscode import show

# Define the three RadiusArcs
arc1 = RadiusArc(Vector(0, -87.5, 0), Vector(20, -85.183625187004, 0), radius=-87.5)
arc1_1 = RadiusArc(Vector(0, -87.5, 0), Vector(20, -85.183625187004, 0), radius=87.5)


arc2 = RadiusArc(Vector(87.5, 0, 0), Vector(71.807033081725, -50, 0), radius=87.5)
arc3 = RadiusArc(Vector(0, 87.5, 0), Vector(20, 85.183625187004, 0), radius=87.5)

# Define a vertex at (0, 0, 0)
origin_vertex = Vertex(0, 0, 0)

# Show all objects
show(arc1, arc1_1, arc2, arc3, origin_vertex)
pass