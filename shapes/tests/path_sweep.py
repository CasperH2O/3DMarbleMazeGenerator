import cadquery as cq

# Create a circular profile (the inner and outer circles)
diameter_inner = 8
diameter_outer = 10

# Define the points for the spline path
pts = [
    (-50, 0, 0),  # Start point
    (-40, 0, 0),
    (-30, 0, 0),
    (-20, 0, 0),
    (-10, 0, 0),
    (0, 0, 0),
    (0, -10, 0),
    (0, -20, 0),
    (0, -30, 0),  # Waypoint
    (10, -30, 0),
    (10, -20, 0),
    (10, -10, 0),  # Waypoint
    (20, -10, 0),
    (30, -10, 0),
    (30, 0, 0),  # Waypoint
    (20, 0, 0),
    (10, 0, 0),
    (10, 10, 0),
    (0, 10, 0),
    (0, 20, 0),
    (0, 30, 0),  # End point
]

# Workplane on the XY plane
circle_profile = (
    cq.Workplane("ZY")
    .workplane(offset=50)
    .circle(diameter_outer / 2)
    .circle(diameter_inner / 2)
)

# Create a path for the sweep
path = cq.Workplane("XY").spline(pts)
#path = cq.Workplane("XY").polyline(pts)
#path = cq.Workplane("XY").bezier(pts)

# Sweep the profile along the path
swept_shape = circle_profile.sweep(path, transition='right')

# Display the results
show_object(circle_profile)
show_object(path)
show_object(swept_shape)