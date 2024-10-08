# cad.py

import cadquery as cq
import os
import config
from puzzle.puzzle import Puzzle
from shapes.path_shapes import *
from shapes.path_builder import PathBuilder
from shapes.case_sphere import CaseSphere
from shapes.case_box import CaseBox
from shapes.case_sphere_with_flange import CaseSphereWithFlange

########
# Case #
########

# Instantiate the appropriate case
if config.CASE_SHAPE == 'Sphere':
    case = CaseSphere(config)
elif config.CASE_SHAPE == 'Box':
    case = CaseBox(config)
elif config.CASE_SHAPE == 'Sphere with flange':
    case = CaseSphereWithFlange(config)
else:
    raise ValueError(f"Unknown CASE_SHAPE '{config.CASE_SHAPE}' specified in config.py.")

# Get the CAD objects
cad_objects = case.get_cad_objects()

# Display CAD objects, if they have options, apply them
for name, value in cad_objects.items():
    if isinstance(value, tuple):
        obj, options = value
        show_object(obj, name=name, options=options)
    else:
        obj = value
        show_object(obj, name=name)

########
# Path #
########

# Create the puzzle
puzzle = Puzzle(
    node_size=config.NODE_SIZE,
    seed=config.SEED,
    case_shape=config.CASE_SHAPE
)

# Get the total path nodes
CAD_nodes = puzzle.total_path

# Initialize the PathBuilder
path_builder = PathBuilder()

# Build the path step by step
# Assign path types and group nodes
CAD_nodes = path_builder.assign_path_profile_and_curve_types(CAD_nodes)
segments = path_builder.group_nodes_by_path_type(CAD_nodes)

# Prepare profiles and paths
path_builder.prepare_profiles_and_paths(segments)

# For debugging: show all profiles before the sweep
#for idx, profile in enumerate(path_builder.profiles):
    #show_object(profile, name=f"Profile_{idx}")

# For debugging: specify the indices of segments to process
indices_to_sweep = None  # Set to None to process all segments, or provide a list like [0, 1, 2]

# Optionally, display the selected profiles and paths
if indices_to_sweep is not None:
    selected_segments = [path_builder.segments_data[i] for i in indices_to_sweep]
else:
    selected_segments = path_builder.segments_data

for idx, segment in enumerate(selected_segments):
    actual_idx = indices_to_sweep[idx] if indices_to_sweep else idx
    profile = segment['profile']
    path = segment['path']
    show_object(profile, name=f"Profile_{actual_idx}")
    show_object(path, name=f"Path_{actual_idx}")

# Now sweep the selected profiles along the paths
path_bodies = path_builder.sweep_profiles_along_paths(indices=indices_to_sweep)

final_path_body = path_builder.build_final_path_body(path_bodies)
# Use final_path_body in the rest of your CAD model
path_body = final_path_body

# Optionally, display the swept bodies
for idx, body in enumerate(path_bodies):
    actual_idx = indices_to_sweep[idx] if indices_to_sweep else idx
    #show_object(body, name=f"Swept_Body_{actual_idx}")

# Get the shape to cut for the current case
cut_shape = case.get_cut_shape()

# Perform the cut operation to make the path body flush with the case
path_body = path_body.cut(cut_shape)

######################
# Ball and ball path #
######################

# Extract node positions from CAD_nodes
node_positions = [(node.x, node.y, node.z) for node in CAD_nodes]

# Place the ball at the second node position
ball = cq.Workplane("XY").sphere(config.BALL_DIAMETER / 2).translate(node_positions[1])

# Create a circular profile on a rotated work plane at the ball's position
ball_path_profile = (
    cq.Workplane("XY")
    .transformed(offset=cq.Vector(node_positions[1]), rotate=(0, 90, 270))
    .circle(config.BALL_DIAMETER / 10)
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

# Show the final path
#show_object(path_body, name="Path", options={"alpha": 0.0})

show_object(ball, name="Ball", options={"color": (192, 192, 192)})
show_object(ball_path, name="Ball Path", options={"color": (192, 192, 192)})

###############
# Export Step #
###############

# Chosen step over stl format for improved scaling units and curved line accuracy

# Construct folder name and path
folder_name = f"Case-{config.CASE_SHAPE}-Seed-{config.SEED}"
path = os.path.join("..", "CAD", "STEP", folder_name)

# Check if path exists, if not create the folder
if not os.path.exists(path):
    os.makedirs(path)

# Define objects we want to export
objects_to_export = {
    #"Mounting Ring": mounting_ring,
    #"Dome Top": dome_top,
    #"Dome Bottom": dome_bottom,
    "Path": path_body,
    "Ball": ball,
}

# Todo, step path is incorrect, use stl

# Export each object
for name, obj in objects_to_export.items():
    file_path = os.path.join(path, f"{name}.stl")
    obj.val().exportStl(file_path)
    file_path = os.path.join(path, f"{name}.step")
    obj.val().exportStep(file_path)