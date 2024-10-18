# shapes/case_sphere_with_flange.py

from .case_base import CaseBase
import cadquery as cq
import math
from config import Config


# Include the faceOnWire method
def _face_on_wire(self, path: cq.Wire) -> cq.Face:
    """Reposition a face from alignment to the x-axis to the provided path"""
    path_length = path.Length()

    bbox = self.BoundingBox()
    face_bottom_center = cq.Vector((bbox.xmin + bbox.xmax) / 2, 0, 0)
    relative_position_on_wire = face_bottom_center.x / path_length
    wire_tangent = path.tangentAt(relative_position_on_wire)
    wire_angle = math.degrees(math.atan2(wire_tangent.y, wire_tangent.x))
    wire_position = path.positionAt(relative_position_on_wire)

    return self.rotate(
        face_bottom_center, face_bottom_center + cq.Vector(0, 0, 1), wire_angle
    ).translate(wire_position - face_bottom_center)


# Attach the method to cq.Face
cq.Face.faceOnWire = _face_on_wire


def text_on_wire(txt: str, fontsize: float, path: cq.Wire, extrude_depth: float) -> cq.Solid:
    """Create 3D text with a baseline following the given path"""
    # Create the text as faces
    text_wp = cq.Workplane("XY").text(
        txt=txt,
        fontsize=fontsize,
        distance=0,  # Create text as faces (2D)
        halign="center",
        valign="center",
        font='Pacifico-Regular',
        fontPath="resources\\Pacifico-Regular.ttf",
    )
    linear_faces = text_wp.faces().vals()

    # Fuse the faces together and clean the result
    text_flat = linear_faces[0]
    if len(linear_faces) > 1:
        for face in linear_faces[1:]:
            text_flat = text_flat.fuse(face)
        text_flat = text_flat.clean()
    else:
        text_flat = text_flat.clean()

    # After fusing, text_flat is a Compound. Extract the faces
    fused_faces = text_flat.Faces()

    # Reposition each face along the path
    faces_on_path = [face.faceOnWire(path) for face in fused_faces]

    # Extrude each face by the specified depth using extrudeLinear
    extruded_solids = [
        cq.Solid.extrudeLinear(face, cq.Vector(0, 0, extrude_depth)) for face in faces_on_path
    ]

    # Combine all extruded solids into one compound
    return cq.Compound.makeCompound(extruded_solids)


