import cadquery as cq

# Define the parameters for the puzzle
sphere_outer_diameter = 100  # Outer diameter in mm
sphere_flange_diameter = 120
sphere_thickness = 3         # Thickness in mm (cross-sectional radius)
sphere_inner_diameter = sphere_outer_diameter - (2 * sphere_thickness)  # Inner diameter in mm
ring_thickness = 3           # Thickness of the ring
ball_diameter = 4

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
'''

# Calculate the outer and inner radius
outer_radius = sphere_outer_diameter / 2
inner_radius = outer_radius - sphere_thickness

dome_top = (
    cq.Workplane("front")
    .moveTo(outer_radius, 0)
    .lineTo(0, sphere_thickness)
    .lineTo(2.0, 1.0)
    .threePointArc((1.0, 1.5), (0.0, 1.0))
    .close()
    .revolve(360, (0, 0, 0), (0, 0, 1))
)

show_object(dome_top, name="Dome Top Alt", options={"alpha": 0.9, "color": (1, 1, 1)})


# Create the outer half-sphere (dome) by cutting a full sphere
dome_outer = (
    cq.Workplane("XY")
    .sphere(outer_radius)           # Create the outer sphere
    .cut(cq.Workplane("XY").box(2 * outer_radius, 2 * outer_radius, outer_radius, centered=(True, True, False)))  # Slice it in half along the XY plane
)

# Create the inner half-sphere (for hollowing the dome)
dome_inner = (
    cq.Workplane("XY")
    .sphere(inner_radius)           # Create the inner sphere (for hollowing)
    .cut(cq.Workplane("XY").box(2 * inner_radius, 2 * inner_radius, inner_radius, centered=(True, True, False)))  # Slice the inner half-sphere
)

# Hollow out the outer dome by subtracting the inner dome from it
dome_hollowed = dome_outer.cut(dome_inner)

# Move the hollowed dome upwards (offset from the XY plane)
dome_offset = dome_hollowed.translate((0, 0, -0.5 * ring_thickness))

# Mirror the extruded half along the XY plane
dome_offset_mirrored = dome_offset.mirror(mirrorPlane="XY")

show_object(dome_offset, name="Dome Bottom", options={"alpha": 0.9, "color": (1, 1, 1)})
show_object(dome_offset_mirrored, name="Dome Top", options={"alpha": 0.9, "color": (1, 1, 1)})

###########
# Flanges #
###########

# Calculate the radius of the sphere glange from the outer and inner diameters
outer_radius = sphere_flange_diameter / 2
inner_radius = sphere_inner_diameter / 2 + 2 * sphere_thickness

# Create the flange ring as a difference between two circles, then extrude symmetrically
flange = (
    cq.Workplane("XY")
    .circle(outer_radius)          # Outer circle
    .circle(inner_radius)          # Inner circle (hole)
    .extrude(ring_thickness / 2)   # Extrude half the thickness upwards
)

# Move the hollowed dome upwards (offset from the XY plane)
flange_offset = flange.translate((0, 0, 0.5 * ring_thickness))

# Mirror the extruded half along the XY plane
flange_offset_mirrored = flange_offset.mirror(mirrorPlane="XY")

show_object(flange_offset, name="Dome Bottom Flange", options={"alpha": 0.9, "color": (1, 1, 1)})
show_object(flange_offset_mirrored, name="Dome Top Flange", options={"alpha": 0.9, "color": (1, 1, 1)})

'''

########
# Path #
########

# Define the 3D path using X, Y, and Z coordinates
CAD_path = [(-35, 0, 0), (-30, 0, 0), (-20, 0, 0), (-20, -10, 0), (-20, -20, 0), (-10, -20, 0), (-10, -30, 0), (0, -30, 0), (10, -30, 0), (10, -20, 0), (10, -10, 0), (20, -10, 0), (30, -10, 0), (30, -20.0001, 0), (30, -20.0001, 10), (30, -10, 10.0001), (30, 0, 10.0001), (30, 0, 0), (30, 10, 0), (30, 20, 0), (20, 20, 0), (10, 20, 0), (0, 20, 0), (-10, 20, 0), (-10, 30, 0)]
u_shape_height_width = 9
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
show_object(u_shape, name="Path Shape")

# Create the path in 3D using a spline
path = cq.Workplane("XY").polyline(CAD_path)

# Sweep the U-shape along the 3D path
u_beam = u_shape.sweep(path, transition='right')

# Show the final swept U-beam
show_object(u_beam, name="Path", options={"alpha": 0.1})

########
# Ball #
########

# Note, relies on path being availible with starting point

ball = cq.Workplane("XY").sphere(ball_diameter / 2).translate(CAD_path[1])
show_object(ball, name="Ball", options={"color": (192, 192, 192)})