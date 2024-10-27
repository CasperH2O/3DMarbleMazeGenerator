# shapes/path_builder.py

import random

import config
from config import *
from shapes.path_profile_type_shapes import *


class PathBuilder:
    """
    Handles the assignment of path types, grouping of nodes, and building of the final path body.
    """

    def __init__(self):
        random.seed(Config.Puzzle.SEED)
        self.waypoint_change_interval = Config.Puzzle.WAYPOINT_CHANGE_INTERVAL  # Store the waypoint change interval
        self.node_size = Config.Puzzle.NODE_SIZE  # Store node size

        self.path_profile_types = Config.Path.PATH_PROFILE_TYPES.copy()
        self.path_profile_type_parameters = Config.Path.PATH_PROFILE_TYPE_PARAMETERS
        self.path_profile_type_functions = {
            'l_shape': create_l_shape,
            'l_shape_adjusted_height': create_l_shape_adjusted_height,
            'o_shape': create_o_shape,
            'u_shape': create_u_shape,
            'u_shape_adjusted_height': create_u_shape_adjusted_height,
            'v_shape': create_v_shape,
            'rectangle_shape': create_rectangle_shape
        }
        self.path_profiles = []  # Store profiles for debugging
        self.paths = []  # Store paths corresponding to profiles

        self.path_curve_types = Config.Path.PATH_CURVE_MODEL.copy()

    def assign_path_profile_and_curve_types(self, nodes):
        """
        Assigns path profile and curve types to nodes based on specified conditions.

        Changes the path profile and curve type every nth waypoint, where n is specified in the configuration.
        """
        path_profile_type = 'u_shape'  # Start with 'u_shape'
        possible_path_profile_types = self.path_profile_types.copy()

        path_curve_type = 'polyline'
        possible_path_curve_types = self.path_curve_types.copy()

        waypoint_counter = 0  # Counter for the number of waypoints encountered

        # First few nodes are u shaped with linear path to get started easily
        for i, node in enumerate(nodes):

            # Todo, remove, done with loft?
            if i < 3:
                node.path_profile_type = 'u_shape'
                node.path_curve_type = 'polyline'
                continue

            if node.puzzle_end:
                # For the final node, adjust the path type
                node.path_profile_type = 'u_shape'
                node.path_curve_type = 'polyline'
                continue

            if node.waypoint:
                waypoint_counter += 1

                if waypoint_counter % self.waypoint_change_interval == 0:
                    # Change path profile and curve type
                    # Randomly select a type different from the current one
                    new_path_profile_types = [pt for pt in possible_path_profile_types if pt != path_profile_type]
                    new_path_curve_types = [ct for ct in possible_path_curve_types if ct != path_curve_type]
                    if new_path_profile_types:
                        path_profile_type = random.choice(new_path_profile_types)
                    if new_path_curve_types:
                        path_curve_type = random.choice(new_path_curve_types)

                node.path_profile_type = path_profile_type
                node.path_curve_type = path_curve_type
            else:
                node.path_profile_type = path_profile_type
                node.path_curve_type = path_curve_type

        return nodes

    def group_nodes_by_path_type(self, nodes):
        """
        Groups nodes into segments where the path and curve is constant.
        Since both of these change at the same time, only the path profile type is checked here.
        """
        segments = []
        current_segment = []
        current_path_type = None

        for node in nodes[2:]:
            if current_path_type is None:
                current_path_type = node.path_profile_type
                current_segment = [node]
            elif node.path_profile_type == current_path_type:
                current_segment.append(node)
            else:
                # Save the current segment
                segments.append((current_path_type, current_segment))
                # Start a new segment
                current_path_type = node.path_profile_type
                current_segment = [node]

        # Add the last segment
        if current_segment:
            segments.append((current_path_type, current_segment))

        return segments

    def prepare_profiles_and_paths(self, segments):
        """
        Creates profiles and paths for each segment and stores them along with the path_profile_type.
        """
        self.segments_data = []  # List to store profiles, paths, and path_types
        previous_end_point = None  # To store the end point of the previous segment
        last_exiting_direction = None  # To store the exiting direction of the last segment

        for idx, (path_profile_type, segment_nodes) in enumerate(segments):
            # Get the sub path points (positions of nodes in the segment)
            subpath_points = [cq.Vector(node.x, node.y, node.z) for node in segment_nodes]

            # Compute the entering direction vector for the start point
            if previous_end_point is not None:
                # Use the vector from previous end point to current start point
                entering_direction = (subpath_points[0] - previous_end_point).normalized()
            elif len(subpath_points) >= 2:
                # For the first segment, use the vector from first to second point
                entering_direction = (subpath_points[1] - subpath_points[0]).normalized()
            else:
                # Default entering direction
                entering_direction = cq.Vector(1, 0, 0)

            # Adjust the start point back along the entering direction by half the node size
            adjusted_start_point = subpath_points[0] - entering_direction * (self.node_size / 2)

            # Compute the exiting direction vector for the end point
            if idx + 1 < len(segments):
                # Next segment exists, use it to compute the exiting direction
                next_segment_nodes = segments[idx + 1][1]
                next_start_point = cq.Vector(next_segment_nodes[0].x, next_segment_nodes[0].y, next_segment_nodes[0].z)
                exiting_direction = (next_start_point - subpath_points[-1]).normalized()
            elif len(subpath_points) >= 2:
                # Use the vector from second last to last point
                exiting_direction = (subpath_points[-1] - subpath_points[-2]).normalized()
            else:
                # Default exiting direction
                exiting_direction = entering_direction

            # Adjust the end point forward along the exiting direction by half the node size
            adjusted_end_point = subpath_points[-1] + exiting_direction * (self.node_size / 2)

            # Build the adjusted subpath points
            adjusted_subpath_points = [adjusted_start_point] + subpath_points + [adjusted_end_point]

            # Create the path with adjusted points
            path = cq.Workplane("XY").polyline([p.toTuple() for p in adjusted_subpath_points])

            # Create a plane at the adjusted start point with normal along the entering direction
            plane = self.create_plane_at_point(adjusted_start_point, entering_direction)

            # Now create the work plane on this plane
            wp = cq.Workplane(plane)

            # Get parameters for the path profile type
            parameters = self.path_profile_type_parameters.get(path_profile_type, {})
            # Create the profile on this work plane
            profile_function = self.path_profile_type_functions.get(path_profile_type, create_u_shape)
            profile = profile_function(work_plane=wp, **parameters)

            # Store the profile, path, and path profile type together
            segment_data = {
                'profile': profile,
                'path': path,
                'path_profile_type': path_profile_type
            }
            self.segments_data.append(segment_data)

            # Update previous_end_point to the adjusted end point of the current segment
            previous_end_point = adjusted_end_point

            # Store the exiting_direction for use after the loop
            last_exiting_direction = exiting_direction

        #  Add closing shape (rectangle) at the end of the last segment
        if last_exiting_direction is not None and previous_end_point is not None:
            # The rectangle starts at the adjusted_end_point from the last segment
            rectangle_start_point = previous_end_point

            # Define the rectangle end point by adding n mm along the exiting_direction
            rectangle_end_point = rectangle_start_point + last_exiting_direction * 3 * config.Manufacturing.NOZZLE_DIAMETER

            # Create the path for the rectangle sweep (n mm long)
            path_points = [rectangle_start_point.toTuple(), rectangle_end_point.toTuple()]
            rectangle_path = cq.Workplane("XY").polyline(path_points)

            # Create a plane at rectangle_start_point with normal along last_exiting_direction
            plane = self.create_plane_at_point(rectangle_start_point, last_exiting_direction)

            # Create the work plane on this plane
            wp = cq.Workplane(plane)

            # Get parameters for the rectangle profile
            parameters = self.path_profile_type_parameters.get('rectangle_shape', {})
            # Create the rectangle profile using the new function
            profile_function = self.path_profile_type_functions.get('rectangle_shape', create_rectangle_shape)
            profile = profile_function(work_plane=wp, **parameters)

            # Store the profile, path, and path profile type
            segment_data = {
                'profile': profile,
                'path': rectangle_path,
                'path_profile_type': 'rectangle_shape'
            }
            self.segments_data.append(segment_data)

    def sweep_profiles_along_paths(self, indices=None):
        """
        Sweeps the stored profiles along their corresponding paths.

        Parameters:
        indices (list of int, optional): The indices of the segments to sweep.
                                         If None, all segments are processed.
        """
        path_bodies = []
        # If indices are provided, use them to select segments
        if indices is not None:
            selected_segments = [self.segments_data[i] for i in indices]
        else:
            selected_segments = self.segments_data

        for idx, segment in enumerate(selected_segments):
            profile = segment['profile']
            path = segment['path']
            path_profile_type = segment['path_profile_type']
            try:
                # Adjust the sweep parameters based on path_profile_type
                if path_profile_type == 'tube_shape' or path_profile_type == 'v_shape':
                    path_body = profile.sweep(path, transition='round')
                else:
                    path_body = profile.sweep(path, transition='right')
                # Collect the body
                path_bodies.append(path_body)
            except Exception as e:
                actual_idx = indices[idx] if indices else idx
                print(f"Error sweeping segment at index {actual_idx}: {e}")
        return path_bodies


    def build_final_path_body(self, path_bodies):
        """
        Combines all path bodies into the final path body.
        """
        final_path_body = path_bodies[0]
        for body in path_bodies[1:]:
            final_path_body = final_path_body.union(body)
        return final_path_body


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
        u_shape_params = Config.Path.PATH_PROFILE_TYPE_PARAMETERS['u_shape']

        # Create the first U-shaped profile with factor 3 applied to width
        profile = create_u_shape(work_plane=wp, factor=3, **u_shape_params)

        # Move the work plane along the adjusted direction by the adjusted distance
        profile = profile.workplane(offset=adjusted_distance)

        # Create the second U-shaped profile with factor 1 (no scaling)
        profile = create_u_shape(work_plane=profile, factor=1, **u_shape_params)

        # Loft between the two profiles
        lofted_shape = profile.loft(combine=True)

        # Optionally, store the lofted shape in an attribute
        self.lofted_shape = lofted_shape

        # Return the lofted shape
        return lofted_shape
