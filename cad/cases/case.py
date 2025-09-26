# cad/cases/case.py

from abc import ABC, abstractmethod
from enum import Enum

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

    MOUNTING_RING_CLIP_START = "Mounting Clip Start"
    MOUNTING_RING_CLIP_SINGLE = "Mounting Clip Single"
    MOUNTING_RING_CLIPS = "Mounting Clips"
    CASING = "Casing"
    DOME_TOP = "Dome Top"
    DOME_BOTTOM = "Dome Bottom"
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


class Case(ABC):
    @abstractmethod
    def __init__(self):
        pass

    @abstractmethod
    def get_parts(self):
        """
        Returns a dictionary of CasePart objects representing the case components.
        """
        pass

    def preview(self) -> None:
        """
        Build parts, include the cut shape (hidden) for viewing
        """

        parts = self.get_parts() or []
        objs = [*parts]
        names = [getattr(p, "label", "Part") for p in parts]

        # include cut shape
        self.cut_shape.part.label = "Cut Shape"
        self.cut_shape.part.color = "#FF00000F"  # very transparent red
        objs.append(self.cut_shape.part)
        names.append("Cut Shape")

        # show first (so groups exist)
        set_defaults(reset_camera=Camera.KEEP)
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
        set_group(CasePart.DOME_TOP.value, shape=1, edges=0)
        set_group(CasePart.DOME_BOTTOM.value, shape=1, edges=0)

        set_viewer_config(states=st)
