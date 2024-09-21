import cadquery as cq
import math

# Define the parameters for the puzzle
sphere_outer_diameter = 100  # Outer diameter in mm
sphere_flange_diameter = 120
sphere_thickness = 3         # Thickness in mm (cross-sectional radius)
sphere_inner_diameter = sphere_outer_diameter - (2 * sphere_thickness)  # Inner diameter in mm
ring_thickness = 3           # Thickness of the ring

ball_diameter = 4

mounting_hole_diameter = 3   # Diameter of the mounting holes
mounting_hole_amount = 5     # Number of mounting holes

#################
# Mounting Ring #
#################

# Calculate the radius of the mounting from the outer and inner diameters
outer_radius = sphere_flange_diameter / 2
inner_radius = sphere_inner_diameter / 2

# Create the mounting ring as a difference between two circles, then extrude symmetrically
mounting_ring = (
    cq.Workplane("XY")
    .circle(outer_radius)          # Outer circle
    .circle(inner_radius)          # Inner circle (hole)
    .extrude(ring_thickness)   # Extrude half the thickness upwards
)

mounting_ring = mounting_ring.translate((0, 0,- 0.5 * ring_thickness))

# Display the ring
show_object(mounting_ring, name="Mounting Ring")

#########
# Domes #
#########

sphere_outer_radius = sphere_outer_diameter / 2
sphere_inner_radius = sphere_inner_diameter / 2
sphere_flange_radius = sphere_flange_diameter / 2

# Calculate the intermediate point at 45 degrees (π/4 radians)
angle_45 = math.radians(45)

# Intermediate points for inner arc
x_mid_inner = sphere_inner_radius * math.cos(angle_45)
y_mid_inner = sphere_inner_radius * math.sin(angle_45)

# Calculate adjusted starting point for outer arc
x_start_outer = math.sqrt(sphere_outer_radius**2 - sphere_thickness**2)
y_start_outer = sphere_thickness  # Given

# Calculate angle for adjusted starting point
theta_start = math.asin(y_start_outer / sphere_outer_radius)

# Calculate intermediate point for outer arc
theta_mid_outer = (theta_start + math.pi / 2) / 2
x_mid_outer = sphere_outer_radius * math.cos(theta_mid_outer)
y_mid_outer = sphere_outer_radius * math.sin(theta_mid_outer)

# Create the profile on the XZ plane
profile = (
    cq.Workplane("XZ")
    # Start at the outer circle top
    .moveTo(0, sphere_outer_radius)  # Point A
    .lineTo(0, sphere_inner_radius)  # Line down to Point B
    .threePointArc((x_mid_inner, sphere_inner_radius * math.sin(angle_45)), (sphere_inner_radius, 0))  # Inner arc to Point C
    .lineTo(sphere_flange_radius, 0)  # Line to Point D
    .lineTo(sphere_flange_radius, sphere_thickness)  # Line up to Point E
    .lineTo(x_start_outer, y_start_outer)  # Line to adjusted starting point for outer arc (Point F)
    .threePointArc((x_mid_outer, y_mid_outer), (0, sphere_outer_radius))  # Outer arc back to Point A
    .close()
)

# Display the profile
#show_object(profile, name="Profile", options={"alpha": 0.5, "color": (1, 0, 0)})

# Revolve the profile
dome_top = profile.revolve(angleDegrees=360, axisStart=(0, 0, 0), axisEnd=(0, 1, 0))

dome_top = dome_top.translate((0, 0, 0.5 * ring_thickness))

# Mirror the extruded half along the XY plane
dome_bottom = dome_top.mirror(mirrorPlane="XY")

show_object(dome_top, name="Dome Bottom", options={"alpha": 0.9, "color": (1, 1, 1)})
show_object(dome_bottom, name="Dome Top", options={"alpha": 0.9, "color": (1, 1, 1)})

########
# Path #
########

