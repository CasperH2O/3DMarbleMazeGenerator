# path_interpolator.py

import numpy as np
from scipy import interpolate
from geomdl import BSpline, utilities
import random

class PathInterpolator:
    def __init__(self, total_path, seed=None):
        """
        Initializes the PathInterpolator.

        :param total_path: List of nodes representing the path.
        :param seed: Seed for random selection of interpolation methods.
        """
        self.total_path = total_path
        self.seed = seed
        if self.seed is not None:
            random.seed(self.seed)
        self.interpolated_segments = []  # List to store interpolated segments with metadata

        # Initialize interpolation methods
        self.interpolation_methods = ['straight', 'bezier', 'spline']

        # Assign interpolation methods to segments
        self.segments = self.group_nodes_by_interpolation_method()

        # Interpolate segments
        self.interpolate_segments()

    def group_nodes_by_interpolation_method(self):
        """
        Groups nodes into segments where the interpolation method is assigned.
        The first segment always uses 'straight' interpolation.
        At each waypoint, the interpolation method is changed randomly.
        """
        segments = []
        current_segment_nodes = []
        current_method = 'straight'  # Start with 'straight'

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
        for segment in self.segments:
            method = segment['method']
            nodes = segment['nodes']
            if method == 'straight':
                self._interpolate_straight(nodes)
            elif method == 'bezier':
                self._interpolate_bezier(nodes)
            elif method == 'spline':
                self._interpolate_spline(nodes)
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

    def _interpolate_spline(self, nodes):
        """
        Interpolates a segment using splines between nodes.
        """
        if len(nodes) < 2:
            # Not enough points for a spline
            self._interpolate_straight(nodes)
            return

        # Extract coordinates
        xs = [node.x for node in nodes]
        ys = [node.y for node in nodes]
        zs = [node.z for node in nodes]

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
            self._interpolate_straight(nodes)
            return

        # Sample the spline
        uu = np.linspace(u_nodes[0], u_nodes[-1], 100)
        xx = sx(uu)
        yy = sy(uu)
        zz = sz(uu)
        segment_points = np.vstack([xx, yy, zz]).T
        segment = {
            'type': 'spline',
            'points': segment_points
        }
        self.interpolated_segments.append(segment)
