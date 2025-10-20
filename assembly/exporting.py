# assembly/exporting.py

import os

from build123d import Part, Vector, export_stl

from assembly.casing import CasePart
from config import Config


def export_all(case_parts: list[Part], base_parts: list[Part], additional_parts=None):
    """
    Export all case parts as STLs for 3D print manufacturing.
    """
    if not Config.Manufacturing.EXPORT_STL:
        return

    # root export folder
    folder_name = f"Case-{Config.Puzzle.CASE_SHAPE.value}-Seed-{Config.Puzzle.SEED}"
    export_root = os.path.join("export", "stl", folder_name)
    os.makedirs(export_root, exist_ok=True)

    # create the four categories for folder sorting
    folders = {
        "Puzzle": os.path.join(export_root, "Puzzle"),
        "Mounting": os.path.join(export_root, "Mounting"),
        "Base": os.path.join(export_root, "Base"),
        "Extra": os.path.join(export_root, "Extra"),
    }
    for p in folders.values():
        os.makedirs(p, exist_ok=True)

    # export each case part to STL format
    puzzle_case = {
        CasePart.MOUNTING_RING.value,
        CasePart.INTERNAL_PATH_BRIDGES.value,
    }
    mounting_case = {
        CasePart.MOUNTING_RING_TOP.value,
        CasePart.MOUNTING_RING_BOTTOM.value,
        CasePart.MOUNTING_RING_CLIP_START.value,
        CasePart.MOUNTING_RING_CLIP_SINGLE.value,
        CasePart.START_INDICATOR.value,
    }
    extra_case = {
        CasePart.CASE_TOP.value,
        CasePart.CASE_BOTTOM.value,
        CasePart.CASING.value,
        CasePart.MOUNTING_RING_CLIPS.value,
    }

    # Adjust some orienation to prepare for 3D printing plate
    for part in case_parts:
        match part.label:
            # Rotate mounting ring top upside down
            case CasePart.MOUNTING_RING_TOP.value:
                part.orientation = Vector(0, 180, 0)
            # Rotate mounting clips
            case (
                CasePart.START_INDICATOR.value
                | CasePart.MOUNTING_RING_CLIP_START.value
                | CasePart.MOUNTING_RING_CLIP_SINGLE.value
            ):
                part.orientation = Vector(90, 0, 0)

    for part in case_parts:
        label = part.label
        if label in puzzle_case:
            dst = folders["Puzzle"]
        elif label in mounting_case:
            dst = folders["Mounting"]
        elif label in extra_case:
            dst = folders["Extra"]
        else:
            # anything un-matched goes to Extra
            dst = folders["Extra"]
        export_stl(to_export=part, file_path=os.path.join(dst, f"{label}.stl"))

    # export puzzle stand base
    for part in base_parts:
        label = part.label
        dst = folders["Base"]
        export_stl(to_export=part, file_path=os.path.join(dst, f"{label}.stl"))

    # export additional objects, the paths, if any.
    if additional_parts:

        # flatten nested lists, for split body paths
        def _flatten(parts):
            for item in parts:
                if isinstance(item, list):
                    yield from _flatten(item)
                else:
                    yield item

        # all these go into the puzzle folder
        for part in _flatten(additional_parts):
            label = part.label
            dst = folders["Puzzle"]
            export_stl(to_export=part, file_path=os.path.join(dst, f"{label}.stl"))
