import cadquery as cq
import math

# Define the parameters for the puzzle
sphere_outer_diameter = 100  # Outer diameter in mm
sphere_flange_diameter = 130
sphere_thickness = 3         # Thickness in mm (cross-sectional radius)
ring_thickness = 3           # Thickness of the ring
ball_diameter = 4
mounting_hole_diameter = 3   # Diameter of the mounting holes
mounting_hole_amount = 5     # Number of mounting holes

# Derived variables
sphere_inner_diameter = sphere_outer_diameter - (2 * sphere_thickness)  # Inner diameter in mm
sphere_outer_radius = sphere_outer_diameter / 2
sphere_inner_radius = sphere_inner_diameter / 2
sphere_flange_radius = sphere_flange_diameter / 2

#################
# Mounting Ring #
#################

# Create the mounting ring as a difference between two circles, then extrude symmetrically
mounting_ring = (
    cq.Workplane("XY")
    .circle(sphere_flange_radius)          # Outer circle
    .circle(sphere_inner_radius)          # Inner circle (hole)
    .extrude(ring_thickness)   # Extrude half the thickness upwards
)

# Move to center
mounting_ring = mounting_ring.translate((0, 0,- 0.5 * ring_thickness))

#########
# Domes #
#########

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
dome_bottom = profile.revolve(angleDegrees=360, axisStart=(0, 0, 0), axisEnd=(0, 1, 0))

# Move to make place for mounting ring
dome_bottom = dome_bottom.translate((0, 0, 0.5 * ring_thickness))

# Mirror the dome for the other side
dome_top = dome_bottom.mirror(mirrorPlane="XY")

########
# Path #
########

# Define the 3D path using X, Y, and Z coordinates
CAD_path = [(-35, 0, 0), (-30, 0, 0), (-20, 0, 0), (-20, -10, 0), (-20, -20, 0), (-10, -20, 0), (-10, -30, 0), (0, -30, 0), (10, -30, 0), (10, -20, 0), (10, -10, 0), (20, -10, 0), (30, -10, 0), (30, -20.0001, 0), (30, -20.0001, 10), (30, -10, 10.0001), (30, 0, 10.0001), (30, 0, 0), (30, 10, 0), (30, 20, 0), (20, 20, 0), (10, 20, 0), (0, 20, 0), (-10, 20, 0), (-10, 30, 0)]
#CAD_path = [(-30, 0, 0), (-30, 0, -10), (-30, 0, -20), (-20, 0, -20), (-20, 0, -10), (-20, -10, -10), (-10, -10, -10), (-10, -10, 0), (-10, -20, 0), (-10, -30, 0), (0, -30, 0), (10, -30, 0), (10, -20, 0), (10, -10, 0), (20, -10, 0), (30, -10, 0), (30, -20, 0), (30, -20, 10), (30, -10, 10), (30, 0, 10), (30, 0, 0), (30, 10, 0), (30, 20, 0), (20, 20, 0), (10, 20, 0), (0, 20, 0), (0, 30, 0), (0, 30, -10), (-10, 30, -10), (-10, 30, 0)]
#CAD_path =  [(-50, 0, 0), (-40, 0, 0), (-30, 0, 0), (-30, 0, -10), (-30, 0, -20), (-20, 0, -20), (-10, 0, -20), (0, 0, -20), (0, -10, -20), (0, -10, -30), (0, -20, -30), (0, -20, -20), (0, -20, -10), (0, -20, 0), (-10, -20, 0), (-10, -30, 0), (0, -30, 0), (10, -30, 0), (10, -20, 0), (10, -10, 0), (20, -10, 0), (30, -10, 0), (30, -20, 0), (30, -20, 10), (30, -10, 10), (30, 0, 10), (30, 0, 0), (30, 10, 0), (30, 20, 0), (20, 20, 0), (10, 20, 0), (0, 20, 0), (0, 30, 0), (0, 30, -10), (-10, 30, -10), (-10, 30, 0), (-10, 20, 0), (-10, 20, 10), (-10, 20, 20), (-20, 20, 20), (-20, 10, 20), (-20, 0, 20)]

# Define path shape U
u_shape_height_width = 10 - 0.0001
u_shape_wall_thickness = 2

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
#show_object(u_shape, name="Path Shape U")

# Path shape: tube
tube_outer_diameter = 10 - 0.0001  # Example value
tube_wall_thickness = 2   # Example value

# Calculate inner diameter
tube_inner_diameter = tube_outer_diameter - 2 * tube_wall_thickness

# Define the tube shape
tube_shape = (
    cq.Workplane("XY")
    .transformed(offset=cq.Vector(CAD_path[0]), rotate=cq.Vector(0, 90, 270))
    .circle(tube_outer_diameter / 2)
    .circle(tube_inner_diameter / 2)
)

#show_object(tube_shape, name="Path Shape Tube")

# Path shape configurable height U shape
# Parameters
u_shape_height_width = 10.0 -0.0001 # Overall width and initial height of the U-shape
u_shape_wall_thickness = 2.0        # Wall thickness
lower_distance = 2.0                # Amount to shorten the vertical sides

# Adjusted top Y-coordinate
adjusted_top_y = u_shape_height_width / 2 - lower_distance

