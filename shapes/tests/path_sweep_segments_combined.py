import cadquery as cq
from ocp_vscode import *
from enum import Enum

class PathApproach(Enum):
    INDIVIDUAL = "individual"
    WORKPLANE = "workplane"
    WIRE_LIST = "wire_list"

# Approach to sweep the profiles along the paths, adjust as desired
approach = PathApproach.INDIVIDUAL

# Define the points for the different paths to try
path_initial_pts = [
    (-50, 0, 0),
    (-40, 0, 0),
    (-30, 0, 0),
    (-20, 0, 0),
    (-20, 10, 0),
    (-20, 10, 10),
    (-20, 10, 20),
    (-10, 10, 20),
    (-10, 20, 20),
    (0, 20, 20),
    (0, 20, 10),
]

# Creat path points for the sweeps, different curve options
# part 1, poly
path_1 = [
    (-50, 0, 0),
    (-40, 0, 0),
    (-30, 0, 0),
]

# part 2, bezier
path_2 = [
    (-30, 0, 0),
    (-20, 0, 0),
    (-20, 10, 0),
    (-20, 10, 10),
]

# part 3, poly
path_3 = [
    (-20, 10, 10),
    (-20, 10, 20),
    (-10, 10, 20),
    (-10, 20, 20),
    (0, 20, 20),
    (0, 20, 10),
]

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

# Profile for part 2
circle_profile_2 = (
    cq.Workplane("ZY")
    .workplane(offset=30)
    .circle(diameter_outer / 2)
    .circle(diameter_inner / 2)
    .consolidateWires()
)

# Profile for part 3
circle_profile_3 = (
    cq.Workplane("ZY")
    .transformed(rotate=(0, 90, 0), offset=(10, 10, 20))
    .circle(diameter_outer / 2)
    .circle(diameter_inner / 2)
    .consolidateWires()
)

# Define path with initial polyline points for refreence
path_initial = cq.Workplane("XY").polyline(path_initial_pts)
show_object(path_initial)

# Create a path for the sweep, different curve options
path_1 = cq.Workplane("XY").polyline(path_1)
path_2 = cq.Workplane("XY").bezier(path_2)
path_3 = cq.Workplane("XY").polyline(path_3)

match approach:
    case PathApproach.INDIVIDUAL:
        # Individual paths approach

        # Sweep the profiles along the paths
        swept_shape_1 = circle_profile_1.sweep(path_1, transition='right')
        swept_shape_2 = circle_profile_2.sweep(path_2, transition='round')
        swept_shape_3 = circle_profile_3.sweep(path_3, transition='round')

        show_object(swept_shape_1)
        show_object(swept_shape_2)
        show_object(swept_shape_3)

    case PathApproach.WORKPLANE:
        
        # Workplane approach
        combined_path = (
            cq.Workplane("XY")
            .add(path_1.vals())
            .add(path_2.vals())
            .add(path_3.vals())
        )

        # Create the full swept shape
        full_swept_shape = circle_profile_1.sweep(combined_path, transition='right')

        show_object(full_swept_shape)

    case PathApproach.WIRE_LIST:
        
        # Wire list approach
        # Get the wires from each path
        wire_1 = path_1.vals()[0]
        wire_2 = path_2.vals()[0]
        wire_3 = path_3.vals()[0]

        # Create a list of wires
        path_wires = [wire_1, wire_2, wire_3]

        # Create a compound wire from all segments
        compound_wire = cq.Wire.combine(path_wires)[0]

        # Create the full swept shape
        full_swept_shape = circle_profile_1.sweep(compound_wire, transition='right')

        show_object(full_swept_shape)
