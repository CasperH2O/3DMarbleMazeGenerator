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

        # Create the segments
        self.create_segments()

        # Make holes in O-shaped path segments
        self.cut_holes_in_o_shape_path_profile_segments()

        self.final_path_bodies = self.build_final_path_body()

    def create_segments(self):
        """
        Creates profile(s), path and body for each path segment
        """
        segments = self.path_architect.segments
        previous_segment = None

        for segment in segments:
            # Skip segments that contain the start node
            if any(node.puzzle_start for node in segment.nodes):
                continue

            # Polyline and spline segments are handled differently
            if segment.curve_model == PathCurveModel.POLYLINE:
                segment = self.create_polyline_segment(previous_segment, segment)
            elif segment.curve_model == PathCurveModel.SPLINE:
                segment = self.create_spline_segment(previous_segment, segment)
            else:
                print(f"Unsupported curve model: {segment.curve_model}")

            previous_segment = segment

    def create_polyline_segment(self, previous_segment, segment):
        """
        Creates a polyline segment.
        """
        # Get the sub path points (positions of nodes in the segment)
        sub_path_points = [Vector(node.x, node.y, node.z) for node in segment.nodes]
        
        # Path

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

        # Profile
        path_line_angle = -90
        profile_angle = 0      

        # Determine path line angle difference between the current segment and the previous segment for rotation
        if previous_segment is not None:
            loc1 = previous_segment.path^1
            loc2 = segment.path^0
            path_angle_delta = loc2.y_axis.direction.get_signed_angle(loc1.y_axis.direction, loc2.z_axis.direction)
            path_line_angle += 90 * round(path_angle_delta / 90.0)

        # Determine the angle of the profile based on the previous segment
        if previous_segment is not None:
            profile_angle = self.determine_path_profile_angle(previous_segment, segment, path_line_angle)

        # Get parameters for the path profile type
        path_parameters = self.path_profile_type_parameters.get(segment.path_profile_type.value, {})

        # Store path profile sketch
        path_profile_function = self.path_profile_type_functions.get(segment.path_profile_type, create_u_shape)
        segment.path_profile = path_profile_function(**path_parameters, rotation_angle=path_line_angle + profile_angle)

        # Sweep for the main path body
        segment.path_body = sweep_single_profile(segment, segment.path_profile, segment.transition_type, "Path")

        # Create the accent profile if the segment has an accent profile type
        if segment.accent_profile_type != None:

            # Get parameters for the accent profile type
            accent_path_parameters = self.path_profile_type_parameters.get(segment.accent_profile_type.value, {})

            # Store accent color profile sketch
            accent_profile_function = self.path_profile_type_functions.get(segment.accent_profile_type, create_u_shape)
            segment.accent_profile = accent_profile_function(**accent_path_parameters, rotation_angle=path_line_angle + profile_angle)

            # Sweep for the accent body
            segment.accent_body = sweep_single_profile(segment, segment.accent_profile, segment.transition_type, "Accent")

        # Create the support profile if the segment has a support profile type
        if segment.support_profile_type != None:

            # Get parameters for the support profile type
            support_path_parameters = self.path_profile_type_parameters.get(segment.support_profile_type.value, {})

            # Store support profile sketch
            support_profile_function = self.path_profile_type_functions.get(segment.support_profile_type, create_u_shape)
            segment.support_profile = support_profile_function(**support_path_parameters, rotation_angle=path_line_angle + profile_angle)

            # Sweep for the support body
            segment.support_body = sweep_single_profile(segment, segment.support_profile, segment.transition_type, "Support")

        return segment


    def create_spline_segment(self, previous_segment, segment):
        """
        Creates a spline segment. 

        Tries different spline point combinations to create a valid path and profile
        for a SPLINE curve model segment. Falls back to a polyline path if no valid path can be created.
        """
        # Get the sub path points (positions of nodes in the segment)
        sub_path_points = [Vector(node.x, node.y, node.z) for node in segment.nodes]

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

            # Polyline helper path for tangents at start and end of spline
            help_path = Polyline(sub_path_points)

            # Create the spline with tangents
            segment.path = Spline(spline_points, tangents=[help_path%0, help_path%1])

            # Debug statement indicating sweep attempt
            print(f"Attempting to test sweep with Option {opt_idx} for segment {segment.main_index}.{segment.secondary_index}")

            path_line_angle = -90

            # Determine path line angle difference between the current segment and the previous segment for rotation
            if previous_segment is not None:
                loc1 = previous_segment.path^1
                loc2 = segment.path^0
                path_line_angle += loc2.y_axis.direction.get_signed_angle(loc1.y_axis.direction, loc2.z_axis.direction)

            # Determine the angle of the profile based on the previous segment
            if previous_segment is not None:
                profile_angle = self.determine_path_profile_angle(previous_segment, segment, path_line_angle)

            # Determine spline path end angle for additional end of path profile rotation
            loc1 = help_path^1
            loc2 = segment.path^1
            angle_profile_end_of_path = loc2.y_axis.direction.get_signed_angle(loc1.y_axis.direction, loc2.z_axis.direction)
            angle_profile_end_of_path = angle_profile_end_of_path % 90

            # Get parameters for the path profile type
            path_parameters = self.path_profile_type_parameters.get(segment.path_profile_type.value, {})

            # Store path profile sketch
            path_profile_function = self.path_profile_type_functions.get(segment.path_profile_type, create_u_shape)
            segment.path_profile = path_profile_function(**path_parameters, rotation_angle=path_line_angle + profile_angle)
            path_profile_end = path_profile_function(**path_parameters, rotation_angle=profile_angle + angle_profile_end_of_path)

            try:
                print(f"Sweeping for segment {segment.main_index}.{segment.secondary_index}")

                # Sweep for the main path body
                with BuildPart() as segment.path_body:
                    with BuildLine() as l:
                        add(segment.path)      
                    with BuildSketch(segment.path^0) as s1:
                        add(segment.path_profile)
                    with BuildSketch(segment.path^1) as s2:
                        add(path_profile_end)    
                    sweep([s1.sketch,s2.sketch],l.line,multisection=True)

                # Check if bodies are valid
                if not segment.path_body.part.is_valid():
                    print(f"Segment {segment.main_index}.{segment.secondary_index} has an invalid path body")

                # Create the accent profile if the segment has an accent profile type
                if segment.accent_profile_type != None:

                    # Get parameters for the accent profile type
                    accent_path_parameters = self.path_profile_type_parameters.get(segment.accent_profile_type.value, {})

                    # Store accent color profile sketch
                    accent_profile_function = self.path_profile_type_functions.get(segment.accent_profile_type, create_u_shape)
                    segment.accent_profile = accent_profile_function(**accent_path_parameters, rotation_angle=path_line_angle + profile_angle)
                    path_profile_end = accent_profile_function(**accent_path_parameters, rotation_angle=profile_angle + angle_profile_end_of_path)

                    # Sweep for the accent body
                    with BuildPart() as segment.accent_body:
                        with BuildLine() as l:
                            add(segment.path)      
                        with BuildSketch(segment.path^0) as s1:
                            add(segment.accent_profile)
                        with BuildSketch(segment.path^1) as s2:
                            add(path_profile_end)                        
                        sweep([s1.sketch,s2.sketch],l.line,multisection=True)   

                # Create the support profile if the segment has a support profile type
                if segment.support_profile_type != None:

                    # Get parameters for the support profile type
                    support_path_parameters = self.path_profile_type_parameters.get(segment.support_profile_type.value, {})

                    # Store support profile sketch
                    support_profile_function = self.path_profile_type_functions.get(segment.support_profile_type, create_u_shape)
                    segment.support_profile = support_profile_function(**support_path_parameters, rotation_angle=path_line_angle + profile_angle)
                    path_profile_end = support_profile_function(**support_path_parameters, rotation_angle=profile_angle + angle_profile_end_of_path)

                    # Sweep for the support body
                    with BuildPart() as segment.support_body:
                        with BuildLine() as l:
                            add(segment.path)
                        with BuildSketch(segment.path^0) as s1:
                            add(segment.support_profile)
                        with BuildSketch(segment.path^1) as s2:
                            add(path_profile_end)                        
                        sweep([s1.sketch,s2.sketch],l.line,multisection=True)

                # If we reach this point, the sweep succeeded, return segment
                #print(f"Option {opt_idx}: Successfully created a valid path and profile for segment {segment.main_index}.{segment.secondary_index}")

                return segment


            except Exception as e:
                # The spline creation failed, try the next option
                print(f"Option {opt_idx}: Spline creation failed for segment {segment.main_index}.{segment.secondary_index} with error: {e}")
                continue

        # Fallback option, change the curve model to POLYLINE and include all nodes
        print(f"Falling back to POLYLINE for segment {segment.main_index}.{segment.secondary_index}")
    
        # Create the path as polyline with all nodes and set curve model to POLYLINE
        segment.path = Polyline(sub_path_points)
        segment.curve_model =  PathCurveModel.POLYLINE

        # Create the segment as polyline instead of a spline
        segment = self.create_polyline_segment(previous_segment, segment)

        return segment


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

        
    def determine_path_profile_angle(self, previous_segment, current_segment, start_angle: float) -> float:
        """
        Determine the relative rotation angle between the profile of the `previous_segment`
        and the start of the `current_segment`.

        This function takes the swept path shape from `previous_segment` It then attempts 
        to match that profile with a sketch placed at the start of the `current_segment.path`. 
        The function returns the rotation offset (0 <= angle < 360) at which the profile 
        matches, or 0 if no match is found.

        :param previous_segment: The segment whose swept profile is being checked
        :param current_segment: The segment at whose start we want to match the profile
        :param start_angle: Base rotation offset to apply when creating the profile
        :return: The additional rotation angle (in degrees) at which the profile matches;
                returns 0 if no matching angle is found
        """

        # Obtain faces from the swept shape
        faces = previous_segment.path_body.part.faces()

        # Get parameters for the path profile type
        path_parameters = self.path_profile_type_parameters.get(previous_segment.path_profile_type.value, {})
        # Apply the path profile function
        path_profile_function = self.path_profile_type_functions.get(previous_segment.path_profile_type, create_u_shape)

        # Create previous segment profile type at the start of the current segment path with 90 degree angle increments
        for angle in range(0, 360, 90):

            # Create path profile sketch at the combined angle
            previous_segment_path_profile = path_profile_function(**path_parameters, rotation_angle=angle + start_angle)

            # Create sketch at start of the second path at respective angle
            with BuildSketch(current_segment.path^0) as current_segment_path_profile:
                add(previous_segment_path_profile)

            # Compare the newly-created sketch with the faces of the sweep
            for face in faces:
                 # Filter out faces that have a (nearly) identical area
                if are_float_values_close(face.area, current_segment_path_profile.sketch.area):
                    # Check equality of face shape geometry
                    if are_equal_faces(face, current_segment_path_profile.sketch):
                        return angle

        # If no mathcing angle found, notify and return 0 degrees
        print(f"No matching profile type angle found for segment {previous_segment.main_index}.{previous_segment.secondary_index} to segment {current_segment.main_index}.{current_segment.secondary_index}")
        
        return 0
    

