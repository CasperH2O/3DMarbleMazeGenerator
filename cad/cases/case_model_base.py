# cad/cases/case_model_base.py

from abc import ABC, abstractmethod
from enum import Enum

from build123d import (
    Align,
    Axis,
    BuildPart,
    Cylinder,
    Keep,
    Mode,
    Part,
    Plane,
    Sphere,
    chamfer,
    split,
)
from ocp_vscode import Camera, set_defaults, set_viewer_config, show, status


class CaseManufacturer(Enum):
    GENERIC = "generic"
    SPHERE_PLAYTASTIC_120_MM = "sphere_playtastic_120_mm"
    SPHERE_PLAYTASTIC_170_MM = "sphere_playtastic_170_mm"
    SPHERE_SAIDKOCC_100_MM = "sphere_saidkocc_100_mm"


class CasePart(Enum):
    """
    Enumeration representing the different types of case parts
    """

    BASE = "Base"
    MOUNTING_RING_CLIP_START = "Mounting Clip Start"
    MOUNTING_RING_CLIP_SINGLE = "Mounting Clip Single"
    MOUNTING_RING_CLIPS = "Mounting Clips"
    CASING = "Casing"
    CASE_TOP = "Case Top"
    CASE_BOTTOM = "Case Bottom"
    MOUNTING_RING = "Mounting Ring"
    MOUNTING_RING_TOP = "Mounting Ring Top"
    MOUNTING_RING_BOTTOM = "Mounting Ring Bottom"
    START_INDICATOR = "Start Indicator"
    INTERNAL_PATH_BRIDGES = "Path Bridges"


class CaseShape(Enum):
    """
    Enumeration representing the different shapes of the puzzle casing.
    """

    SPHERE = "Sphere"
    SPHERE_WITH_FLANGE = "Sphere with flange"
    SPHERE_WITH_FLANGE_ENCLOSED_TWO_SIDES = "Sphere with flange enclosed two sides"
    BOX = "Box"
    CYLINDER = "Cylinder"


class Case(ABC):
    @abstractmethod
    def __init__(self):
        pass

    @abstractmethod
    def get_parts(self) -> list[Part]:
        """Return the case components as a list Part objects."""
        pass

    @abstractmethod
    def get_base_parts(self) -> list[Part]:
        """Return the base components as a list of Part objects."""
        pass

    @staticmethod
    def _create_circular_base_parts(
        sphere_diameter: float,
        top_color: str,
        bottom_color: str,
        edge_color: str,
    ) -> list[Part]:
        """
        Build the standard circular base used by spherical casings.
        """

        _BASE_TOP_LABEL = "Base Top"
        _BASE_BOTTOM_LABEL = "Base Bottom"
        _BASE_EDGE_LABEL = "Base Edge"

        _OUTER_RADIUS = 30.0
        _INNER_RADIUS = 15.0
        _CLEARANCE_OFFSET = 7.0
        _FOOT_OFFSET = 5.0
        _EDGE_OFFSET = 6.5
        _CHAMFER_LENGTH = 2.0

        extrusion_amount = -1 * (sphere_diameter / 2 + _CLEARANCE_OFFSET)

        with BuildPart() as base:
            Cylinder(
                radius=_OUTER_RADIUS,
                height=-extrusion_amount,
                align=(Align.CENTER, Align.CENTER, Align.MAX),
            )
            Cylinder(
                radius=_INNER_RADIUS,
                height=-extrusion_amount,
                align=(Align.CENTER, Align.CENTER, Align.MAX),
                mode=Mode.SUBTRACT,
            )
            Sphere(radius=sphere_diameter / 2, mode=Mode.SUBTRACT)
            chamfer(base.edges().group_by(Axis.Z)[0], length=_CHAMFER_LENGTH)
            chamfer(base.edges().group_by(Axis.Z)[-1], length=_CHAMFER_LENGTH)

        base_foot = split(
            objects=base.part,
            bisect_by=Plane.XY.offset(extrusion_amount + _FOOT_OFFSET),
            keep=Keep.BOTTOM,
        )
        base_edge = split(
            objects=base.part,
            bisect_by=Plane.XY.offset(extrusion_amount + _EDGE_OFFSET),
            keep=Keep.BOTTOM,
        )

        base.part -= base_foot
        base.part -= base_edge
        base_edge -= base_foot

        base.part.label = _BASE_TOP_LABEL
        base.part.color = top_color

        base_foot.label = _BASE_BOTTOM_LABEL
        base_foot.color = bottom_color

        base_edge.label = _BASE_EDGE_LABEL
        base_edge.color = edge_color

        return [base.part, base_foot, base_edge]

    def preview(self) -> None:
        """
        Build parts, include the cut shape (hidden) for viewing
        """

        parts = self.get_parts() or []
        base_parts = self.get_base_parts() or []
        objs = [*parts, *base_parts]
        names = [getattr(p, "label", "Part") for p in parts]
        names.extend(getattr(p, "label", "Part") for p in base_parts)

        # include cut shape
        self.cut_shape.part.label = "Cut Shape"
        self.cut_shape.part.color = "#FF00000F"  # very transparent red
        objs.append(self.cut_shape.part)
        names.append("Cut Shape")

        # show first (so groups exist)
        set_defaults(reset_camera=Camera.KEEP, black_edges=True)
        show(*objs, names=names)

        # fetch states and edit leaves
        st = status()["states"].copy()

        def set_group(prefix: str, shape: int | None, edges: int | None):
            gp = f"/Group/{prefix}"
            for k, v in list(st.items()):
                # only touch leaves (v is a [shape, edges] list); internal nodes are 2
                if (
                    (k == gp or k.startswith(gp + "/"))
                    and isinstance(v, list)
                    and len(v) == 2
                ):
                    s, e = v
                    if shape is not None:
                        s = shape
                    if edges is not None:
                        e = edges
                    st[k] = [s, e]

        # Hide the cut volume completely
        set_group("Cut Shape", shape=0, edges=0)

        # Show casing solids but hide edges
        set_group(CasePart.CASING.value, shape=1, edges=0)
        set_group(CasePart.CASE_TOP.value, shape=1, edges=0)
        set_group(CasePart.CASE_BOTTOM.value, shape=1, edges=0)

        set_viewer_config(states=st)
