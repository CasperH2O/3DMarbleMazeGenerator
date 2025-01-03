# cad/path_builder.py

from build123d import *
from typing import List
from ocp_vscode import *
import random

from config import *
from cad.path_profile_type_shapes import *
from config import PathProfileType, PathCurveModel
from cad.path_segment import PathSegment

class PathBuilder:
    """
    Handles the creation of segment shapes using profiles, sweeping along paths, and building the final path body.
    """

    def __init__(self, puzzle):
        """
        Initializes the PathBuilder with a reference to the PathArchitect.
        """
        self.path_architect = puzzle.path_architect
        self.total_path = puzzle.total_path
        self.node_size = Config.Puzzle.NODE_SIZE  # Store node size

        self.path_profile_type_parameters = Config.Path.PATH_PROFILE_TYPE_PARAMETERS
        self.path_profile_type_functions = {
            PathProfileType.L_SHAPE: create_l_shape,
            PathProfileType.L_SHAPE_ADJUSTED_HEIGHT: create_l_shape_adjusted_height,
            PathProfileType.O_SHAPE: create_o_shape,
            PathProfileType.O_SHAPE_SUPPORT: create_o_shape_support,
            PathProfileType.U_SHAPE: create_u_shape,
            PathProfileType.U_SHAPE_PATH_COLOR: create_u_shape_path_color,
            PathProfileType.U_SHAPE_ADJUSTED_HEIGHT: create_u_shape_adjusted_height,
            PathProfileType.V_SHAPE: create_v_shape,
            PathProfileType.V_SHAPE_PATH_COLOR: create_v_shape_path_color,
            PathProfileType.RECTANGLE_SHAPE: create_rectangle_shape
        }

        self.seed = Config.Puzzle.SEED
        random.seed(self.seed)  # Set the random seed for reproducibility

        # Create the start area based on the first segment
        self.start_area = self.create_start_area_funnel(self.path_architect.segments[0])

        # Prepare profiles and paths
        self.prepare_profiles_and_paths()

        # Sweep profiles along paths
        self.sweep_profiles_along_paths()

        # Make holes in O-shaped path segments
        self.cut_holes_in_o_shape_path_profile_segments()

        self.final_path_bodies = self.build_final_path_body()

    def prepare_profiles_and_paths(self):
        """
        Creates profiles and paths for each segment and stores them in the PathSegment objects.
        Skips segments that contain the puzzle start node.
        """
        segments = self.path_architect.segments
        previous_path_line = None
        angle = -90

        for segment in segments:
            # Skip segments that contain the start node
            if any(node.puzzle_start for node in segment.nodes):
                continue

            # Get the sub path points (positions of nodes in the segment)
            sub_path_points = [Vector(node.x, node.y, node.z) for node in segment.nodes]
            
            # Create the path based on the curve model
            if segment.curve_model == PathCurveModel.POLYLINE:
                if segment.curve_type == PathCurveType.DEGREE_90_SINGLE_PLANE:
                    if len(sub_path_points) >= 3:
                        first = sub_path_points[0]
                        middle = sub_path_points[len(sub_path_points) // 2]
                        last = sub_path_points[-1]
                        segment.path = Bezier([(first.X, first.Y, first.Z), (middle.X, middle.Y, middle.Z), (last.X, last.Y, last.Z)])
                elif segment.curve_type == PathCurveType.S_CURVE:
                    if len(sub_path_points) >= 3:
                        segment.path = Bezier([(p.X, p.Y, p.Z) for p in sub_path_points])
                else:
                    segment.path = Polyline([(p.X, p.Y, p.Z) for p in sub_path_points])
            elif segment.curve_model == PathCurveModel.SPLINE:
                # Call the method to attempt creating a valid spline path and profile
                segment.path, segment.curve_model = self.attempt_spline_path_creation(segment, sub_path_points)

            # Determine angle difference between the current segment and the previous segment for rotation
            if previous_path_line is not None:
                #print(f"Determining angle for segment index: {segment.main_index}.{segment.secondary_index}")
                #print(f"Comparing previous path line: {previous_path_line^1} with segment path: {segment.path^0}")
                loc1 = previous_path_line^1
                loc2 = segment.path^0
                angle += loc2.y_axis.direction.get_signed_angle(loc1.y_axis.direction, loc2.z_axis.direction)
                #print(f"\nAngle: {angle}")

            # Get parameters for the path profile type
            path_parameters = self.path_profile_type_parameters.get(segment.path_profile_type.value, {})

            # Store path profile sketch
            path_profile_function = self.path_profile_type_functions.get(segment.path_profile_type, create_u_shape)
            segment.path_profile = path_profile_function(**path_parameters, rotation_angle=angle)

            #increments = [0.1, 0.5, 0.9]
            #for val in increments:
            #    show_object(segment.path^val, name=f"Path Line - {val:.2f}, index {segment.main_index}.{segment.secondary_index}")

            # Create the accent profile if the segment has an accent profile type
            if segment.accent_profile_type != None:

                # Get parameters for the accent profile type
                accent_path_parameters = self.path_profile_type_parameters.get(segment.accent_profile_type.value, {})

                # Store accent color profile sketch
                accent_profile_function = self.path_profile_type_functions.get(segment.accent_profile_type, create_u_shape)
                segment.accent_profile = accent_profile_function(**accent_path_parameters, rotation_angle=angle)

            # Create the support profile if the segment has a support profile type
            if segment.support_profile_type != None:

                # Get parameters for the support profile type
                support_path_parameters = self.path_profile_type_parameters.get(segment.support_profile_type.value, {})

                # Store support profile sketch
                support_profile_function = self.path_profile_type_functions.get(segment.support_profile_type, create_u_shape)
                segment.support_profile = support_profile_function(**support_path_parameters, rotation_angle=angle)

            # Visualize the paths for debugging
            #show_object(segment.path, name=f"path_{segment.main_index}")

            previous_path_line = segment.path
            

    def sweep_profiles_along_paths(self):
        """
        Sweeps the stored profiles along their corresponding paths.
        """
        segments = self.path_architect.segments
        previous_path_line = None

        for segment in segments:

            # Skip segments that contain the start node
            if any(node.puzzle_start for node in segment.nodes):
                continue

            # Determine the start workplane, first segment, at the start, 
            # there after end of previous
            if previous_path_line is None:
                with BuildLine() as path_line:
                    add(segment.path) 
                workplane = path_line.line^0 
            else:
                #workplane = previous_path_line.line^1
                with BuildLine() as path_line:
                    add(segment.path) 
                workplane = path_line.line^0 

            if segment.curve_model == PathCurveModel.SPLINE:  
                try:
                    # Create a spline path sweep
                    with BuildPart() as sweep_spline_path_segment:
                        with BuildLine() as spline_path_line:
                            add(segment.path)      
                        with BuildSketch(workplane):
                            add(segment.path_profile)
                        sweep()  

                    segment.path_body = sweep_spline_path_segment                        

                    # Visualize the profiles and the path
                    #show_object(sweep_spline_path_segment, name=f"Sweep Spline Segment {segment.main_index}.{segment.secondary_index}")
                    #show_object(spline_path_line, name=f"Spline Path Line {segment.main_index}.{segment.secondary_index}")
                
                except Exception as e:
                    print(f"Error multi sweeping segment at index {segment.main_index}.{segment.secondary_index}: {e}")

            else:
                # For other curve models, use standard sweep

                try:
                    # Create path body out of path profile and path
                    with BuildPart() as sweep_path_segment:
                        with BuildLine() as path_line:
                            add(segment.path)      
                        # Create the sketch
                        with BuildSketch(workplane) as sketch_path_profile:
                            add(segment.path_profile)
                        sweep(transition=segment.transition_type)  

                    segment.path_body = sweep_path_segment

                    # Visualize the path, path profile and body
                    #show_object(path_line, name=f"{segment.main_index}.{segment.secondary_index} - Path")
                    #show_object(sketch_path_profile.sketch, name=f"{segment.main_index}.{segment.secondary_index} - Path Profile")
                    #show_object(sweep_path_segment, name=f"{segment.main_index}.{segment.secondary_index} - Path Body")
                    #show_object(sketch_path_profile.workplanes, name=f"{segment.main_index}.{segment.secondary_index} - Workplane")
                    
                    # Visualize the path line coordinate systems along the line
                    #increments = [0.1, 0.5, 0.9]
                    #for val in increments:
                    #    show_object(path_line.line ^ val, name=f"Path Line - {val:.2f}")

                except Exception as e:
                    print(f"Error sweeping segment at index {segment.main_index}.{segment.secondary_index}: {e}")

                try:
                    # Perform the sweep for the accent color body
                    if segment.accent_profile_type is not None:

                        # Create accent color part out of path color profile and path
                        with BuildPart() as sweep_accent_segment:
                            with BuildLine() as path_line:
                                add(segment.path)
                            # Create the sketch
                            with BuildSketch(workplane) as sketch_path_profile:
                                add(segment.accent_profile)
                            sweep(transition=segment.transition_type)  

                        segment.accent_body = sweep_accent_segment

                        # Visualize the color accent profile and body of this segment
                        #show_object(sweep_accent_segment, name=f"{segment.main_index}.{segment.secondary_index} - Accent Body")
                        #show_object(sketch_path_profile.sketch, name=f"{segment.main_index}.{segment.secondary_index} - Accent Profile")

                except Exception as e:
                    print(f"Error sweeping accent for segment at index {segment.main_index}.{segment.secondary_index}: {e}")

                try:
                    # Perform the sweep for the support body
                    if segment.support_profile_type is not None:

                        # Create part out of path profile and path
                        with BuildPart() as sweep_support_segment:
                            with BuildLine() as path_line:
                                add(segment.path)    
                            # Create the sketch
                            with BuildSketch(workplane) as path_support_sketch:
                                add(segment.support_profile)
                            sweep(transition=segment.transition_type)  

                        segment.support_body = sweep_support_segment
                        
                        # Visualize the support profile and body of this segment
                        #show_object(sweep_support_segment, name=f"{segment.main_index}.{segment.secondary_index} - Support Body")
                        #show_object(path_support_sketch.sketch, name=f"{segment.main_index}.{segment.secondary_index} - Support Profile")

                except Exception as e:
                    print(f"Error sweeping support for segment at index {segment.main_index}.{segment.secondary_index}: {e}")

            previous_path_line = path_line


    def build_final_path_body(self):
        # Create two separate combined bodies
        standard_body = None
        support_body = None
        coloring_body = None
        
        for segment in self.path_architect.segments:

            # Skip segments that contain the start node
            if any(node.puzzle_start for node in segment.nodes):
                continue

            # Skip segments without a body
            if not hasattr(segment, 'path_body') or segment.path_body is None:

                print(f"Segment at index {segment.main_index}-{segment.secondary_index} has no body.")
                continue            
            else:                
                # Build the path body
                if standard_body is None:
                    standard_body = segment.path_body.part
                else:
                    standard_body = standard_body + segment.path_body.part

            # Check if the segment has a (optional) support body
            if segment.support_body != None:
                if support_body is None:
                    support_body = segment.support_body.part
                else:
                    support_body = support_body + segment.support_body.part
            
            # Check if the segment has a (optional) color accent body
            if segment.accent_body != None:
                if coloring_body is None:
                    coloring_body = segment.accent_body.part
                else:
                    coloring_body = coloring_body + segment.accent_body.part
        
        return {
            'standard': standard_body,
            'support': support_body,
            'coloring': coloring_body
        }


    def create_start_area_funnel(self, segment):
        """
        Creates two lofted funnel shapes for the first segment of the puzzle
        One using U-shaped profiles, and another using U-shaped path coloring.
        """

        if len(segment.nodes) < 2:
            raise ValueError("Start area funnel, segment must contain at least two nodes.")

        # Extract first and second node x, y, z coordinates
        first_coords = (segment.nodes[0].x, segment.nodes[0].y, segment.nodes[0].z)
        second_coords = (segment.nodes[-1].x, segment.nodes[-1].y, segment.nodes[-1].z)

        # Create the standard path start area funnel
        with BuildPart() as start_area_standard:

            u_shape_params = Config.Path.PATH_PROFILE_TYPE_PARAMETERS[PathProfileType.U_SHAPE.value]

            with BuildLine() as start_area_line:
                Line(first_coords, second_coords)
            # Create the two U-shaped profiles
            with BuildSketch(start_area_line.line^0):
                add(create_u_shape(factor=3, **u_shape_params))
            with BuildSketch(start_area_line.line^1):
                add(create_u_shape(**u_shape_params))
            loft() 
    
        # Create the coloring path start area funnel
        with BuildPart() as start_area_coloring:

            u_shape_color_params = Config.Path.PATH_PROFILE_TYPE_PARAMETERS[PathProfileType.U_SHAPE_PATH_COLOR.value]

            with BuildLine() as start_area_line:
                Line(first_coords, second_coords)
            # Create the two color profiles
            with BuildSketch(start_area_line.line^0):
                add(create_u_shape_path_color(factor=3, **u_shape_color_params))
            with BuildSketch(start_area_line.line^1):
                add(create_u_shape_path_color(**u_shape_color_params))
            loft() 

        # Return both lofted shapes
        return start_area_standard, start_area_coloring


    def cut_holes_in_o_shape_path_profile_segments(self):
        n = 2  # Cut holes every n-th node
        possible_workplanes = [Plane.XY, Plane.XZ, Plane.YZ]
        main_index_to_workplane_direction = {}
        main_index_to_has_mounting_node = {}

        # First pass: Build main_index_to_has_mounting_node mapping
        for segment in self.path_architect.segments:
            main_index = segment.main_index
            if main_index not in main_index_to_has_mounting_node:
                # Check if any segment with this main_index has a mounting node
                has_mounting_node = any(
                    node.mounting
                    for s in self.path_architect.segments if s.main_index == main_index
                    for node in s.nodes
                )
                main_index_to_has_mounting_node[main_index] = has_mounting_node

        for segment in self.path_architect.segments:
            main_index = segment.main_index

            # Only process segments of PathProfileType O_SHAPE and POLYLINE
            if segment.path_profile_type not in [PathProfileType.O_SHAPE] or segment.curve_model != PathCurveModel.POLYLINE:
                continue  # Skip this segment

            # Determine the workplane direction for this main_index
            if main_index not in main_index_to_workplane_direction:
                has_mounting_node = main_index_to_has_mounting_node[main_index]
                if has_mounting_node:
                    # Must use 'XY' workplane
                    workplane_direction = Plane.XY
                else:
                    # Randomly choose a workplane direction
                    workplane_direction = random.choice(possible_workplanes)
                main_index_to_workplane_direction[main_index] = workplane_direction
            else:
                workplane_direction = main_index_to_workplane_direction[main_index]

            # Skip O_SHAPE_SUPPORT segments if workplane is not 'XY',
            # no need to print support underneath holes along the Z axis
            if workplane_direction != Plane.XY and segment.path_profile_type == PathProfileType.O_SHAPE_SUPPORT:
                continue  # Skip this segment

            # Skip segments that are not straight
            if segment.curve_type not in [PathCurveType.STRAIGHT, None]:
                continue  # Skip this segment

            hole_size = config.Puzzle.BALL_DIAMETER + 1
            total_nodes = len(segment.nodes)

            if total_nodes <= 2:
                continue  # Skip this segment

            start_idx = 1  # Exclude the first node
            end_idx = total_nodes - 1  # Exclude the last node

            for idx in range(start_idx, end_idx):
                node = segment.nodes[idx]
                # Adjust the index to align with the interval 'n'
                adjusted_idx = idx - start_idx
                if adjusted_idx % n != 0:
                    continue  # Skip this node

                # Create the cutting cylinder based on workplane direction
                with BuildPart() as cutting_cylinder:
                    with BuildSketch(workplane_direction):
                        Circle(hole_size / 2)
                    extrude(amount=-self.node_size / 2, both=True)

                # Move the cutting cylinder to the node position
                cutting_cylinder.part.position = (node.x, node.y, node.z)

                #show_object(cutting_cylinder, name=f"Cutting Cylinder at Node {idx}")

                segment.path_body.part = segment.path_body.part - cutting_cylinder.part
                if segment.support_body:
                    segment.support_body.part = segment.support_body.part - cutting_cylinder.part

        '''
                # Check for intersection
                if hole_cylinder.val().intersect(segment.path_body.val()).Volume() > 0:
                    segment.path_body = segment.path_body.cut(hole_cylinder)
                    if segment.support_body:
                        segment.support_body = segment.support_body.cut(hole_cylinder)

        '''

    def attempt_spline_path_creation(self, segment, sub_path_points):
        """
        Tries different spline point combinations to create a valid path and profile
        for a SPLINE curve model segment.

        Parameters:
        segment (PathSegment): The segment to process.
        sub_path_points (list of Vectors): The points defining the path.

        Returns:
        path: A feasible path for spline or a fallback polyline path.
        """

        segment_curve_model = segment.curve_model

        def option1():
            """
            Option 1: Use only the first and last nodes.
            This creates the simplest possible spline between start and end points.
            """
            if len(sub_path_points) >= 2:
                return [sub_path_points[0], sub_path_points[-1]]
            else:
                return None

        def option2():
            """
            Option 2: Use the first node, every second node in between, and the last node.
            This reduces the number of intermediate points to simplify the spline.
            """
            if len(sub_path_points) >= 2:
                spline_points = [sub_path_points[0]] + sub_path_points[1:-1:2] + [sub_path_points[-1]]
                return spline_points
            else:
                return None

        def option3():
            """
            Option 3: Use all nodes.
            This attempts to create a spline that passes through every node.
            """
            if len(sub_path_points) >= 2:
                return sub_path_points
            else:
                return None

        # Define the options for spline point combinations that will be attempted
        options = [option1, option2, option3]

        # Try each option
        for opt_idx, option in enumerate(options, 1):
            # Debug statement indicating which option is being tried
            #print(f"Attempting Option {opt_idx} for segment {segment.main_index}.{segment.secondary_index}")

            # Try the option
            spline_points = option()

            if spline_points is None or len(spline_points) < 2:
                print(f"Option {opt_idx}: Not enough points to create a spline.")
                continue

            try:
                # Polyline helper path for tangents at start and end of spline
                help_path = Polyline(sub_path_points)

                # Create the spline with tangents
                spline_path = Spline(spline_points, tangents=[help_path%0, help_path%1])

                # Get parameters for the path profile type
                parameters = self.path_profile_type_parameters.get(segment.path_profile_type.value, {})

                # Create the path profile
                profile_function = self.path_profile_type_functions.get(segment.path_profile_type, create_u_shape)
                profile = profile_function(**parameters)

                # For testing purposes, attempt to perform a sweep to see if it will succeed
                try:
                    # Debug statement indicating sweep attempt
                    #print(f"Attempting to test sweep with Option {opt_idx} for segment {segment.main_index}.{segment.secondary_index}")

                    with BuildPart():
                        with BuildLine():
                            add(spline_path)      
                        with BuildSketch(spline_path^0):
                            add(profile)
                        sweep()  

                    # If we reach this point, the sweep succeeded
                    #print(f"Option {opt_idx}: Successfully created a valid path and profile for segment {segment.main_index}.{segment.secondary_index}")

                    return spline_path, segment_curve_model

                except Exception as e:
                    # The sweep failed, try the next option
                    print(f"Option {opt_idx}: Sweep failed for segment {segment.main_index}.{segment.secondary_index} with error: {e}")
                    continue

            except Exception as e:
                # The spline creation failed, try the next option
                print(f"Option {opt_idx}: Spline creation failed for segment {segment.main_index}.{segment.secondary_index} with error: {e}")
                continue

        # Fallback option, change the curve model to POLYLINE and include all nodes
        print(f"Falling back to POLYLINE for segment {segment.main_index}.{segment.secondary_index}")
    
        # Create the path as polyline with all nodes
        path = Polyline(sub_path_points)
        segment_curve_model =  PathCurveModel.POLYLINE

        return path, segment_curve_model

def align_location_to_nearest_90_degrees(self, location):
    """
    Align the given location to the nearest 90-degree angle.
    """
    # Make a copy so we don't accidentally change the original
    aligned_location = location.copy()

    # Snap each axis' direction vector to the nearest cardinal axis
    aligned_location.x_axis.direction = Vector(
        snap_to_cardinal(aligned_location.x_axis.direction.X),
        snap_to_cardinal(aligned_location.x_axis.direction.Y),
        snap_to_cardinal(aligned_location.x_axis.direction.Z),
    )
    aligned_location.y_axis.direction = Vector(
        snap_to_cardinal(aligned_location.y_axis.direction.X),
        snap_to_cardinal(aligned_location.y_axis.direction.Y),
        snap_to_cardinal(aligned_location.y_axis.direction.Z),
    )
    aligned_location.z_axis.direction = Vector(
        snap_to_cardinal(aligned_location.z_axis.direction.X),
        snap_to_cardinal(aligned_location.z_axis.direction.Y),
        snap_to_cardinal(aligned_location.z_axis.direction.Z),
    )

    return aligned_location
    
def snap_to_cardinal(value: float) -> int:
    """
    Given a float in range [-1,1], snap it to -1, 0 or 1 
    by using +/-0.5 as the threshold.
    """
    if value > 0.5:
        return 1
    elif value < -0.5:
        return -1
    else:
        return 0    