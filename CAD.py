# cad.py

import cadquery as cq
import math

from puzzle.casing import *
from puzzle.puzzle import Puzzle
from shapes.path_shapes import *
from utils.config import (
    DIAMETER, SPHERE_FLANGE_DIAMETER, SHELL_THICKNESS, RING_THICKNESS, 
    BALL_DIAMETER, MOUNTING_HOLE_DIAMETER, MOUNTING_HOLE_AMOUNT, NODE_SIZE, 
    SEED, CASE_SHAPE
)
from puzzle.node_creator import SphereGridNodeCreator
from puzzle.pathfinder import AStarPathFinder

# Define the parameters for the puzzle
sphere_outer_diameter = DIAMETER
sphere_flange_diameter = SPHERE_FLANGE_DIAMETER
sphere_thickness = SHELL_THICKNESS
ring_thickness = RING_THICKNESS
ball_diameter = BALL_DIAMETER
mounting_hole_diameter = MOUNTING_HOLE_DIAMETER
mounting_hole_amount = MOUNTING_HOLE_AMOUNT

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
    .extrude(sphere_thickness)   # Extrude thickness
)

# Move to center
mounting_ring = mounting_ring.translate((0, 0, -0.5 * sphere_thickness))

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
# show_object(profile, name="Profile", options={"alpha": 0.5, "color": (1, 0, 0)})

# Revolve the profile
dome_bottom = profile.revolve(angleDegrees=360, axisStart=(0, 0, 0), axisEnd=(0, 1, 0))

# Move to make place for mounting ring
dome_bottom = dome_bottom.translate((0, 0, 0.5 * ring_thickness + 0.01))

# Mirror the dome for the other side
dome_top = dome_bottom.mirror(mirrorPlane="XY")

########
# Path #
########

# Initialize the node creator and pathfinder
casing = SphereCasing(diameter=DIAMETER, shell_thickness=SHELL_THICKNESS)
node_creator = SphereGridNodeCreator()
pathfinder = AStarPathFinder()

# Create the puzzle
puzzle = Puzzle(
    node_size=NODE_SIZE,
    seed=SEED,
    case_shape=CASE_SHAPE
)

if puzzle.total_path:
    print(f"Total path length: {len(puzzle.total_path)}")
    # Get the CAD path from the puzzle's total_path
    CAD_path = [(node.x, node.y, node.z) for node in puzzle.total_path]
else:
    print("No path could be constructed to connect all waypoints.")
    CAD_path = []

if CAD_path:
    # Define the path shape
    u_shape_parameters = {
        'height_width': 10.0 - 0.0001,
        'wall_thickness': 2.0,
        'lower_distance': 2.0
    }
    u_shape = create_u_shape_adjusted_height(CAD_path[0], **u_shape_parameters)
    u_shape_adjusted_height_rectangle_1 = create_u_shape_adjusted_height_edge_1(CAD_path[0], **u_shape_parameters)
    u_shape_adjusted_height_rectangle_2 = create_u_shape_adjusted_height_edge_2(CAD_path[0], **u_shape_parameters)

    # Create the 3D path using a polyline
    path = cq.Workplane("XY").polyline(CAD_path)
    path1 = cq.Workplane("XY").polyline(CAD_path)
    path2 = cq.Workplane("XY").polyline(CAD_path)


    # Sweep the U-shape along the 3D path
    path_body = u_shape.sweep(path, transition='right')
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
    path_body1 = path_body1.cut(hollow_sphere)
    path_body2 = path_body2.cut(hollow_sphere)

    ######################
    # Ball and ball path #
    ######################

    # Place the ball at the second node position
    if len(CAD_path) > 1:
        ball = cq.Workplane("XY").sphere(ball_diameter / 2).translate(CAD_path[1])
        
        # Create a circular profile on a rotated workplane
        ball_path_profile = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(CAD_path[1]), rotate=(0, 90, 270))
            .circle(ball_diameter / 10)
        )
        
        # Create the 3D path using a polyline starting from the same spot as the ball
        path = cq.Workplane("XY").polyline(CAD_path[1:])
        ball_path = ball_path_profile.sweep(path, transition='right') 
        

##################
# Mounting Holes #
##################

# Calculate the hole pattern radius
hole_pattern_radius = (sphere_outer_radius + sphere_flange_radius) / 2  # Average radius

# Create a work plane on the XY plane
wp = cq.Workplane("XY")

# Define the hole pattern
holes = (
    wp
    .workplane()
    .polarArray(hole_pattern_radius, 0, 360, mounting_hole_amount, fill=True)
    .circle(mounting_hole_diameter / 2)
    .extrude(3 * sphere_thickness, both=True)  # Extrude length sufficient to cut through the bodies
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
show_object(path_body1, name="Path Edge 1", options={"alpha": 0.0})
show_object(path_body2, name="Path Edge 2", options={"alpha": 0.0})

show_object(ball, name="Ball", options={"color": (192, 192, 192)})
#show_object(ball_path, name="Ball Path", options={"color": (192, 192, 192)})