class CaseSphereWithFlange(CaseBase):
    def __init__(self):
        self.sphere_outer_diameter = Config.Sphere.SPHERE_DIAMETER
        self.sphere_flange_diameter = Config.Sphere.SPHERE_FLANGE_DIAMETER
        self.sphere_thickness = Config.Sphere.SHELL_THICKNESS
        self.mounting_ring_thickness = Config.Sphere.MOUNTING_RING_THICKNESS
        self.ball_diameter = Config.Puzzle.BALL_DIAMETER
        self.mounting_hole_diameter = Config.Sphere.MOUNTING_HOLE_DIAMETER
        self.mounting_hole_amount = Config.Sphere.MOUNTING_HOLE_AMOUNT
        self.node_size = Config.Puzzle.NODE_SIZE
        self.number_of_mounting_points = Config.Sphere.NUMBER_OF_MOUNTING_POINTS
        self.mounting_distance = Config.Sphere.SPHERE_DIAMETER - Config.Puzzle.NODE_SIZE

        # Derived variables
        self.sphere_inner_diameter = self.sphere_outer_diameter - (2 * self.sphere_thickness)
        self.sphere_outer_radius = self.sphere_outer_diameter / 2
        self.sphere_inner_radius = self.sphere_inner_diameter / 2
        self.sphere_flange_radius = self.sphere_flange_diameter / 2

        # Create the components
        self.mounting_ring, self.path_bridges, self.start_text = self.create_mounting_ring()
        self.dome_top, self.dome_bottom = self.create_domes()
        self.add_mounting_holes()

    def create_mounting_ring(self):
        # Create the mounting ring
        mounting_ring = (
            cq.Workplane("XY")
            .circle(self.sphere_flange_radius)  # Outer circle
            .circle(self.sphere_inner_radius)  # Inner circle (hole)
            .extrude(self.mounting_ring_thickness)  # Extrude thickness
        )
        # Move to center in Z
        mounting_ring = mounting_ring.translate((0, 0, -0.5 * self.mounting_ring_thickness))

        # Define the circular path for the text
        text_radius = (self.sphere_outer_radius + self.sphere_flange_radius) / 2
        path = cq.Workplane("XY").circle(text_radius).edges().val()

        # Rotate the path by 180 degrees around the Z-axis if needed
        path = path.rotate((0, 0, 0), (0, 0, 1), 180)

        # Create the text along the path
        text_on_path = text_on_wire(
            txt="START",
            fontsize=6,  # Adjust fontsize as needed
            path=path,
            extrude_depth=-1  # Negative value to extrude into the ring
        )

        # Position the text at the top surface of the ring
        text_on_path = text_on_path.translate((0, 0, 0.5 * self.mounting_ring_thickness))

        # Subtract the text from the mounting ring
        mounting_ring = mounting_ring.cut(text_on_path)

        # Add rectangular mounting bridges for the mounting ring, skipping the first one and rotating 180 degrees
        mounting_ring_bridges = (
            cq.Workplane("XY")
            .polarArray(self.mounting_distance / 2, 180, 360, self.number_of_mounting_points)[1:]  # Skip the first rectangle and start at 180 degrees
            .rect(self.node_size * 2, self.node_size)  # Define the rectangle
            .extrude(self.mounting_ring_thickness / 2, both=True)  # Extrude symmetrically
        )

        # Add rectangular mounting bridges for the path within, skipping the first one and rotating 180 degrees
        # Todo, add to config
        printing_layer_thickness = 0.2
        printing_nozzle_diameter = 0.4

        path_bridges = (
            cq.Workplane("XY")
            .polarArray(self.mounting_distance / 2, 180, 360, self.number_of_mounting_points)[1:]  # Skip the first rectangle and start at 180 degrees
            .rect(self.node_size * 2 + 4 * printing_nozzle_diameter, self.node_size - 4 * printing_nozzle_diameter)  # Define the rectangle
            .extrude(self.mounting_ring_thickness / 2 - printing_layer_thickness * 4, both=True)  # Extrude symmetrically
        )

        # Combine the ring and the nodes, cut out path bridge
        path_bridges = path_bridges.cut(mounting_ring)
        mounting_ring = mounting_ring.union(mounting_ring_bridges.cut(path_bridges))

        return mounting_ring, path_bridges, text_on_path

    def create_domes(self):
        # Calculate the intermediate point at 45 degrees (π/4 radians)
        angle_45 = math.radians(45)

        # Intermediate points for inner arc
        x_mid_inner = self.sphere_inner_radius * math.cos(angle_45)

        # Calculate adjusted starting point for outer arc
        x_start_outer = math.sqrt(self.sphere_outer_radius**2 - self.sphere_thickness**2)
        y_start_outer = self.sphere_thickness  # Given

        # Calculate angle for adjusted starting point
        theta_start = math.asin(y_start_outer / self.sphere_outer_radius)

        # Calculate intermediate point for outer arc
        theta_mid_outer = (theta_start + math.pi / 2) / 2
        x_mid_outer = self.sphere_outer_radius * math.cos(theta_mid_outer)
        y_mid_outer = self.sphere_outer_radius * math.sin(theta_mid_outer)

        # Create the profile on the XZ plane
        dome_profile = (
            cq.Workplane("XZ")
            # Start at the outer circle top
            .moveTo(0, self.sphere_outer_radius)  # Point A
            .lineTo(0, self.sphere_inner_radius)  # Line down to Point B
            .threePointArc((x_mid_inner, self.sphere_inner_radius * math.sin(angle_45)), (self.sphere_inner_radius, 0))  # Inner arc to Point C
            .lineTo(self.sphere_flange_radius, 0)  # Line to Point D
            .lineTo(self.sphere_flange_radius, self.sphere_thickness)  # Line up to Point E
            .lineTo(x_start_outer, y_start_outer)  # Line to adjusted starting point for outer arc (Point F)
            .threePointArc((x_mid_outer, y_mid_outer), (0, self.sphere_outer_radius))  # Outer arc back to Point A
            .close()
        )

        # Revolve the dome profile
        dome_top = dome_profile.revolve(angleDegrees=360, axisStart=(0, 0, 0), axisEnd=(0, 1, 0))

        # Move to make place for mounting ring
        # Add small distance to prevent overlap artifacts during rendering
        dome_top = dome_top.translate((0, 0, 0.5 * self.mounting_ring_thickness + 0.01))

        # Mirror the dome for the other side
        dome_bottom = dome_top.mirror(mirrorPlane="XY")

        return dome_top, dome_bottom

    def add_mounting_holes(self):
        # Calculate the hole pattern radius
        hole_pattern_radius = (self.sphere_outer_radius + self.sphere_flange_radius) / 2  # Average radius

        # Create a work plane on the XY plane
        wp = cq.Workplane("XY")

        # Define the hole pattern
        holes = (
            wp
            .workplane()
            .polarArray(hole_pattern_radius, 45, 360, self.mounting_hole_amount, fill=True)
            .circle(self.mounting_hole_diameter / 2)
            .extrude(3 * self.sphere_thickness, both=True)  # Extrude length sufficient to cut through the bodies
        )

        # Cut the holes in applicable bodies
        self.mounting_ring = self.mounting_ring.cut(holes)
        self.dome_top = self.dome_top.cut(holes)
        self.dome_bottom = self.dome_bottom.cut(holes)

    def get_cad_objects(self):
        return {
            "Mounting Ring": (self.mounting_ring, {"color": (40, 40, 43)}),
            "Dome Top": (self.dome_top, {"alpha": 0.9, "color": (1, 1, 1)}),
            "Dome Bottom": (self.dome_bottom, {"alpha": 0.9, "color": (1, 1, 1)}),
            "Path Bridge": (self.path_bridges, {"color": (57, 255, 20)}),
            "Start Text": (self.start_text, {"color": (57, 255, 20)}),
        }

    def get_cut_shape(self):
        # Add small distance for tolerances
        flush_distance_tolerance = 0.0

        # Create the cross-sectional profile of the hollow sphere
        hollow_sphere_profile = (
            cq.Workplane("XZ")
            .moveTo(0, self.sphere_outer_radius * 2)
            .threePointArc((-self.sphere_outer_radius * 2, 0), (0, -self.sphere_outer_radius * 2))
            .lineTo(0, -self.sphere_inner_radius + flush_distance_tolerance)
            .threePointArc((-self.sphere_inner_radius + flush_distance_tolerance, 0), (0, self.sphere_inner_radius - flush_distance_tolerance))
            .close()
        )

        # Revolve the profile to create the hollow sphere solid
        hollow_sphere = hollow_sphere_profile.revolve(angleDegrees=360)
        return hollow_sphere
