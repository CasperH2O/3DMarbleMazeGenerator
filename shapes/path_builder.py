# shapes/path_builder.py

from typing import List

from config import *
from shapes.path_profile_type_shapes import *
from config import PathProfileType, PathCurveModel  # Import the enums
from shapes.path_architect import PathSegment

class PathBuilder:
    """
    Handles the creation of segment shapes using profiles, sweeping along paths, and building the final path body.
    """

    def __init__(self, path_architect):
        """
        Initializes the PathBuilder with a reference to the PathArchitect.
        """
        self.path_architect = path_architect
        self.node_size = Config.Puzzle.NODE_SIZE  # Store node size

        self.path_profile_type_parameters = Config.Path.PATH_PROFILE_TYPE_PARAMETERS
        self.path_profile_type_functions = {
            PathProfileType.L_SHAPE: create_l_shape,
            PathProfileType.L_SHAPE_ADJUSTED_HEIGHT: create_l_shape_adjusted_height,
            PathProfileType.O_SHAPE: create_o_shape,
            PathProfileType.U_SHAPE: create_u_shape,
            PathProfileType.U_SHAPE_ADJUSTED_HEIGHT: create_u_shape_adjusted_height,
            PathProfileType.V_SHAPE: create_v_shape,
            PathProfileType.RECTANGLE_SHAPE: create_rectangle_shape
        }

    def prepare_profiles_and_paths(self):
        """
        Creates profiles and paths for each segment and stores them in the PathSegment objects.
        Skips segments that contain the puzzle start node.
        """
        segments = self.path_architect.segments

        for segment in segments:
            # Skip segments that contain the start node
            if any(node.puzzle_start for node in segment.nodes):
                continue

            # Get the sub path points (positions of nodes in the segment)
            sub_path_points = [cq.Vector(node.x, node.y, node.z) for node in segment.nodes]

            # Initialize the path work plane
            path_wp = cq.Workplane("XY")
            path = None

            if segment.curve_model == PathCurveModel.POLYLINE:
                if segment.curve_type == PathCurveType.DEGREE_90_SINGLE_PLANE:
                    if len(sub_path_points) >= 3:
                        first = sub_path_points[0]
                        middle = sub_path_points[len(sub_path_points) // 2]
                        last = sub_path_points[-1]
                        path = path_wp.bezier([first.toTuple(), middle.toTuple(), last.toTuple()])
                elif segment.curve_type == PathCurveType.S_CURVE:
                    if len(sub_path_points) >= 3:
                        path = path_wp.bezier([p.toTuple() for p in sub_path_points])
                else:
                    path = path_wp.polyline([p.toTuple() for p in sub_path_points])

            elif segment.curve_model == PathCurveModel.SPLINE:
                if len(sub_path_points) >= 4:
                    first_two = sub_path_points[:2]
                    last_two = sub_path_points[-2:]
                    spline_points = first_two + last_two
                    path = path_wp.spline([p.toTuple() for p in spline_points])

            if path is None:
                continue

            # Determine entering direction at the start of the segment
            if len(sub_path_points) >= 2:
                entering_direction = (sub_path_points[1] - sub_path_points[0]).normalized()
            elif len(sub_path_points) == 1 and segment.nodes[0].segment_start and segment.nodes[0].segment_end:
                entering_direction = cq.Vector(1, 0, 0)
            else:
                continue

            # Create a plane at the start point with normal along the entering direction
            plane = self.create_plane_at_point(sub_path_points[0], entering_direction)
            wp = cq.Workplane(plane)

            # Get parameters for the path profile type
            parameters = self.path_profile_type_parameters.get(segment.profile_type.value, {})

            # Create the profile on this work plane
            profile_function = self.path_profile_type_functions.get(segment.profile_type, create_u_shape)
            profile = profile_function(work_plane=wp, **parameters)

            # Store the profile and path directly in the PathSegment object
            segment.profile = profile
            segment.path = path


    def sweep_profiles_along_paths(self, indices=None):
        """
        Sweeps the stored profiles along their corresponding paths.

        Parameters:
        indices (list of int, optional): The indices of the segments to sweep.
                                        If None, all segments are processed.
        """
        segments = self.path_architect.segments
        
        # If indices are provided, use them to select segments
        if indices is not None:
            selected_segments = [segments[i] for i in indices]
        else:
            selected_segments = segments

        # Initialize the transition tracker
        next_transition = 'round'  # Starting with 'right'

        for idx, segment in enumerate(selected_segments):

            # Skip segments that contain the start node
            if any(node.puzzle_start for node in segment.nodes):
                continue

            try:
                # Determine the transition type based on path_profile_type
                if segment.profile_type in [PathProfileType.V_SHAPE, PathProfileType.O_SHAPE]:
                    transition_type = 'round'
                elif any(node.mounting for node in segment.nodes):
                    transition_type = 'right'
                else:
                    # Alternately choose between 'right' and 'round'
                    transition_type = next_transition
                    # Flip the next_transition for the subsequent else case
                    next_transition = 'round' if next_transition == 'right' else 'right'

                # Perform the sweep with the determined transition type
                path_body = segment.profile.sweep(segment.path, transition=transition_type)
                
                # Store the body in the segment
                segment.body = path_body
                
            except Exception as e:
                actual_idx = indices[idx] if indices else idx
                print(f"Error sweeping segment at index {actual_idx}: {e}")

    def build_final_path_body(self):
        # Create two separate combined bodies
        standard_body = None
        o_shape_body = None
        
        for segment in self.path_architect.segments:

            # Skip segments that contain the start node
            if any(node.puzzle_start for node in segment.nodes):
                continue

            # Check if the segment is an O-shape profile
            if segment.profile_type == PathProfileType.O_SHAPE:
                if o_shape_body is None:
                    o_shape_body = segment.body
                else:
                    o_shape_body = o_shape_body.union(segment.body)
            else:
                if standard_body is None:
                    standard_body = segment.body
                else:
                    standard_body = standard_body.union(segment.body)
        
        return {
            'standard': standard_body,
            'o_shape': o_shape_body
        }

    def create_plane_at_point(self, origin, normal_vector):
        """
        Creates a plane at the given origin, with the normal vector.
        The X direction is chosen to be perpendicular to the normal vector.
        """
        normal = cq.Vector(normal_vector)
        if normal.Length == 0:
            raise ValueError("Normal vector cannot be zero")

        # Choose an arbitrary vector not parallel to the normal vector
        z_axis = cq.Vector(0, 0, 1)
        if abs(normal.normalized().dot(z_axis)) >= 0.99:
            # normal is parallel to Z axis, use X axis
            arbitrary = cq.Vector(1, 0, 0)
        else:
            arbitrary = z_axis

        # Compute the X direction vector as cross product of arbitrary vector and normal
        x_dir = arbitrary.cross(normal).normalized()

        # Now create the plane
        plane = cq.Plane(origin=origin, xDir=x_dir, normal=normal)
        return plane

    def create_loft_between_nodes(self, total_path):
        """
        Creates a lofted shape between the first two nodes in total path using U-shaped profiles.
        The profile at the start node has a factor of 3 applied to the width, while the profile at the second node has a factor of 1.
        Only the second node's position is adjusted forward by half the node size along the exiting direction.
        Uses Config parameters for the U shape.
        """

        # Todo, rename, this is not just lof between nodes, this creates the start area body
        # Todo, probably no longer requires third node creation, otherwise, do that in PathArchitect

        if len(total_path) < 2:
            raise ValueError("Total path must contain at least two nodes.")

        # Extract first and second nodes
        first_node = total_path[0]
        second_node = total_path[1]

        # Get positions
        first_node_pos = cq.Vector(first_node.x, first_node.y, first_node.z)
        second_node_pos = cq.Vector(second_node.x, second_node.y, second_node.z)

        # Compute the direction vector from first to second node
        direction_vector = second_node_pos - first_node_pos
        distance = direction_vector.Length
        if distance == 0:
            raise ValueError("First and second node positions are the same.")

        direction = direction_vector.normalized()

        # Compute the exiting direction vector for the second node
        if len(total_path) > 2:
            # Next node exists, use it to compute the exiting direction
            third_node = total_path[2]
            third_node_pos = cq.Vector(third_node.x, third_node.y, third_node.z)
            exiting_direction = (third_node_pos - second_node_pos).normalized()
        else:
            # Use the same direction as from first to second node
            exiting_direction = direction

        # Adjust the second node position forward along the exiting direction by half the node size
        adjusted_second_node_pos = second_node_pos + exiting_direction * (self.node_size / 2)

        # Compute the adjusted direction vector and adjusted distance
        adjusted_direction_vector = adjusted_second_node_pos - first_node_pos
        adjusted_distance = adjusted_direction_vector.Length
        if adjusted_distance == 0:
            raise ValueError("Adjusted second node position is the same as first node position.")

        adjusted_direction = adjusted_direction_vector.normalized()

        # Create a plane at the first node position with the normal pointing along the adjusted direction
        plane = self.create_plane_at_point(first_node_pos, adjusted_direction)

        # Start the work plane at the first node position
        wp = cq.Workplane(plane)

        # Get the parameters for 'u_shape' from Config
        u_shape_params = Config.Path.PATH_PROFILE_TYPE_PARAMETERS[PathProfileType.U_SHAPE.value]

        # Create the first U-shaped profile with factor 3 applied to width
        profile = create_u_shape(work_plane=wp, factor=3, **u_shape_params)

        # Move the work plane along the adjusted direction by the adjusted distance
        profile = profile.workplane(offset=adjusted_distance)

        # Create the second U-shaped profile with factor 1 (no scaling)
        profile = create_u_shape(work_plane=profile, factor=1, **u_shape_params)

        # Loft between the two profiles
        lofted_shape = profile.loft(combine=True)

        # Return the lofted shape
        return lofted_shape
