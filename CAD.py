# cad.py

import cadquery as cq
import math
import os

from puzzle.casing import *
from puzzle.puzzle import Puzzle
from shapes.path_shapes import *
from shapes.path_builder import PathBuilder
from utils.config import (
    DIAMETER, SPHERE_FLANGE_DIAMETER, SHELL_THICKNESS, RING_THICKNESS, 
    BALL_DIAMETER, MOUNTING_HOLE_DIAMETER, MOUNTING_HOLE_AMOUNT, NODE_SIZE, 
    SEED, CASE_SHAPE, PATH_TYPES
)
from puzzle.node_creator import SphereGridNodeCreator
from puzzle.path_finder import AStarPathFinder

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
dome_profile = (
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

# Display the dome profile
# show_object(dome_profile, name="Dome Profile", options={"alpha": 0.5, "color": (1, 0, 0)})

# Revolve the dome profile
dome_bottom = dome_profile.revolve(angleDegrees=360, axisStart=(0, 0, 0), axisEnd=(0, 1, 0))

# Move to make place for mounting ring
dome_bottom = dome_bottom.translate((0, 0, 0.5 * ring_thickness + 0.01))

# Mirror the dome for the other side
dome_top = dome_bottom.mirror(mirrorPlane="XY")

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

########
# Path #
########

# Create the puzzle
puzzle = Puzzle(
    node_size=NODE_SIZE,
    seed=SEED,
    case_shape=CASE_SHAPE
)

# Get the total path nodes
CAD_nodes = puzzle.total_path

# Initialize the PathBuilder
path_builder = PathBuilder(seed=SEED)

# Build the path step by step
# Assign path types and group nodes
CAD_nodes = path_builder.assign_path_types(CAD_nodes)
segments = path_builder.group_nodes_by_path_type(CAD_nodes)

# Prepare profiles and paths
path_builder.prepare_profiles_and_paths(segments)

# For debugging: show all profiles before the sweep
#for idx, profile in enumerate(path_builder.profiles):
    #show_object(profile, name=f"Profile_{idx}")

# For debugging: specify the indices of profiles and paths to process
indices_to_sweep = list(range(len(path_builder.profiles)))  # Change this list to the indices you want to process

# Optionally, display the selected profiles and paths
for idx in indices_to_sweep:
    profile = path_builder.profiles[idx]
    path = path_builder.paths[idx]
    show_object(profile, name=f"Profile_{idx}", options={"color": (192, 192, 20)})
    show_object(path, name=f"Path_{idx}", options={"color": (20, 192, 192)})

# Now sweep the selected profiles along the paths
path_bodies = path_builder.sweep_profiles_along_paths(indices=indices_to_sweep)

# Build the final path body
if path_bodies:
    final_path_body = path_builder.build_final_path_body(path_bodies)

    # Use final_path_body in the rest of your CAD model
    path_body = final_path_body

    # Optionally, display the swept bodies
    for idx, body in zip(indices_to_sweep, path_bodies):
        show_object(body, name=f"Swept_Body_{idx}")
else:
    print("No path bodies were created.")

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

# Perform the cut operation to make start flush with sphere on the inside
#path_body = path_body.cut(hollow_sphere)

######################
# Ball and ball path #
######################

# Extract node positions from CAD_nodes
node_positions = [(node.x, node.y, node.z) for node in CAD_nodes]

# Place the ball at the second node position
ball = cq.Workplane("XY").sphere(ball_diameter / 2).translate(node_positions[1])

# Create a circular profile on a rotated workplane at the ball's position
ball_path_profile = (
    cq.Workplane("XY")
    .transformed(offset=cq.Vector(node_positions[1]), rotate=(0, 90, 270))
    .circle(ball_diameter / 10)
)

# Create the 3D path using a polyline starting from the second node
# Since we have segments now, we can reconstruct the full path from the node positions
ball_path_points = node_positions[1:]  # Exclude the first node if needed

# Create the path
path = cq.Workplane("XY").polyline(ball_path_points)

# Sweep the profile along the path
ball_path = ball_path_profile.sweep(path, transition='right')

###########
# Display #
###########

# Display the mounting ring
show_object(mounting_ring, name="Mounting Ring")

# Show domes
show_object(dome_top, name="Dome Bottom", options={"alpha": 0.9, "color": (1, 1, 1)})
show_object(dome_bottom, name="Dome Top", options={"alpha": 0.9, "color": (1, 1, 1)})

# Show the final path
#show_object(path_body, name="Path", options={"alpha": 0.0})

#show_object(ball, name="Ball", options={"color": (192, 192, 192)})
show_object(ball_path, name="Ball Path", options={"color": (192, 192, 192)})

###############
# Export Step #
###############

# Chosen step over stl format for improved scaling units and curved line accuracy

# Construct folder name and path
folder_name = f"Case-{CASE_SHAPE}-Seed-{SEED}"
path = os.path.join("..", "CAD", "STEP", folder_name)

# Check if path exists, if not create the folder
if not os.path.exists(path):
    os.makedirs(path)

# Define objects we want to export
objects_to_export = {
    "Mounting Ring": mounting_ring,
    "Dome Top": dome_top,
    "Dome Bottom": dome_bottom,
    #"Path": path_body,
    "Ball": ball,
}

# Export each object
for name, obj in objects_to_export.items():
    file_path = os.path.join(path, f"{name}.step")
    obj.val().exportStep(file_path)