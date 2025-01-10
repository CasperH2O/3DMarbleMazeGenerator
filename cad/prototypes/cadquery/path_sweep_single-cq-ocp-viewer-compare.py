import cadquery as cq
from ocp_vscode import *

# Create a tube profile (the inner and outer circles)
diameter_inner = 8
diameter_outer = 10 - 0.001

# Profile for part 1
circle_profile_1 = (
    cq.Workplane("ZY")
    .workplane(offset=50)
    .circle(diameter_outer / 2)
    .circle(diameter_inner / 2)
    .consolidateWires()
)

show_object(circle_profile_1)