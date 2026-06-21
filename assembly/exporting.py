# assembly/exporting.py

import os
from collections.abc import Iterable
from pathlib import Path

from build123d import Part, Vector, export_stl

from assembly.casing import CasePart
from config import Config


def _export_folder_name() -> str:
    return f"Case-{Config.Puzzle.CASE_SHAPE.value}-Seed-{Config.Puzzle.SEED}"


def _case_export_root() -> str:
    return os.path.join("export", _export_folder_name())


def _create_export_folders(export_root: str) -> dict[str, str]:
    # create the four categories for folder sorting
    folders = {
        "Puzzle": os.path.join(export_root, "Puzzle"),
        "Mounting": os.path.join(export_root, "Mounting"),
        "Base": os.path.join(export_root, "Base"),
        "Extra": os.path.join(export_root, "Extra"),
    }
    for folder_path in folders.values():
        os.makedirs(folder_path, exist_ok=True)
    return folders


def _flatten_parts(parts: Iterable):
    for item in parts:
        if isinstance(item, list):
            yield from _flatten_parts(item)
        else:
            yield item


def _categorize_case_part(label: str) -> str:
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

    if label in puzzle_case:
        return "Puzzle"
    if label in mounting_case:
        return "Mounting"
    if label in extra_case:
        return "Extra"
    # anything un-matched goes to Extra
    return "Extra"


def _prepare_parts_for_manufacturing(case_parts: list[Part]) -> None:
    # Adjust some orientation to prepare for 3D printing plate
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


def _part_records(case_parts: list[Part], base_parts: list[Part], additional_parts=None):
    for part in case_parts:
        yield _categorize_case_part(part.label), part

    for part in base_parts:
        yield "Base", part

    # export additional objects, the paths, if any.
    if additional_parts:
        # all these go into the puzzle folder
        for part in _flatten_parts(additional_parts):
            try:
                part.label
            except AttributeError:
                continue
            yield "Puzzle", part


def _default_orca_print_settings():
    from orca123d import PrintSettings

    return PrintSettings(
        enable_support=Config.Manufacturing.ORCA_ENABLE_SUPPORT,
        support_interface_top_layers=Config.Manufacturing.ORCA_SUPPORT_INTERFACE_TOP_LAYERS,
        support_interface_bottom_layers=Config.Manufacturing.ORCA_SUPPORT_INTERFACE_BOTTOM_LAYERS,
        support_interface_filament=Config.Manufacturing.ORCA_SUPPORT_INTERFACE_FILAMENT,
    )


def _export_stl_parts(
    case_parts: list[Part],
    base_parts: list[Part],
    additional_parts=None,
) -> str:
    export_root = os.path.join(_case_export_root(), "stl")
    folders = _create_export_folders(export_root)

    for category, part in _part_records(case_parts, base_parts, additional_parts):
        label = part.label
        export_stl(
            to_export=part,
            file_path=os.path.join(folders[category], f"{label}.stl"),
        )

    return export_root


def _export_3mf_parts(
    case_parts: list[Part],
    base_parts: list[Part],
    additional_parts=None,
) -> str:
    try:
        from orca123d import Project, ProjectInfo
    except ImportError as import_error:
        raise RuntimeError(
            "3MF export requires orca123d. Install dependencies from requirements.txt "
            "before enabling Config.Manufacturing.EXPORT_3MF."
        ) from import_error

    export_root = os.path.join(_case_export_root(), "3mf")
    os.makedirs(export_root, exist_ok=True)
    print_settings = _default_orca_print_settings()

    for _, part in _part_records(case_parts, base_parts, additional_parts):
        label = part.label
        project = Project(
            info=ProjectInfo(
                title=label,
                designer="3D Marble Maze Generator",
                description=(
                    "Model-only OrcaSlicer 3MF export with support interface "
                    "settings for soluble PVA interface material."
                ),
            )
        )
        project.add_object(part, name=label, settings=print_settings)
        project.save(Path(export_root) / f"{label}.3mf")

    return export_root


def export_all(
    case_parts: list[Part],
    base_parts: list[Part],
    additional_parts=None,
    apply_manufacturing_preparation: bool = True,
) -> str | None:
    """Export all case parts for 3D print manufacturing.

    Args:
        case_parts: List of case parts to export.
        base_parts: List of base parts to export.
        additional_parts: Optional additional parts to export.
        apply_manufacturing_preparation: If True, apply rotations and other tweaks for optimal 3D printing.
                                        If False, export in original model orientation (for visualization).

    Returns the export root folder when exports are enabled, otherwise ``None``.
    """
    if not Config.Manufacturing.EXPORT_STL and not Config.Manufacturing.EXPORT_3MF:
        return None

    if apply_manufacturing_preparation:
        _prepare_parts_for_manufacturing(case_parts)

    export_roots = []
    if Config.Manufacturing.EXPORT_STL:
        export_roots.append(_export_stl_parts(case_parts, base_parts, additional_parts))
    if Config.Manufacturing.EXPORT_3MF:
        export_roots.append(_export_3mf_parts(case_parts, base_parts, additional_parts))

    return export_roots[-1] if export_roots else None
