# path_builder.py

import random
import cadquery as cq
from utils.config import PATH_TYPES, PATH_TYPE_PARAMETERS, SEED, NODE_SIZE
from shapes.path_shapes import (
    create_u_shape,
    create_tube_shape,
    create_u_shape_adjusted_height
)


class PathBuilder:
    """
    Handles the assignment of path types, grouping of nodes, and building of the final path body.
    """

    def __init__(self, seed=SEED, path_types=PATH_TYPES, node_size=NODE_SIZE):
        self.seed = seed
        self.path_types = path_types.copy()
        random.seed(self.seed)
        self.path_type_parameters = PATH_TYPE_PARAMETERS
        self.profile_functions = {
            'u_shape': create_u_shape,
            'tube_shape': create_tube_shape,
            'u_shape_adjusted_height': create_u_shape_adjusted_height
        }
        self.profiles = []  # Store profiles for debugging
        self.paths = []     # Store paths corresponding to profiles
        self.node_size = node_size  # Store node size

    def assign_path_types(self, nodes):
        """
        Assigns path types to nodes based on specified conditions.
        """
        path_type = 'u_shape'  # Start with 'u_shape'
        path_type_counter = 0  # Counter for nodes since last path_type change
        path_type_change_interval = 5  # Change path_type every 5 nodes
        possible_path_types = self.path_types.copy()

        # First 3 nodes are 'u_shape'
        for i in range(len(nodes)):
            node = nodes[i]
            if i < 3:
                node.path_type = 'u_shape'
                continue

            if node.end:
                # For the final node, do not change the path type
                node.path_type = path_type
                continue

            if node.waypoint:
                # When node is a waypoint, change path type randomly from that point on
                path_type_counter = 0  # Reset counter
                # Randomly select a new path_type different from the current one
                new_path_types = [pt for pt in possible_path_types if pt != path_type]
                path_type = random.choice(new_path_types)
                node.path_type = path_type
                continue

            if path_type_counter >= path_type_change_interval:
                # Check if the next 5 nodes contain a waypoint
                contains_waypoint = any(n.waypoint for n in nodes[i:i + 5])
                if not contains_waypoint:
                    # Change path_type
                    path_type_counter = 0
                    # Randomly select a new path_type different from the current one
                    new_path_types = [pt for pt in possible_path_types if pt != path_type]
                    path_type = random.choice(new_path_types)
            node.path_type = path_type
            path_type_counter += 1
        return nodes

    def group_nodes_by_path_type(self, nodes):
        """
        Groups nodes into segments where the path_type is constant.
        """
        segments = []
        current_segment = []
        current_path_type = None

        for node in nodes:
            if current_path_type is None:
                current_path_type = node.path_type
                current_segment = [node]
            elif node.path_type == current_path_type:
                current_segment.append(node)
            else:
                # Save the current segment
                segments.append((current_path_type, current_segment))
                # Start a new segment
                current_path_type = node.path_type
                current_segment = [node]

        # Add the last segment
        if current_segment:
            segments.append((current_path_type, current_segment))
        return segments

    def prepare_profiles_and_paths(self, segments):
        """
        Creates profiles and paths for each segment and stores them along with the path_type.
        """
        self.segments_data = []  # List to store profiles, paths, and path_types
        previous_end_point = None  # To store the end point of the previous segment

        for idx, (path_type, segment_nodes) in enumerate(segments):
            # Get the subpath points (positions of nodes in the segment)
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

            # Now create the Workplane on this plane
            wp = cq.Workplane(plane)

            # Get parameters for the path_type
            parameters = self.path_type_parameters.get(path_type, {})
            # Create the profile on this Workplane
            profile_function = self.profile_functions.get(path_type, create_u_shape)
            profile = profile_function(workplane=wp, **parameters)

            # Store the profile, path, and path_type together
            segment_data = {
                'profile': profile,
                'path': path,
                'path_type': path_type
            }
            self.segments_data.append(segment_data)

            # Update previous_end_point to the adjusted end point of the current segment
            previous_end_point = adjusted_end_point

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
            path_type = segment['path_type']
            try:
                # Adjust the sweep parameters based on path_type
                if path_type == 'tube_shape':
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

    def build_path(self, nodes):
        """
        High-level method to build the final path body from nodes.
        """
        # Assign path types
        nodes = self.assign_path_types(nodes)
        # Group nodes by path type
        segments = self.group_nodes_by_path_type(nodes)
        # Prepare profiles and paths
        self.prepare_profiles_and_paths(segments)
        # For debugging, profiles and paths are now available
        # Sweep profiles along paths
        path_bodies = self.sweep_profiles_along_paths()
        # Build final path body
        final_path_body = self.build_final_path_body(path_bodies)
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
        # Now compute Y direction as cross product of normal and X direction
        y_dir = normal.cross(x_dir).normalized()

        # Now create the plane
        plane = cq.Plane(origin=origin, xDir=x_dir, normal=normal)
        return plane
