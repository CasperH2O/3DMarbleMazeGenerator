# path_interpolator.py

import numpy as np
from scipy import interpolate
from geomdl import BSpline, utilities
import random
import config


class PathInterpolator:
    def __init__(self, total_path, seed, interpolation_types=config.Path.PATH_CURVE_TYPES):
        """
        Initializes the PathInterpolator.

        :param total_path: List of nodes representing the path.
        :param seed: Seed for random selection of interpolation methods.
        :param interpolation_types: List of interpolation methods from config.
        """
        self.total_path = total_path
        self.seed = seed

        self.interpolated_segments = []  # List to store interpolated segments with metadata
        self._spline_cache = None  # Cache for the computed spline

        # Initialize interpolation methods from config
        self.interpolation_methods = interpolation_types.copy()

        # Assign interpolation methods to segments
        self.segments = self.group_nodes_by_interpolation_method()

        # Interpolate segments
        self.interpolate_segments()

    def group_nodes_by_interpolation_method(self):
        """
        Groups nodes into segments where the interpolation method is assigned.
        The first segment uses the first method from the interpolation methods.
        At each waypoint, the interpolation method is changed randomly.
        """
        segments = []
        current_segment_nodes = []

        # Start with the first interpolation method
        current_method = self.interpolation_methods[0]

        total_path_nodes = self.total_path
        interpolation_methods = self.interpolation_methods.copy()

        for i, node in enumerate(total_path_nodes):
            current_segment_nodes.append(node)
            if node.waypoint and i != 0:
                # Save the current segment before changing the method
                segments.append({
                    'method': current_method,
                    'nodes': current_segment_nodes.copy()
                })
                # Change interpolation method randomly for the next segment
                new_methods = [m for m in interpolation_methods if m != current_method]
                if new_methods:
                    current_method = random.choice(new_methods)
                # Start a new segment beginning with the current waypoint
                current_segment_nodes = [node]
        # After processing all nodes, add the last segment
        if current_segment_nodes:
            segments.append({
                'method': current_method,
                'nodes': current_segment_nodes.copy()
            })
        return segments

    def interpolate_segments(self):
        """
        Interpolates each segment using its assigned interpolation method.
        """
        # Map method names to interpolation functions
        interpolation_functions = {
            'polyline': self._interpolate_straight,
            'bezier': self._interpolate_bezier,
            'spline': self._interpolate_spline,
            # Add other interpolation methods here if needed
        }

        for segment in self.segments:
            method = segment['method']
            nodes = segment['nodes']
            if method in interpolation_functions:
                interpolation_functions[method](nodes)
            else:
                raise ValueError(f"Unknown interpolation method: {method}")


    def _interpolate_straight(self, nodes):
        """
        Interpolates a segment using straight lines between nodes.
        """
        points = [(node.x, node.y, node.z) for node in nodes]
        segment = {
            'type': 'straight',
            'points': np.array(points)
        }
        self.interpolated_segments.append(segment)

    def _interpolate_bezier(self, nodes):
        """
        Interpolates a segment using Bézier curves (using NURBS).
        """
        if len(nodes) < 4:
            # Not enough points for a Bézier curve of degree 3
            self._interpolate_straight(nodes)
            return

        control_points = [[node.x, node.y, node.z] for node in nodes]

        # Create a B-Spline curve instance
        curve = BSpline.Curve()

        # Set up the curve degree and control points
        curve.degree = 3
        curve.ctrlpts = control_points

        # Auto-generate the knot vector
        curve.knotvector = utilities.generate_knot_vector(curve.degree, len(control_points))

        # Increase the evaluation resolution for smoother curves
        curve.delta = 0.001  # Lower delta for smoother evaluation

        # Evaluate the curve points
        curve.evaluate()

        # Extract the evaluated points
        curve_points = np.array(curve.evalpts)
        segment = {
            'type': 'bezier',
            'points': curve_points
        }
        self.interpolated_segments.append(segment)

    def _interpolate_spline(self, segment_nodes):
        """
        Interpolates a segment using splines between nodes.
        Returns only the segment corresponding to the provided nodes.
        Segments are based on spline based on full route for large fluid curves
        """
        # Ensure the spline has been computed
        if not hasattr(self, '_spline_segments'):
            self._compute_full_spline()

        # Find the spline segment corresponding to the provided nodes
        start_node = segment_nodes[0]
        end_node = segment_nodes[-1]

        # Search for the matching spline segment
        for spline_segment in self._spline_segments:
            if spline_segment['start_node'] == start_node and spline_segment['end_node'] == end_node:
                # Found the matching segment
                segment = {
                    'type': 'spline',
                    'points': spline_segment['points']
                }
                self.interpolated_segments.append(segment)
                return

        # If no matching spline segment is found, fall back to straight line
        self._interpolate_straight(segment_nodes)

    def _compute_full_spline(self):
        """
        Computes the full spline over the relevant nodes (waypoints and adjacent nodes), splits it at waypoints,
        and caches the spline segments.
        """
        total_path_nodes = self.total_path

        # Collect waypoint nodes along with the nodes immediately before and after each waypoint
        relevant_nodes_set = set()
        for i, node in enumerate(total_path_nodes):
            if node.waypoint:
                relevant_nodes_set.add(node)
                if i > 0:
                    relevant_nodes_set.add(total_path_nodes[i - 1])
                if i < len(total_path_nodes) - 1:
                    relevant_nodes_set.add(total_path_nodes[i + 1])

        # Sort the relevant nodes by their original order in total_path
        relevant_nodes = sorted(relevant_nodes_set, key=lambda node: total_path_nodes.index(node))

        if len(relevant_nodes) < 2:
            # Not enough points for a spline
            self._interpolate_straight(total_path_nodes)
            return

        # Extract coordinates
        xs = [node.x for node in relevant_nodes]
        ys = [node.y for node in relevant_nodes]
        zs = [node.z for node in relevant_nodes]

        # Chord-length parameterization
        xyz = np.vstack([xs, ys, zs]).T
        u_nodes = np.cumsum(np.r_[0, np.linalg.norm(np.diff(xyz, axis=0), axis=1)])

        # Create splines for each coordinate
        try:
            sx = interpolate.InterpolatedUnivariateSpline(u_nodes, xs)
            sy = interpolate.InterpolatedUnivariateSpline(u_nodes, ys)
            sz = interpolate.InterpolatedUnivariateSpline(u_nodes, zs)
        except Exception as e:
            # In case of errors, fall back to straight lines
            self._interpolate_straight(total_path_nodes)
            return

        # Sample the spline
        uu = np.linspace(u_nodes[0], u_nodes[-1], 1000)
        xx = sx(uu)
        yy = sy(uu)
        zz = sz(uu)
        spline_points = np.vstack([xx, yy, zz]).T

        # Identify indices of waypoints in relevant_nodes
        waypoint_indices = [i for i, node in enumerate(relevant_nodes) if node.waypoint]
        u_waypoints = u_nodes[waypoint_indices]

        # Split the spline at waypoints and store each segment
        self._spline_segments = []
        start_idx = 0
        for i in range(len(u_waypoints)):
            end_u = u_waypoints[i]
            end_idx = np.searchsorted(uu, end_u)

            # Get the segment points
            segment_xx = xx[start_idx:end_idx + 1]
            segment_yy = yy[start_idx:end_idx + 1]
            segment_zz = zz[start_idx:end_idx + 1]
            segment_points = np.vstack([segment_xx, segment_yy, segment_zz]).T

            # Store the segment along with its corresponding waypoints
            segment_info = {
                'start_node': relevant_nodes[waypoint_indices[i - 1]] if i > 0 else relevant_nodes[0],
                'end_node': relevant_nodes[waypoint_indices[i]],
                'points': segment_points
            }
            self._spline_segments.append(segment_info)

            # Update indices for next segment
            start_idx = end_idx
