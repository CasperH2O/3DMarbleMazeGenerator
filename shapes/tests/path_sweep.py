import cadquery as cq

# Define the points for the different paths to try

# 90-degree curve, single plane
pts = [
    (-50, 0, 0),  # Start point
    (-40, 0, 0),
    (-40, 10, 0),
]

# S-Curve, dual plane
pts = [
    (-50, 0, 0),  # Start point
    (-40, 0, 0),
    (-30, 10, 0),
    (-20, 10, 0),
]

# 90 degree, 3D
pts = [
    (-50, 0, 0),
    (-40, 0, 0),
    (-40, 10, 0),
    (-40, 10, 10),
]

# Create a tube profile (the inner and outer circles)
diameter_inner = 8
diameter_outer = 10 - 0.0001

circle_profile = (
    cq.Workplane("ZY")
    .workplane(offset=50)
    .circle(diameter_outer / 2)
    .circle(diameter_inner / 2)
)

# Create a path for the sweep, different curve options
#path = cq.Workplane("XY").spline(pts)
#path = cq.Workplane("XY").polyline(pts)
path = cq.Workplane("XY").bezier(pts)

# Sweep the profile along the path
swept_shape = circle_profile.sweep(path, transition='round')

# Display the results
show_object(circle_profile)
show_object(path)
show_object(swept_shape)