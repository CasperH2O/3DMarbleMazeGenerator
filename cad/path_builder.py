import math
import random
from enum import Enum
from typing import Any, Dict, List, Optional

from build123d import (
    Bezier,
    BuildLine,
    BuildPart,
    BuildSketch,
    Circle,
    Face,
    FrameMethod,
    Line,
    Part,
    Plane,
    Polyline,
    RadiusArc,
    Sketch,
    Spline,
    Transition,
    Vector,
    Wire,
    add,
    extrude,
    loft,
    sweep,
)

from cad.path_profile_type_shapes import (
    PROFILE_TYPE_FUNCTIONS,
    PathProfileType,
    create_u_shape,
    create_u_shape_path_color,
)
from config import Config, PathCurveModel, PathCurveType
from puzzle.puzzle import Node, Puzzle

from .path_architect import PathArchitect
from .path_segment import PathSegment, _node_to_vector, is_same_location


class PathTypes(Enum):
    """
    Enumeration representing the different types of path segments
    """

    STANDARD = "Standard Path"
    SUPPORT = "Support Path"
    ACCENT_COLOR = "Accent Color Path"


class PathBuilder:
    """
    Handles the creation of segment shapes using profiles, sweeping along paths, and building the final path body.
    """

    def __init__(self, puzzle: Puzzle):
        """
        Initializes the PathBuilder with a reference to the PathArchitect.
        """
        self.path_architect: PathArchitect = puzzle.path_architect
        self.total_path = puzzle.total_path
        self.node_size = Config.Puzzle.NODE_SIZE  # Store node size
        self.path_profile_type_parameters = Config.Path.PATH_PROFILE_TYPE_PARAMETERS
        self.seed = Config.Puzzle.SEED
        random.seed(self.seed)  # Set the random seed for reproducibility

        # Create the start area based on the first segment
        self.start_area = self.create_start_area_funnel(self.path_architect.segments[0])

        # Create the paths based provided segments from path architect
        self.build_segments()

        # Make holes in O-shaped path segments
        self.cut_holes_in_o_shape_path_profile_segments()

        # Combine final path bodies, depending on amount of divides
        self.final_path_bodies = self.combine_final_path_bodies()

    def build_segments(self) -> None:
        """
        Create profile(s), path and body for each path segment.
        """
        # Get segments from path architect
        segments: List[PathSegment] = self.path_architect.segments

        # Process each segment, define it's path
        self._define_segment_paths(segments)

        # Group sub segments of compound segments and combine their paths
        combine_segments: List[PathSegment] = self._combine_compound_segments_for_path(
            segments
        )

        # Sweep segments
        swept_segments: List[PathSegment] = self.sweep_segments(combine_segments)

        # Store segments in path architect again
        self.path_architect.segments = swept_segments

    def sweep_segments(self, segments: List[PathSegment]) -> List[PathSegment]:
        # Sweep the segments, with information of which ever segment comes previous
        previous_segment: Optional[PathSegment] = None

        # Iterate with an index so we can look ahead one element
        for idx, segment in enumerate(segments):
            # Get the following segment if it exists
            next_segment: Optional[PathSegment] = (
                segments[idx + 1] if idx + 1 < len(segments) else None
            )

            """
            print(
                f"Segment {segment.main_index}.{segment.secondary_index} of curve mode {segment.curve_model}"
            )
            """

            if segment.curve_model in (PathCurveModel.COMPOUND, PathCurveModel.SINGLE):
                # Sweep the segment.
                segment = self.sweep_standard_segment(
                    segment=segment, previous_segment=previous_segment
                )

            # Create a spline segment, trying different path combinations.
            # Requires the paths of the segment before and after it for proper tangents
            elif segment.curve_model == PathCurveModel.SPLINE:
                segment = self.create_spline_segment(
                    segment=segment,
                    previous_segment=previous_segment,
                    next_segment=next_segment,
                )
            else:
                print(f"Unsupported curve model: {segment.curve_model}")

            # Store the processed segment back (in case it was modified)
            segments[idx] = segment
            previous_segment = segment

        return segments

    def _define_segment_paths(self, segments: List[PathSegment]) -> None:
        """
        Process each (sub) segment to define its path.
        """
        for segment in segments:
            if segment.curve_model != PathCurveModel.SPLINE:
                segment = self.define_standard_segment_path(segment)

    def _combine_compound_segments_for_path(
        self, segments: List[PathSegment]
    ) -> List[PathSegment]:
        """
        Combine all the individual paths of sub segments of a
        single main index compound segment into a single path
        """
        compound_groups: Dict[int, List[PathSegment]] = {}
        non_compound_segments: List[PathSegment] = []

        # Separate compound segments from non-compound segments.
        for segment in segments:
            if segment.curve_model == PathCurveModel.COMPOUND and not any(
                node.puzzle_start for node in segment.nodes
            ):
                compound_groups.setdefault(segment.main_index, []).append(segment)
            else:
                non_compound_segments.append(segment)

        combined_segments: List[PathSegment] = []
        for main_index, seg_list in compound_groups.items():
            if len(seg_list) == 1:
                # No combination needed if there's only one segment in this group.
                combined_segments.append(seg_list[0])
            else:
                # Sort segments by secondary_index to maintain correct order.
                seg_list_sorted: List[PathSegment] = sorted(
                    seg_list, key=lambda s: s.secondary_index
                )
                # Collect edges from each segment's already-created path.
                all_edges: List[Any] = self._collect_edges(seg_list_sorted)
                # Combine the collected edges into one continuous Wire.
                combined_wire = Wire(all_edges)
                # Combine the nodes of the segments.
                combined_nodes = self._combine_nodes(seg_list_sorted)
                # Create a new compound segment using the combined nodes and Wire.
                new_segment = PathSegment(
                    combined_nodes, main_index=main_index, secondary_index=0
                )
                new_segment.curve_model = PathCurveModel.COMPOUND
                new_segment.path = combined_wire
                # Inherit additional attributes (like profile type and transition) from the first segment.
                new_segment.copy_attributes_from(seg_list_sorted[0])
                combined_segments.append(new_segment)

        segments = non_compound_segments + combined_segments

        # Sort segments by main_index and secondary_index to ensure correct order.
        segments.sort(key=lambda s: (s.main_index, s.secondary_index))

        # Return both non-compound and combined compound segments (sorted)
        return segments

    def _collect_edges(self, seg_list: List[PathSegment]) -> List[Any]:
        """
        Helper method to collect edges from the path of each segment.

        If the path is a Wire, extract its edges; otherwise, assume it's a single Edge.
        """
        all_edges: List[Any] = []
        for seg in seg_list:
            if seg.path:
                if hasattr(seg.path, "edges"):
                    all_edges.extend(seg.path.edges())
                else:
                    all_edges.append(seg.path)
        return all_edges

    def _combine_nodes(self, seg_list: List[PathSegment]) -> List[Node]:
        """
        Helper method to combine nodes from a sorted list of segments.

        Starts with the nodes of the first segment, then for each subsequent segment,
        skips its first node if it duplicates the previous segment's end node,
        ensuring continuity in the combined node list.
        """
        combined_nodes: List[Node] = seg_list[0].nodes.copy()
        for seg in seg_list[1:]:
            # Use helper _node_to_vector to compare positions of nodes.
            if seg.nodes and is_same_location(
                _node_to_vector(seg.nodes[0]), _node_to_vector(combined_nodes[-1])
            ):
                combined_nodes.extend(seg.nodes[1:])
            else:
                combined_nodes.extend(seg.nodes)
        return combined_nodes

    def define_standard_segment_path(self, segment: PathSegment) -> PathSegment:
        """
        Creates a standard segment's path
        """

        # Get the sub path points (positions of nodes in the segment)
        sub_path_points = [Vector(node.x, node.y, node.z) for node in segment.nodes]

        # Create the path wire based on the curve type
        if segment.curve_type == PathCurveType.CURVE_90_DEGREE_SINGLE_PLANE:
            if len(sub_path_points) >= 3:
                first = sub_path_points[0]
                middle = sub_path_points[len(sub_path_points) // 2]
                last = sub_path_points[-1]
                segment.path = Bezier(
                    [
                        (first.X, first.Y, first.Z),
                        (middle.X, middle.Y, middle.Z),
                        (last.X, last.Y, last.Z),
                    ]
                )
        elif segment.curve_type == PathCurveType.S_CURVE:
            if len(sub_path_points) >= 3:
                segment.path = Bezier([(p.X, p.Y, p.Z) for p in sub_path_points])
        elif segment.curve_type == PathCurveType.ARC:
            if len(sub_path_points) >= 2:
                first = sub_path_points[0]
                last = sub_path_points[-1]
                # Calculate the Euclidean distance between first node to 0,0,0 center of puzzle
                distance_to_center = math.sqrt(first.X**2 + first.Y**2 + first.Z**2)
                segment.path = RadiusArc(
                    start_point=first, end_point=last, radius=distance_to_center
                )
                # Check if the arc is bent in the right direction, if not invert and recreate
                if not is_close_to_origin(segment.path.arc_center):
                    distance_to_center *= -1
                    segment.path = RadiusArc(
                        start_point=first, end_point=last, radius=distance_to_center
                    )
        else:
            segment.path = Polyline([(p.X, p.Y, p.Z) for p in sub_path_points])

        return segment

    def sweep_standard_segment(
        self, segment: PathSegment, previous_segment: PathSegment
    ) -> PathSegment:
        """
        Sweeps the segment based on its defined path and profile.
        Uses the previous segment for it's start orienation
        Creates the main path body, accent body, and support body.
        """

        # Profile
        path_line_angle = 0
        profile_angle = -90

        """
        print(
            f"Sweep Segment {segment.main_index}.{segment.secondary_index} "
            f"of curve mode {segment.curve_model}"
        )
        """

        # Determine path line angle difference between the current segment and the previous segment for rotation
        if previous_segment is not None:
            loc1 = previous_segment.path ^ 1
            loc2 = segment.path ^ 0
            path_angle_delta = loc2.y_axis.direction.get_signed_angle(
                loc1.y_axis.direction, loc2.z_axis.direction
            )
            path_line_angle += 90 * round(path_angle_delta / 90.0)

        # Determine the angle of the profile based on the previous segment
        if previous_segment is not None:
            profile_angle = self.determine_path_profile_angle(
                previous_segment, segment, path_line_angle
            )

        # Get parameters for the path profile type
        path_parameters = self.path_profile_type_parameters.get(
            segment.path_profile_type.value, {}
        )

        # Store path profile sketch based on path profile registry
        path_profile_function = PROFILE_TYPE_FUNCTIONS.get(
            segment.path_profile_type, create_u_shape
        )
        segment.path_profile = path_profile_function(
            **path_parameters, rotation_angle=path_line_angle + profile_angle
        )

        # Sweep for the main path body
        segment.path_body = sweep_single_profile(
            segment, segment.path_profile, segment.transition_type, "Path"
        )

        # Create the accent profile if the segment has an accent profile type
        if segment.accent_profile_type is not None:
            # Get parameters for the accent profile type
            accent_path_parameters = self.path_profile_type_parameters.get(
                segment.accent_profile_type.value, {}
            )
            # Store accent color profile sketch based on path profile registry
            accent_profile_function = PROFILE_TYPE_FUNCTIONS.get(
                segment.accent_profile_type, create_u_shape
            )
            segment.accent_profile = accent_profile_function(
                **accent_path_parameters, rotation_angle=path_line_angle + profile_angle
            )
            # Sweep for the accent body
            segment.accent_body = sweep_single_profile(
                segment, segment.accent_profile, segment.transition_type, "Accent"
            )

        # Create the support profile if the segment has a support profile type
        if segment.support_profile_type is not None:
            # Get parameters for the support profile type
            support_path_parameters = self.path_profile_type_parameters.get(
                segment.support_profile_type.value, {}
            )
            # Store support profile sketch based on path profile registry
            support_profile_function = PROFILE_TYPE_FUNCTIONS.get(
                segment.support_profile_type, create_u_shape
            )
            segment.support_profile = support_profile_function(
                **support_path_parameters,
                rotation_angle=path_line_angle + profile_angle,
            )
            # Sweep for the support body
            segment.support_body = sweep_single_profile(
                segment, segment.support_profile, segment.transition_type, "Support"
            )

        return segment

    def create_spline_segment(
        self,
        segment: PathSegment,
        previous_segment: PathSegment,
        next_segment: PathSegment,
    ):
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
            Option 2: Use the first node, every third node in between, and the last node.
            This reduces the number of intermediate points to simplify the spline.
            """
            if len(sub_path_points) >= 2:
                return (
                    [sub_path_points[0]]
                    + sub_path_points[1:-2:3]
                    + [sub_path_points[-1]]
                )
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
            # print(f"Attempting Option {opt_idx} for segment {segment.main_index}.{segment.secondary_index}")

            # Try the option
            spline_points = option()

            if spline_points is None or len(spline_points) < 2:
                print(f"Option {opt_idx}: Not enough points to create a spline.")
                continue

            # Polyline helper path for tangents at start and end of spline
            help_path = Polyline(sub_path_points)

            # previous_segment
            # next_segment

            # Create the spline with tangents
            segment.path = Spline(
                spline_points,
                tangents=[previous_segment.path % 1, next_segment.path % 0],
            )

            # Debug statement indicating sweep attempt
            print(
                f"Attempting to test sweep with Option {opt_idx} for segment {segment.main_index}.{segment.secondary_index}"
            )

            # Start with -90 angle to orientate the profile sketch "right way up"
            angle_path_line_previous = -90

            # Determine the rotation angle between the path line of the current segment and the previous segment
            loc1 = previous_segment.path ^ 1
            loc2 = segment.path.location_at(0, frame_method=FrameMethod.CORRECTED)
            angle_path_line_previous += loc2.y_axis.direction.get_signed_angle(
                loc1.y_axis.direction, loc2.z_axis.direction
            )

            # Determine the angle where profile matches  the previous segment
            angle_profile_rotation_match = self.determine_path_profile_angle(
                previous_segment, segment, angle_path_line_previous
            )

            # Determine spline path end angle for additional end of path profile rotation due to help path tangent
            loc1 = help_path ^ 1
            loc2 = segment.path.location_at(1, frame_method=FrameMethod.CORRECTED)
            angle_profile_end_of_path = loc2.y_axis.direction.get_signed_angle(
                loc1.y_axis.direction, loc2.z_axis.direction
            )

            # Compute base angle (the sum of the previous segment angle and the profile match)
            base_angle = angle_path_line_previous + angle_profile_rotation_match

            # Compute the difference between the desired end-of-path angle and the base angle,
            # normalized to the range (-180, 180)
            angle_diff = normalize_angle(angle_profile_end_of_path - base_angle)

            # Choose twist_offset based on the sign of angle_diff.
            # (This rule gives:
            #   - twist_offset = 0 if the desired end-of-path aligns with the base angle,
            #   - twist_offset = -90 if the difference is positive,
            #   - twist_offset =  90 if the difference is negative.)
            if abs(angle_diff) < 1e-6:
                twist_offset = 0
            elif angle_diff > 0:
                twist_offset = -90
            else:
                twist_offset = 90

            # Compute the adjustment.
            # The final sketch angle corrected by the twist offset to match the end-of-path angle.
            # That is, if twist_offset is -90, we require:
            #       final_angle2 + 90 == angle_profile_end_of_path,
            # and if twist_offset is 90:
            #       final_angle2 - 90 == angle_profile_end_of_path.
            if twist_offset == -90:
                computed_adjustment = (angle_profile_end_of_path - 90) - base_angle
            elif twist_offset == 90:
                computed_adjustment = (angle_profile_end_of_path + 90) - base_angle
            else:  # twist_offset == 0
                computed_adjustment = angle_profile_end_of_path - base_angle

            # Final sketch angles:
            angle_sketch_1_final = base_angle
            angle_sketch_2_final = base_angle + computed_adjustment

            # Get parameters for the path profile type
            path_parameters = self.path_profile_type_parameters.get(
                segment.path_profile_type.value, {}
            )

            # Store path profile sketch based on path profile registry
            path_profile_function = PROFILE_TYPE_FUNCTIONS.get(
                segment.path_profile_type, create_u_shape
            )
            segment.path_profile = path_profile_function(
                **path_parameters, rotation_angle=angle_sketch_1_final
            )
            path_profile_end = path_profile_function(
                **path_parameters, rotation_angle=angle_sketch_2_final
            )

            try:
                # print(f"Sweeping for segment {segment.main_index}.{segment.secondary_index}")

                # Sweep for the main path body
                with BuildPart() as segment.path_body:
                    with BuildLine() as segment_path_line:
                        add(segment.path)
                    with BuildSketch(
                        segment.path.location_at(0, frame_method=FrameMethod.CORRECTED)
                    ) as s1:
                        add(segment.path_profile)
                    with BuildSketch(
                        segment.path.location_at(1, frame_method=FrameMethod.CORRECTED)
                    ) as s2:
                        add(path_profile_end)
                    sweep(
                        sections=[s1.sketch, s2.sketch],
                        path=segment_path_line.line,
                        multisection=True,
                    )

                # Check if bodies are valid
                if not segment.path_body.part.is_valid():
                    print(
                        f"Check segment {segment.main_index}.{segment.secondary_index} has an invalid path body?"
                    )

                # Create the accent profile if the segment has an accent profile type
                if segment.accent_profile_type is not None:
                    # Get parameters for the accent profile type
                    accent_path_parameters = self.path_profile_type_parameters.get(
                        segment.accent_profile_type.value, {}
                    )

                    # Store accent color profile sketch based on path profile registry
                    accent_profile_function = PROFILE_TYPE_FUNCTIONS.get(
                        segment.accent_profile_type, create_u_shape
                    )
                    segment.accent_profile = accent_profile_function(
                        **accent_path_parameters, rotation_angle=angle_sketch_1_final
                    )
                    path_profile_end = accent_profile_function(
                        **accent_path_parameters, rotation_angle=angle_sketch_2_final
                    )

                    # Sweep for the accent body
                    with BuildPart() as segment.accent_body:
                        with BuildLine() as segment_path_line:
                            add(segment.path)
                        with BuildSketch(
                            segment.path.location_at(
                                0, frame_method=FrameMethod.CORRECTED
                            )
                        ) as s1:
                            add(segment.accent_profile)
                        with BuildSketch(
                            segment.path.location_at(
                                1, frame_method=FrameMethod.CORRECTED
                            )
                        ) as s2:
                            add(path_profile_end)
                        sweep(
                            [s1.sketch, s2.sketch],
                            segment_path_line.line,
                            multisection=True,
                        )

                # Create the support profile if the segment has a support profile type
                if segment.support_profile_type is not None:
                    # Get parameters for the support profile type
                    support_path_parameters = self.path_profile_type_parameters.get(
                        segment.support_profile_type.value, {}
                    )

                    # Store support profile sketch based on path profile registry
                    support_profile_function = PROFILE_TYPE_FUNCTIONS.get(
                        segment.support_profile_type, create_u_shape
                    )
                    segment.support_profile = support_profile_function(
                        **support_path_parameters, rotation_angle=angle_sketch_1_final
                    )
                    path_profile_end = support_profile_function(
                        **support_path_parameters, rotation_angle=angle_sketch_2_final
                    )

                    # Sweep for the support body
                    with BuildPart() as segment.support_body:
                        with BuildLine() as segment_path_line:
                            add(segment.path)
                        with BuildSketch(
                            segment.path.location_at(
                                0, frame_method=FrameMethod.CORRECTED
                            )
                        ) as s1:
                            add(segment.support_profile)
                        with BuildSketch(
                            segment.path.location_at(
                                1, frame_method=FrameMethod.CORRECTED
                            )
                        ) as s2:
                            add(path_profile_end)
                        sweep(
                            [s1.sketch, s2.sketch],
                            segment_path_line.line,
                            multisection=True,
                        )

                # If we reach this point, the sweep succeeded, return segment

                """        
                show_object(l, f"Spline Line - segment {segment.main_index}.{segment.secondary_index}")
                show_object(help_path, f"Help path - segment {segment.main_index}.{segment.secondary_index}")
                path_increments = [0.1, 0.5, 0.9]
                for val in path_increments:
                    show_object(l.line ^ val, name=f"Spline Line - {val:.2f} - segment {segment.main_index}.{segment.secondary_index}")  
                    show_object(help_path ^ val, name=f"Help path - segment {segment.main_index}.{segment.secondary_index}")      
                """

                return segment

            except Exception as e:
                # The spline creation failed, try the next option
                print(
                    f"Option {opt_idx}: Spline creation failed for segment {segment.main_index}.{segment.secondary_index} with error: {e}"
                )
                continue

        # Fallback option, change the curve model to POLYLINE and include all nodes
        print(
            f"Falling back to POLYLINE for segment {segment.main_index}.{segment.secondary_index}"
        )

        # Create the path as standard curve model with all nodes and set curve model to POLYLINE
        segment.path = Polyline(sub_path_points)
        segment.curve_model = PathCurveModel.COMPOUND

        # Create the segment as standard curve model instead of a spline
        segment = self.create_standard_segment(previous_segment, segment)

        return segment

    def combine_final_path_bodies(self):
        # Combine sepereate segment path bodies depending on divide options

        # Prepare for n standard path bodies
        num_divisions = Config.Manufacturing.DIVIDE_PATHS_IN
        standard_bodies = [None] * num_divisions
        counter = 0

        support_body = None
        accent_color_body = None

        # TODO first combine all segments with the same main_index, for example spline segments consists of sets of threes
        # TODO, when DIVIDE_PATHS_IN is 0, keep all paths seperate
        # TODO, seperate method to create inner bridge cut and addition to the path bodies to connect them

        for segment in self.path_architect.segments:
            # Skip segments with a start node.
            if any(node.puzzle_start for node in segment.nodes):
                continue

            # Skip segments that have no body.
            if not hasattr(segment, "path_body") or segment.path_body is None:
                print(
                    f"Segment at {segment.main_index}-{segment.secondary_index} has no body."
                )
                continue

            # Standard body processing:
            if num_divisions == 0:
                # If number of divisions is zero, do not combine: store each path body separately.
                standard_bodies.append(segment.path_body.part)
            else:
                # If number of divisions > 0, use cyclic bucket combination.
                bucket_idx = counter % num_divisions

                if standard_bodies[bucket_idx] is None:
                    standard_bodies[bucket_idx] = segment.path_body.part
                else:
                    standard_bodies[bucket_idx] = (
                        standard_bodies[bucket_idx] + segment.path_body.part
                    )
                    counter += 1

            # Check if the segment has a (optional) support body
            if hasattr(segment, "support_body") and segment.support_body is not None:
                if support_body is None:
                    support_body = segment.support_body.part
                else:
                    support_body = support_body + segment.support_body.part

            # Check if the segment has a (optional) color accent body
            if hasattr(segment, "accent_body") and segment.accent_body is not None:
                if accent_color_body is None:
                    accent_color_body = segment.accent_body.part
                else:
                    accent_color_body = accent_color_body + segment.accent_body.part

        return {
            PathTypes.STANDARD: [body for body in standard_bodies if body is not None],
            PathTypes.SUPPORT: support_body,
            PathTypes.ACCENT_COLOR: accent_color_body,
        }

    def create_start_area_funnel(self, segment: PathSegment):
        """
        Creates two lofted funnel shapes for the first segment of the puzzle
        One using U-shaped profiles, and another using U-shaped path accent coloring.
        """

        if len(segment.nodes) < 2:
            raise ValueError(
                "Start area funnel, segment must contain at least two nodes."
            )

        # Extract first and second node x, y, z coordinates
        first_coordinate = (segment.nodes[0].x, segment.nodes[0].y, segment.nodes[0].z)
        second_coordinate = (
            segment.nodes[-1].x,
            segment.nodes[-1].y,
            segment.nodes[-1].z,
        )

        # Create the standard path start area funnel
        with BuildPart() as start_area_standard:
            u_shape_params = Config.Path.PATH_PROFILE_TYPE_PARAMETERS[
                PathProfileType.U_SHAPE.value
            ]

            with BuildLine() as start_area_line:
                Line(first_coordinate, second_coordinate)
            # Create the two U-shaped profiles
            with BuildSketch(start_area_line.line ^ 0):
                add(create_u_shape(factor=6, **u_shape_params, rotation_angle=-90))
            with BuildSketch(start_area_line.line ^ 1):
                add(create_u_shape(**u_shape_params, rotation_angle=-90))
            loft()

        # Create the accent coloring path start area funnel
        with BuildPart() as start_area_coloring:
            u_shape_color_params = Config.Path.PATH_PROFILE_TYPE_PARAMETERS[
                PathProfileType.U_SHAPE_PATH_COLOR.value
            ]

            with BuildLine() as start_area_line:
                Line(first_coordinate, second_coordinate)
            # Create the two color profiles
            with BuildSketch(start_area_line.line ^ 0):
                add(
                    create_u_shape_path_color(
                        factor=6, **u_shape_color_params, rotation_angle=-90
                    )
                )
            with BuildSketch(start_area_line.line ^ 1):
                add(
                    create_u_shape_path_color(
                        **u_shape_color_params, rotation_angle=-90
                    )
                )
            loft()

        # Return both lofted shapes
        return start_area_standard, start_area_coloring

    def cut_holes_in_o_shape_path_profile_segments(self):
        n = 2  # Cut holes every n-th node
        possible_work_planes = [Plane.XY, Plane.XZ, Plane.YZ]
        main_index_to_work_plane_direction = {}
        main_index_to_has_mounting_node = {}

        # First pass: Build main_index_to_has_mounting_node mapping
        for segment in self.path_architect.segments:
            main_index = segment.main_index
            if main_index not in main_index_to_has_mounting_node:
                # Check if any segment with this main_index has a mounting node
                has_mounting_node = any(
                    node.mounting
                    for s in self.path_architect.segments
                    if s.main_index == main_index
                    for node in s.nodes
                )
                main_index_to_has_mounting_node[main_index] = has_mounting_node

        for segment in self.path_architect.segments:
            main_index = segment.main_index

            # Only process segments of PathProfileType O_SHAPE and Standard curve model
            if (
                segment.path_profile_type not in [PathProfileType.O_SHAPE]
                or segment.curve_model != PathCurveModel.COMPOUND
            ):
                continue  # Skip this segment

            # Determine the work plane direction for this main_index
            if main_index not in main_index_to_work_plane_direction:
                has_mounting_node = main_index_to_has_mounting_node[main_index]
                if has_mounting_node:
                    # Must use 'XY' work plane
                    work_plane = Plane.XY
                else:
                    # Randomly choose a work plane direction
                    work_plane = random.choice(possible_work_planes)
                main_index_to_work_plane_direction[main_index] = work_plane
            else:
                work_plane = main_index_to_work_plane_direction[main_index]

            # Skip O_SHAPE_SUPPORT segments if work plane is not 'XY',
            # no need to print support underneath holes along the Z axis
            if (
                work_plane != Plane.XY
                and segment.path_profile_type == PathProfileType.O_SHAPE_SUPPORT
            ):
                continue  # Skip this segment

            # Skip segments that are not straight
            if segment.curve_type not in [PathCurveType.STRAIGHT, None]:
                continue  # Skip this segment

            hole_size = Config.Puzzle.BALL_DIAMETER + 1
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

                # Create the cutting cylinder based on work plane direction
                with BuildPart() as cutting_cylinder:
                    with BuildSketch(work_plane):
                        Circle(hole_size / 2)
                    extrude(amount=self.node_size / 2 + self.node_size * 0.1, both=True)

                # Move the cutting cylinder to the node position
                cutting_cylinder.part.position = (node.x, node.y, node.z)

                # show_object(cutting_cylinder, name=f"Cutting Cylinder at Node {idx}")

                if segment.path_body and segment.path_body.part.is_valid():
                    segment.path_body.part = (
                        segment.path_body.part - cutting_cylinder.part
                    )
                if segment.support_body:
                    segment.support_body.part = (
                        segment.support_body.part - cutting_cylinder.part
                    )

    def determine_path_profile_angle(
        self,
        previous_segment: PathSegment,
        current_segment: PathSegment,
        start_angle: float,
    ) -> float:
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

        # If none type, print warning and return 0 degrees
        if previous_segment.path_body is None:
            print(
                f"Segment {previous_segment.main_index}.{previous_segment.secondary_index} has no path body"
            )
            return 0

        # Obtain faces from the swept shape
        swept_path_faces = previous_segment.path_body.part.faces()

        # Get parameters for the path profile type
        path_parameters = self.path_profile_type_parameters.get(
            previous_segment.path_profile_type.value, {}
        )
        # Apply the path profile function based on path profile registry
        path_profile_function = PROFILE_TYPE_FUNCTIONS.get(
            previous_segment.path_profile_type, create_u_shape
        )

        # Create previous segment profile type at the start of the current segment path with 90-degree angle increments
        for angle in range(0, 360, 90):
            # Create path profile sketch at the combined angle
            previous_segment_path_profile = path_profile_function(
                **path_parameters, rotation_angle=angle + start_angle
            )

            # Create sketch at start of the second path at respective angle
            with BuildSketch(current_segment.path ^ 0) as current_segment_path_profile:
                add(previous_segment_path_profile)

            # Compare the newly-created sketch with the faces of the sweep
            for swept_path_face in swept_path_faces:
                # Filter out faces that have a (nearly) identical area
                if are_float_values_close(
                    swept_path_face.area, current_segment_path_profile.sketch.area
                ):
                    # Check equality of face shape geometry
                    if are_equal_faces(
                        swept_path_face, current_segment_path_profile.sketch
                    ):
                        return angle

        # If no matching angle found, notify and return 0 degrees
        print(
            f"No matching profile type angle found for segment {previous_segment.main_index}.{previous_segment.secondary_index} to segment {current_segment.main_index}.{current_segment.secondary_index}"
        )

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


def are_equal_faces(face1: Face, face2: Face, tolerance: float = 0.01) -> bool:
    """
    Check if two faces have 'approximately' the same area within a given tolerance (default 1%).

    We measure the total 'difference area' (areas in face1 not in face2 plus
    areas in face2 not in face1) and compare it against the average area.
    """
    # Calculate the 'difference area' - area that doesn't overlap
    difference_area = (Sketch() + (face1 - face2)).area + (
        Sketch() + (face2 - face1)
    ).area

    # Use the average of the two face areas as the reference
    avg_area = (face1.area + face2.area) / 2

    # Guard against division by zero if either face has zero area
    if avg_area == 0:
        return difference_area == 0

    # Compare the difference area to a tolerance fraction of the average area
    return (difference_area / avg_area) <= tolerance


def sweep_single_profile(
    segment: PathSegment,
    profile: Sketch,
    transition_type: Transition,
    sweep_label: str = "Path",
) -> Part | None:
    """
    Helper for sweeping a single profile (main path, accent, or support).
    """

    try:
        # Create part out of path profile and path
        with BuildPart() as sweep_result:
            with BuildLine() as path_line:
                add(segment.path)
            # Create the path profile sketch on the work plane
            with BuildSketch(path_line.line ^ 0) as sketch_path_profile:
                add(profile)
            sweep(transition=transition_type)

        # Debugging / visualization

        """
        show_object(
            path_line,
            name=f"{segment.main_index}.{segment.secondary_index} - {sweep_label} Path",
        )
        show_object(
            sketch_path_profile.sketch,
            name=f"{segment.main_index}.{segment.secondary_index} - {sweep_label} Profile",
        )
        show_object(
            sweep_result,
            name=f"{segment.main_index}.{segment.secondary_index} - {sweep_label} Body",
        )
        """

        return sweep_result

    except Exception as e:
        print(
            f"Error sweeping {sweep_label.lower()} for segment "
            f"{segment.main_index}.{segment.secondary_index}: {e}"
        )
        return None


def round_to_nearest_90(value: float) -> float:
    if value not in [-180, -90, 0, 90, 180]:
        rounded_value = round(value / 90) * 90
        print(f"Warning: {value} was rounded to {rounded_value}")
    else:
        rounded_value = value

    return rounded_value


def normalize_angle(angle: float) -> float:
    """Normalize angle to the range (-180, 180)"""
    while angle <= -180:
        angle += 360
    while angle > 180:
        angle -= 360
    return angle


def is_close_to_origin(vec: Vector, tol=1e-5) -> bool:
    """Check if a vector is close to the origin within a tolerance."""
    return vec.length < tol
