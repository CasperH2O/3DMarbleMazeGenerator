# solid_modeller.py

import cadquery as cq
import os
from ocp_vscode import *

from config import Config
from config import CaseShape
from puzzle.puzzle import Puzzle
from shapes.path_profile_type_shapes import *
from shapes.path_builder import PathBuilder
from shapes.case_sphere import CaseSphere
from shapes.case_box import CaseBox
from shapes.case_sphere_with_flange import CaseSphereWithFlange

if 'show_object' not in globals():
    def show_object(*args, **kwargs):
        pass

########
# Case #
########

# Create the appropriate case
if Config.Puzzle.CASE_SHAPE == CaseShape.SPHERE:
    case = CaseSphere()
elif Config.Puzzle.CASE_SHAPE == CaseShape.BOX:
    case = CaseBox()
elif Config.Puzzle.CASE_SHAPE == CaseShape.SPHERE_WITH_FLANGE:
    case = CaseSphereWithFlange()
else:
    raise ValueError(f"Unknown CASE_SHAPE '{Config.Puzzle.CASE_SHAPE}' specified in config.py.")

# Get the case objects
case_objects = case.get_cad_objects()

# Display case objects, with options if applicable
for name, value in case_objects.items():
    if isinstance(value, tuple):
        obj, options = value
        if name == 'Mounting Ring' and Config.Puzzle.CASE_SHAPE == CaseShape.SPHERE_WITH_FLANGE:
            mounting_ring = obj
        else:
            show_object(obj, name=name, options=options)
    else:
        obj = value
        show_object(obj, name=name)

########
# Path #
########

# Create the puzzle
puzzle = Puzzle(
    node_size=Config.Puzzle.NODE_SIZE,
    seed=Config.Puzzle.SEED,
    case_shape=Config.Puzzle.CASE_SHAPE
)

# Get the total path nodes
CAD_nodes = puzzle.total_path

# Initialize the PathBuilder
path_builder = PathBuilder(puzzle.path_architect)

# Create the loft between the first two nodes
# todo, improve/fix/investigate start area creation
start_area = path_builder.create_start_area_funnel(CAD_nodes)

# Prepare profiles and paths
path_builder.prepare_profiles_and_paths()

# For debugging: show all profiles before the sweep
#for idx, profile in enumerate(path_builder.profiles):
    #show_object(profile, name=f"Profile_{idx}")

# For debugging: specify the indices of segments to process
indices_to_sweep = None  # Set to None to process all segments, or provide a list like [0, 1, 2]

# Optionally, display the selected profiles and paths
if indices_to_sweep is not None:
    selected_segments = [path_builder.path_architect.segments[i] for i in indices_to_sweep]
else:
    selected_segments = path_builder.path_architect.segments

'''        
Broken with segments change
for idx, segment in enumerate(selected_segments):
    actual_idx = indices_to_sweep[idx] if indices_to_sweep else idx
    if segment.profile != None and segment.path != None:
        profile = segment.profile
        path = segment.path
        show_object(profile, name=f"Profile_{actual_idx}")
        show_object(path, name=f"Path_{actual_idx}")
'''

# Now sweep the selected profiles along the paths
path_builder.sweep_profiles_along_paths(indices=indices_to_sweep)

# Optionally, display the swept bodies individually
'''        
broken, segment change
#for idx, body in enumerate(path_bodies):
    #actual_idx = indices_to_sweep[idx] if indices_to_sweep else idx
    #show_object(body, name=f"Swept_Body_{actual_idx}")
'''
    
final_path_bodies = path_builder.build_final_path_body()

# Get the shape to cut for the current case
cut_shape = case.get_cut_shape()

# Handle standard path
if final_path_bodies['standard']:
    
    # Combine path and start area
    # Todo, dirty hack with using first tuple
    standard_path = final_path_bodies['standard'].union(start_area[0])
    
    # Cut the standard path from the case for bridge
    standard_path = standard_path.cut(cut_shape)

# Handle support bodies separately
if final_path_bodies['support']:
    support_path = final_path_bodies['support'].cut(cut_shape)

# Handle coloring bodies separately
if final_path_bodies['coloring']:

    # Todo, dirty hack with using second tuple entry
    coloring_path = final_path_bodies['coloring'].union(start_area[1]).cut(cut_shape)

if Config.Puzzle.CASE_SHAPE == CaseShape.SPHERE_WITH_FLANGE:
    mounting_ring = mounting_ring.cut(standard_path)

######################
# Ball and ball path #
######################

# Extract node positions from CAD_nodes
node_positions = [(node.x, node.y, node.z) for node in CAD_nodes]

# Place the ball at the second node position
ball = cq.Workplane("XY").sphere(Config.Puzzle.BALL_DIAMETER / 2).translate(node_positions[1])

# Create a circular profile on a rotated work plane at the ball's position
ball_path_profile = (
    cq.Workplane("XY")
    .transformed(offset=cq.Vector(node_positions[1]), rotate=(0, 90, 270))
    .circle(Config.Puzzle.BALL_DIAMETER / 10)
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

show_object(standard_path, name="Standard Path", options={"alpha": 1.0, "color": (57, 255, 20)})
show_object(support_path, name="Support Path", options={"alpha": 0.1, "color": (1, 1, 1)})
show_object(coloring_path, name="Coloring Path", options={"alpha": 1.0, "color": (40, 40, 43)})

if Config.Puzzle.CASE_SHAPE == CaseShape.SPHERE_WITH_FLANGE:
    show_object(mounting_ring, name="Mounting Ring", options={"alpha": 1.0, "color": (40, 40, 43)})

show_object(ball, name="Ball", options={"color": (192, 192, 192)})
show_object(ball_path, name="Ball Path", options={"color": (192, 192, 192)})

# Fetch current states from the viewer
current_states = status()["states"]

# Initialize a dictionary to hold the new configuration
new_config = {}

# Iterate through each group in the current states
for group, config in current_states.items():
    # If the group is "Standard Path", retain its current configuration
    if group == "/Group/Standard Path":
        new_config[group] = config
    else:
        # Set other groups to [1, 0]
        new_config[group] = [1, 0]

# Apply the new configuration
set_viewer_config(states=new_config)

status()["states"]

###############
# Export Step #
###############

# Chosen step over stl format for improved scaling units and curved line accuracy

# Construct folder name and path
folder_name = f"Case-{Config.Puzzle.CASE_SHAPE}-Seed-{Config.Puzzle.SEED}"
path = os.path.join("..", "CAD", "STEP", folder_name)

# Check if path exists, if not create the folder
if not os.path.exists(path):
    os.makedirs(path)

# Define objects we want to export
objects_to_export = {
    #"Mounting Ring": mounting_ring,
    #"Dome Top": dome_top,
    #"Dome Bottom": dome_bottom,
    #"Path": path_body,
    "Ball": ball,
}

# Todo, step path is incorrect, use stl

# Export each object
for name, obj in objects_to_export.items():
    file_path = os.path.join(path, f"{name}.stl")
    obj.val().exportStl(file_path)
    file_path = os.path.join(path, f"{name}.stl")
    obj.val().exportStep(file_path)