# Note, this shape is actually drawn as an n
u_shape_adjusted_height = (
    cq.Workplane("XY")
    .transformed(offset=cq.Vector(CAD_path[0]), rotate=cq.Vector(0, 90, 270))
    .moveTo(- u_shape_height_width / 2, u_shape_height_width / 2)                           # Top left of U-shape
    .lineTo(u_shape_height_width / 2, u_shape_height_width / 2)                             # Top horizontal line
    .lineTo(u_shape_height_width / 2, -adjusted_top_y)                                      # Right vertical line
    .lineTo(u_shape_height_width / 2 - u_shape_wall_thickness, -adjusted_top_y)   # Right wall thickness
    .lineTo(u_shape_height_width / 2 - u_shape_wall_thickness, u_shape_height_width / 2 - u_shape_wall_thickness)               # Bottom inner part
    .lineTo(-u_shape_height_width / 2 + u_shape_wall_thickness, u_shape_height_width / 2 - u_shape_wall_thickness)              # Bottom inner part (other side)
    .lineTo(-u_shape_height_width / 2 + u_shape_wall_thickness, -adjusted_top_y)             # Left wall thickness
    .lineTo(-u_shape_height_width / 2, -adjusted_top_y)             # Left vertical line
    .close()                    # Close the U-shape
)

#show_object(u_shape_adjusted_height, name="Path Shape Lowered Height U")

# Note, this shape is actually drawn as an n
u_shape_adjusted_height_rectangle_1 = (
    cq.Workplane("XY")
    .transformed(offset=cq.Vector(CAD_path[0]), rotate=cq.Vector(0, 90, 270))
    .moveTo(-u_shape_height_width / 2, -adjusted_top_y) 
    .lineTo(-u_shape_height_width / 2, -u_shape_height_width / 2)
    .lineTo(-u_shape_height_width / 2 + u_shape_wall_thickness, -u_shape_height_width / 2)   # Right wall thickness
    .lineTo(-u_shape_height_width / 2 + u_shape_wall_thickness, -u_shape_height_width / 2 + lower_distance)   # Right wall thickness
    .close()                    # Close the shape
)

#show_object(u_shape_adjusted_height_rectangle_1, name="Path Shape Lowered Height U 1")

# Note, this shape is actually drawn as an n
u_shape_adjusted_height_rectangle_2 = (
    cq.Workplane("XY")
    .transformed(offset=cq.Vector(CAD_path[0]), rotate=cq.Vector(0, 90, 270))
    .moveTo(u_shape_height_width / 2, -adjusted_top_y) 
    .lineTo(u_shape_height_width / 2, -u_shape_height_width / 2)
    .lineTo(u_shape_height_width / 2 - u_shape_wall_thickness, -u_shape_height_width / 2)   # Right wall thickness
    .lineTo(u_shape_height_width / 2 - u_shape_wall_thickness, -u_shape_height_width / 2 + lower_distance)   # Right wall thickness
    .close()                    # Close the shape
)

#show_object(u_shape_adjusted_height_rectangle_2, name="Path Shape Lowered Height U 2")

# Create the path in 3D using a spline
path = cq.Workplane("XY").polyline(CAD_path)
path1 = cq.Workplane("XY").polyline(CAD_path)
path2 = cq.Workplane("XY").polyline(CAD_path)

# Sweep the U-shape along the 3D path
path_body = u_shape_adjusted_height.sweep(path, transition='right') #right, round
path_body1 = u_shape_adjusted_height_rectangle_1.sweep(path1, transition='right') #right, round
path_body2 = u_shape_adjusted_height_rectangle_2.sweep(path2, transition='right') #right, round

# Prepare for cutting around path body, makes start flush with sphere edge
# Create the cross-sectional profile of the hollow sphere
hollow_sphere_profile = (
    cq.Workplane("XZ")
    .moveTo(0, sphere_flange_radius)
    .threePointArc((-sphere_flange_radius, 0), (0, -sphere_flange_radius))
    .lineTo(0, -sphere_inner_radius)
    .threePointArc((-sphere_inner_radius, 0), (0, sphere_inner_radius))
    .close()
)

# Revolve the profile to create the hollow sphere solid
hollow_sphere = hollow_sphere_profile.revolve(angleDegrees=360)

# Perform the cut operation
path_body = path_body.cut(hollow_sphere)

########
# Ball #
########

# Note, relies on path being availible with starting point
ball = cq.Workplane("XY").sphere(ball_diameter / 2).translate(CAD_path[1])

##################
# Mounting holes #
##################

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

# Cut the holes in applicable bodies
mounting_ring = mounting_ring.cut(holes)
dome_top = dome_top.cut(holes)
dome_bottom = dome_bottom.cut(holes)

###########
# Display #
###########

# Display the mounting ring
show_object(mounting_ring, name="Mounting Ring")

# Show domes
show_object(dome_top, name="Dome Bottom", options={"alpha": 0.9, "color": (1, 1, 1)})
show_object(dome_bottom, name="Dome Top", options={"alpha": 0.9, "color": (1, 1, 1)})

# Show the final path
show_object(path_body, name="Path", options={"alpha": 0.0})
show_object(path_body1, name="Path1", options={"alpha": 0.0})
show_object(path_body2, name="Path2", options={"alpha": 0.0})
show_object(ball, name="Ball", options={"color": (192, 192, 192)})