def are_float_values_close(val1: float, val2: float, tolerance: float = 0.01) -> bool:
    """
    Checks if two float values are within a given percentage (default 1%) of one another.
    
    :param val1: First float value
    :param val2: Second float value
    :param tolerance: A fraction representing how close they should be 
                      (e.g., 0.01 = within 1%)
    :return: True if the values differ by at most 'tolerance' fraction of their average,
             otherwise False
    """
    
    # If both values are exactly 0, consider them close.
    if val1 == 0 and val2 == 0:
        return True
    
    # Calculate the absolute difference
    diff = abs(val1 - val2)
    
    # Calculate the reference scale, using the average of the two values.
    # Guard for the case if their average is 0 (which can happen if, say, one is 0 and the other is very small).
    avg = (abs(val1) + abs(val2)) / 2.0
    if avg == 0:
        # if the average is zero but one or both values are non-zero, they are not within 1%.
        return diff == 0
    
    # Compare difference to the tolerance fraction of the average
    return (diff / avg) <= tolerance


def are_equal_faces(face1, face2, tolerance=0.01):
    """
    Check if two faces have 'approximately' the same area within a given tolerance (default 1%).

    We measure the total 'difference area' (areas in face1 not in face2 plus 
    areas in face2 not in face1) and compare it against the average area.
    """
    # Calculate the 'difference area' - area that doesn't overlap
    difference_area = (face1 - face2).area + (face2 - face1).area
    
    # Use the average of the two face areas as the reference
    avg_area = (face1.area + face2.area) / 2
    
    # Guard against division by zero if either face has zero area
    if avg_area == 0:
        return difference_area == 0

    # Compare the difference area to a tolerance fraction of the average area
    return (difference_area / avg_area) <= tolerance

def sweep_single_profile(segment, profile, transition_type, sweep_label="Path"):
    """
    Helper for sweeping a single profile (main path, accent, or support).
    """
    try:
        # Create part out of path profile and path
        with BuildPart() as sweep_result:
            with BuildLine() as path_line:
                add(segment.path)
            # Create the path profile sketch on the workplane
            with BuildSketch(path_line.line^0) as sketch_path_profile:
                add(profile)
            sweep(transition=transition_type)

        # Debugging / visualization
        #show_object(path_line, name=f"{segment.main_index}.{segment.secondary_index} - {sweep_label} Path")
        #show_object(sketch_path_profile.sketch, name=f"{segment.main_index}.{segment.secondary_index} - {sweep_label} Profile")
        #show_object(sweep_result, name=f"{segment.main_index}.{segment.secondary_index} - {sweep_label} Body")

        return sweep_result

    except Exception as e:
        print(
            f"Error sweeping {sweep_label.lower()} for segment "
            f"{segment.main_index}.{segment.secondary_index}: {e}"
        )
        return None