# Define the 3D path using X, Y, and Z coordinates
CAD_path = [(-35, 0, 0), (-30, 0, 0), (-20, 0, 0), (-20, -10, 0), (-20, -20, 0), (-10, -20, 0), (-10, -30, 0), (0, -30, 0), (10, -30, 0), (10, -20, 0), (10, -10, 0), (20, -10, 0), (30, -10, 0), (30, -20.0001, 0), (30, -20.0001, 10), (30, -10, 10.0001), (30, 0, 10.0001), (30, 0, 0), (30, 10, 0), (30, 20, 0), (20, 20, 0), (10, 20, 0), (0, 20, 0), (-10, 20, 0), (-10, 30, 0)]
CAD_path = [(-30, 0, 0), (-30, 0, -10), (-30, 0, -20), (-20, 0, -20), (-20, 0, -10), (-20, -10, -10), (-10, -10, -10), (-10, -10, 0), (-10, -20, 0), (-10, -30, 0), (0, -30, 0), (10, -30, 0), (10, -20, 0), (10, -10, 0), (20, -10, 0), (30, -10, 0), (30, -20, 0), (30, -20, 10), (30, -10, 10), (30, 0, 10), (30, 0, 0), (30, 10, 0), (30, 20, 0), (20, 20, 0), (10, 20, 0), (0, 20, 0), (0, 30, 0), (0, 30, -10), (-10, 30, -10), (-10, 30, 0)]
CAD_path =  [(-50, 0, 0), (-40, 0, 0), (-30, 0, 0), (-30, 0, -10), (-30, 0, -20), (-20, 0, -20), (-10, 0, -20), (0, 0, -20), (0, -10, -20), (0, -10, -30), (0, -20, -30), (0, -20, -20), (0, -20, -10), (0, -20, 0), (-10, -20, 0), (-10, -30, 0), (0, -30, 0), (10, -30, 0), (10, -20, 0), (10, -10, 0), (20, -10, 0), (30, -10, 0), (30, -20, 0), (30, -20, 10), (30, -10, 10), (30, 0, 10), (30, 0, 0), (30, 10, 0), (30, 20, 0), (20, 20, 0), (10, 20, 0), (0, 20, 0), (0, 30, 0), (0, 30, -10), (-10, 30, -10), (-10, 30, 0), (-10, 20, 0), (-10, 20, 10), (-10, 20, 20), (-20, 20, 20), (-20, 10, 20), (-20, 0, 20)]

u_shape_height_width = 9.9999
u_shape_wall_thickness = 2

# Define path shape U
u_shape = (
    cq.Workplane("XY")
    .transformed(offset=cq.Vector(CAD_path[0]), rotate=cq.Vector(0, 90, 270))
    .moveTo(- u_shape_height_width / 2, u_shape_height_width / 2)                           # Top left of U-shape
    .lineTo(u_shape_height_width / 2, u_shape_height_width / 2)                             # Top horizontal line
    .lineTo(u_shape_height_width / 2, -u_shape_height_width / 2)                            # Right vertical line
    .lineTo(u_shape_height_width / 2 - u_shape_wall_thickness, -u_shape_height_width / 2)   # Right wall thickness
    .lineTo(u_shape_height_width / 2 - u_shape_wall_thickness, u_shape_height_width / 2 - u_shape_wall_thickness)               # Bottom inner part
    .lineTo(-u_shape_height_width / 2 + u_shape_wall_thickness, u_shape_height_width / 2 - u_shape_wall_thickness)              # Bottom inner part (other side)
    .lineTo(-u_shape_height_width / 2 + u_shape_wall_thickness, -u_shape_height_width / 2)             # Left wall thickness
    .lineTo(-u_shape_height_width / 2, -u_shape_height_width / 2)             # Left vertical line
    .close()                    # Close the U-shape
)

# Show path shap for debug
#show_object(u_shape, name="Path Shape")

# Create the path in 3D using a spline
path = cq.Workplane("XY").polyline(CAD_path)

# Sweep the U-shape along the 3D path
u_beam = u_shape.sweep(path, transition='right')

# Prepare for cutting around path body, makes start start at sphere edge

# Calculate radii
sphere_outer_radius = sphere_flange_diameter / 2
sphere_inner_radius = sphere_inner_diameter / 2

# Create the cross-sectional profile of the hollow sphere
hollow_sphere_profile = (
    cq.Workplane("XZ")
    .moveTo(0, sphere_outer_radius)
    .threePointArc((-sphere_outer_radius, 0), (0, -sphere_outer_radius))
    .lineTo(0, -sphere_inner_radius)
    .threePointArc((-sphere_inner_radius, 0), (0, sphere_inner_radius))
    .close()
)

# Revolve the profile to create the hollow sphere solid
hollow_sphere = hollow_sphere_profile.revolve(angleDegrees=360)

# Perform the cut operation
u_beam_cut = u_beam.cut(hollow_sphere)

# Show the final u_beam after the revolve cut
show_object(u_beam_cut, name="Path", options={"alpha": 0.0})

########
# Ball #
########

# Note, relies on path being availible with starting point

ball = cq.Workplane("XY").sphere(ball_diameter / 2).translate(CAD_path[1])

##################
# Mounting holes #
##################

sphere_outer_radius = sphere_outer_diameter / 2  # 50 mm
sphere_flange_radius = sphere_flange_diameter / 2  # 60 mm

# Calculate the hole pattern radius
hole_pattern_radius = (sphere_outer_radius + sphere_flange_radius) / 2  # Average radius

# Create a workplane on the XY plane
wp = cq.Workplane("XY")

# Define the hole pattern
holes = (
    wp
    .workplane()
    .polarArray(hole_pattern_radius, 0, 360, mounting_hole_amount, fill=True)
    .circle(mounting_hole_diameter / 2)
    .extrude(3 * sphere_thickness, both=True)  # Extrude length sufficient to cut through the bodies, centered on XY plane
)

# Cut the holes in mounting_ring
mounting_ring = mounting_ring.cut(holes)

# Cut the holes in dome_top
dome_top = dome_top.cut(holes)

# Cut the holes in dome_bottom
dome_bottom = dome_bottom.cut(holes)
show_object(ball, name="Ball", options={"color": (192, 192, 192)})