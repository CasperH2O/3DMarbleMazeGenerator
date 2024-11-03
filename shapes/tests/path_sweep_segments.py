import cadquery as cq
from ocp_vscode import *

# Define the points for the different paths to try

path_initial_pts = [
    (-50, 0, 0),  # Start point
    (-40, 0, 0),
    (-30, 0, 0),
    (-20, 0, 0),
    (-20, 10, 0),
    (-20, 10, 10),
    (-20, 10, 20),
    (-10, 10, 20),
    (-10, 20, 20),  # Waypoint
    (0, 20, 20),
    (0, 20, 10),
    (0, 20, 0),
    (0, 30, 0),  # Waypoint
    (10, 30, 0),
    (20, 30, 0),
    (20, 20, 0),
    (20, 10, 0),
    (30, 10, 0),
    (30, 0, 0),  # Waypoint
    (30, -10, 0),
    (30, -20, 0),
    (20, -20, 0),
    (10, -20, 0),
    (0, -20, 0),
    (0, -30, 0),  # End point
]

# part 1, poly
path_1 = [
    (-50, 0, 0),  # Start point
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

# part 3, poly, no 2 straight lines after one another
path_3 = [
    (-20, 10, 10),
    (-20, 10, 20),
    (-10, 10, 20),
    (-10, 20, 20),  # Waypoint
    (0, 20, 20),
    (0, 20, 10),
]

# part 4, bezier 3D
path_4 = [
    (0, 20, 10),
    (0, 20, 0),
    (0, 30, 0),  # Waypoint
    (10, 30, 0),
]

# part 5, bezier 2D 90 degrees regular (3 nodes)
path_5 = [
    (10, 30, 0),
    (20, 30, 0),
    (20, 20, 0),
]

# part 6, bezier S-curve 
path_6 = [
    (20, 20, 0),
    (20, 10, 0),
    (30, 10, 0),
    (30, 0, 0),  # Waypoint
]

# part 7, bezier 2D large 90 degrees (5 nodes, remove 2)
path_7 = [
    (30, 0, 0),  # Waypoint
    #(30, -10, 0),
    (30, -20, 0),
    #(20, -20, 0),
    (10, -20, 0),
]

# part 8, bezier 2D 90 degrees regular (3 nodes)
path_8 = [
    (10, -20, 0),
    (0, -20, 0),
    (0, -30, 0),  # End point
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
)

# Profile for part 2
circle_profile_2 = (
    cq.Workplane("ZY")
    .workplane(offset=30)
    .circle(diameter_outer / 2)
    .circle(diameter_inner / 2)
)

# Profile for part 3
circle_profile_3 = (
    cq.Workplane("ZY")
    .transformed(rotate=(0, 90, 0), offset=(10, 10, 20))
    .circle(diameter_outer / 2)
    .circle(diameter_inner / 2)
)

# Profile for part 4
circle_profile_4 = (
    cq.Workplane("ZY")
    .transformed(rotate=(0, 90, 0), offset=(10, 20, 0))
    .circle(diameter_outer / 2)
    .circle(diameter_inner / 2)
)

# Profile for part 5
circle_profile_5 = (
    cq.Workplane("ZY")
    .transformed(rotate=(0, 0, 0), offset=(0, 30, -10))
    .circle(diameter_outer / 2)
    .circle(diameter_inner / 2)
)

# Profile for part 6
circle_profile_6 = (
    cq.Workplane("ZY")
    .transformed(rotate=(90, 0, 0), offset=(0, 20, -20))
    .circle(diameter_outer / 2)
    .circle(diameter_inner / 2)
)

# Profile for part 7
circle_profile_7 = (
    cq.Workplane("ZY")
    .transformed(rotate=(90, 0, 0), offset=(0, 0, -30))
    .circle(diameter_outer / 2)
    .circle(diameter_inner / 2)
)

# Profile for part 8
circle_profile_8 = (
    cq.Workplane("ZY")
    .transformed(rotate=(0, 0, 0), offset=(0, -30, -10))
    .circle(diameter_outer / 2)
    .circle(diameter_inner / 2)
)

# Create a path for the sweep, different curve options
#path = cq.Workplane("XY").spline(pts)
path_initial = cq.Workplane("XY").polyline(path_initial_pts)

path_1 = cq.Workplane("XY").polyline(path_1)
path_2 = cq.Workplane("XY").bezier(path_2)
path_3 = cq.Workplane("XY").polyline(path_3)
path_4 = cq.Workplane("XY").bezier(path_4)
path_5 = cq.Workplane("XY").bezier(path_5)
path_6 = cq.Workplane("XY").bezier(path_6)
path_7 = cq.Workplane("XY").bezier(path_7)
path_8 = cq.Workplane("XY").bezier(path_8)

# Sweep the profiles along the paths
swept_shape_1 = circle_profile_1.sweep(path_1, transition='right')
swept_shape_2 = circle_profile_2.sweep(path_2, transition='round')
swept_shape_3 = circle_profile_3.sweep(path_3, transition='round')
swept_shape_4 = circle_profile_4.sweep(path_4, transition='right')
swept_shape_5 = circle_profile_5.sweep(path_5, transition='right')
swept_shape_6 = circle_profile_6.sweep(path_6, transition='right')
swept_shape_7 = circle_profile_7.sweep(path_7, transition='right')
swept_shape_8 = circle_profile_8.sweep(path_8, transition='right')

# Display the results
show_object(path_initial)

show_object(circle_profile_1)
show_object(circle_profile_2)
show_object(circle_profile_3)
show_object(circle_profile_4)
show_object(circle_profile_5)
show_object(circle_profile_6)
show_object(circle_profile_7)
show_object(circle_profile_8)

show_object(path_1)
show_object(path_2)
show_object(path_3)
show_object(path_4)
show_object(path_5)
show_object(path_6)
show_object(path_7)
show_object(path_8)

show_object(swept_shape_1)
show_object(swept_shape_2)
show_object(swept_shape_3)
show_object(swept_shape_4)
show_object(swept_shape_5)
show_object(swept_shape_6)
show_object(swept_shape_7)
show_object(swept_shape_8)
