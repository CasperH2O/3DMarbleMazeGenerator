from build123d import *
from ocp_vscode import *

with BuildPart() as partial_cylinder:
    with BuildSketch(Plane.XZ):
        with PolarLocations(radius=50, count=1):
            Rectangle(10, 20)            
    revolve(revolution_arc=270)                  

show_all()