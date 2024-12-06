# solid_modeller.py

from build123d import *
import os
from ocp_vscode import *

from config import Config
from config import CaseShape
from puzzle.puzzle import Puzzle
from cad.path_profile_type_shapes import *
from cad.path_builder import PathBuilder
from cad.case_sphere import CaseSphere
from cad.case_box import CaseBox
from cad.case_sphere_with_flange import CaseSphereWithFlange
from cad.case_sphere_with_flange_enclosed_two_sides import CaseSphereWithFlangeEnclosedTwoSides

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
elif Config.Puzzle.CASE_SHAPE == CaseShape.SPHERE_WITH_FLANGE_ENCLOSED_TWO_SIDES:
    case = CaseSphereWithFlangeEnclosedTwoSides()    
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

support_path = None
coloring_path = None

# Create the puzzle
puzzle = Puzzle(
    node_size=Config.Puzzle.NODE_SIZE,
    seed=Config.Puzzle.SEED,
    case_shape=Config.Puzzle.CASE_SHAPE
)

# Get the total path nodes
CAD_nodes = puzzle.total_path

'''
# Initialize the PathBuilder
path_builder = PathBuilder(puzzle.path_architect)

# Create the loft between the first two nodes
# todo, improve/fix/investigate start area creation
start_area = path_builder.create_start_area_funnel(CAD_nodes)

# Prepare profiles and paths
path_builder.prepare_profiles_and_paths()

# Now sweep the selected profiles along the paths
path_builder.sweep_profiles_along_paths()

# Make holes in o shape path profile segments (and it's respective support)
path_builder.cut_holes_in_o_shape_path_profile_segments()
    
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

'''
######################
# Ball and ball path #
######################

# Extract node positions from CAD_nodes
node_positions = [(node.x, node.y, node.z) for node in CAD_nodes]

# Create and place the ball at the start of the path
with BuildPart(Pos(node_positions[1])) as ball:
    Sphere(Config.Puzzle.BALL_DIAMETER / 2)

# Create ball path indicator
with BuildPart()as ball_path:
    with BuildLine() as ball_path_line:
        Polyline(node_positions[1:]) # Exclude the first node
    with BuildSketch(ball_path_line.line^0) as ball_path_sketch:
        Circle(Config.Puzzle.BALL_DIAMETER / 10)
    sweep(transition=Transition.RIGHT)

###########
# Display #
###########
'''
# Show the final path
show_object(standard_path, name="Standard Path", options={"color": Config.Puzzle.PATH_COLOR})

# Show the support path, if it exists
if support_path:
    show_object(support_path, name="Support Path", options={"alpha": 0.1, "color": (1, 1, 1)})

# Show the coloring path, if it exists
if coloring_path:
    show_object(coloring_path, name="Coloring Path", options={"color": Config.Puzzle.PATH_ACCENT_COLOR})

if Config.Puzzle.CASE_SHAPE == CaseShape.SPHERE_WITH_FLANGE:
    show_object(mounting_ring, name="Mounting Ring", options={"color": Config.Puzzle.MOUNTING_RING_COLOR})
'''
show_object(ball, name="Ball", options={"color": Config.Puzzle.BALL_COLOR})
show_object(ball_path, name="Ball Path", options={"color": Config.Puzzle.BALL_COLOR})

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
'''
for name, obj in objects_to_export.items():
    file_path = os.path.join(path, f"{name}.stl")
    obj.val().exportStl(file_path)
    file_path = os.path.join(path, f"{name}.stl")
    obj.val().exportStep(file_path)
'''