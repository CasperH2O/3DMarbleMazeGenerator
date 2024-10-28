# shapes/path_builder.py

from config import *
from shapes.path_profile_type_shapes import *
from config import PathProfileType, PathCurveModel  # Import the enums

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
        self.segments_data = []  # Store profiles, paths, and path_types
        self.path_profiles = []  # For debugging
        self.paths = []  # For debugging

    def prepare_profiles_and_paths(self):
        """
        Creates profiles and paths for each segment and stores them along with the path_profile_type.
        Skips segments that contain the puzzle start node.
        """
        segments = self.path_architect.segments

        for idx, segment in enumerate(segments):
            # Skip segments that contain a node with .puzzle_start == True
            if any(node.puzzle_start for node in segment.nodes):
                continue

            # Get the sub_path points (positions of nodes in the segment)
            sub_path_points = [cq.Vector(node.x, node.y, node.z) for node in segment.nodes]

            # Create the path using the nodes as provided
            # Todo, handle arcs and bezier here for curves
            path = cq.Workplane("XY").polyline([p.toTuple() for p in sub_path_points])

            # Determine entering direction at the start of the segment
            if len(sub_path_points) >= 2:
                entering_direction = (sub_path_points[1] - sub_path_points[0]).normalized()
            elif len(sub_path_points) == 1 and segment.nodes[0].segment_start and segment.nodes[0].segment_end:
                # For segments with a single node (start and end), use default direction
                entering_direction = cq.Vector(1, 0, 0)
            else:
                # Cannot determine direction, skip this segment
                print(f"Segment {idx} has insufficient nodes to determine direction.")
                continue

            # Create a plane at the start point with normal along the entering direction
            plane = self.create_plane_at_point(sub_path_points[0], entering_direction)

            # Now create the work plane on this plane
            wp = cq.Workplane(plane)

            # Get parameters for the path profile type
            path_profile_type = segment.path_profile_type
            parameters = self.path_profile_type_parameters.get(path_profile_type.value, {})
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

        for idx, segment_data in enumerate(selected_segments):
            profile = segment_data['profile']
            path = segment_data['path']
            path_profile_type = segment_data['path_profile_type']
            try:
                # Adjust the sweep parameters based on path_profile_type
                if path_profile_type in [PathProfileType.V_SHAPE, PathProfileType.O_SHAPE]:
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
        if not path_bodies:
            raise ValueError("No path bodies to combine.")
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
