# assembly/exporting.py

import logging
import os
from collections.abc import Iterable
from pathlib import Path

from build123d import Part, Vector, export_stl

from assembly.casing import CasePart
from cad.cases.case_model_base import CaseShape
from config import Config

from orca123d import Project, ProjectInfo, PrintSettings

logger = logging.getLogger(__name__)


def _case_export_root() -> str:
    """Builds the per-configuration export root path, unique per case shape and seed."""
    export_folder_name = f"Case-{Config.Puzzle.CASE_SHAPE.value}-Seed-{Config.Puzzle.SEED}"
    return os.path.join("export", export_folder_name)


def _create_export_folders(export_root: str) -> dict[str, str]:
    """Creates the category subfolders under export_root and returns their paths."""
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
    """Recursively flattens nested lists of parts into a single sequence."""
    for item in parts:
        if isinstance(item, list):
            yield from _flatten_parts(item)
        else:
            yield item


def _categorize_case_part(label: str) -> str:
    """Maps a CasePart label to its export category (Puzzle, Mounting, Base, or Extra)."""
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
    return "Extra"


def _prepare_parts_for_manufacturing(case_parts: list[Part]) -> None:
    """Rotates parts into print-ready orientations before export.

    Parts are designed in assembly orientation; some need to be flipped or
    rotated so they sit flat on the build plate without requiring support.
    """
    for part in case_parts:
        match part.label:
            case CasePart.MOUNTING_RING_TOP.value:
                part.orientation = Vector(0, 180, 0)
            case (
                CasePart.START_INDICATOR.value
                | CasePart.MOUNTING_RING_CLIP_START.value
                | CasePart.MOUNTING_RING_CLIP_SINGLE.value
            ):
                part.orientation = Vector(90, 0, 0)


def _part_records(case_parts: list[Part], base_parts: list[Part], additional_parts=None):
    """Yields (category, part) pairs for all parts across case, base, and additional inputs."""
    for part in case_parts:
        yield _categorize_case_part(part.label), part

    for part in base_parts:
        yield "Base", part

    if additional_parts:
        for part in _flatten_parts(additional_parts):
            try:
                part.label
            except AttributeError:
                continue
            yield "Puzzle", part


def _default_3d_print_settings():
    """Builds a PrintSettings object from Manufacturing config for use across all 3MF objects."""

    return PrintSettings(
        enable_support=Config.Manufacturing.SLICER_3D_PRINTING_ENABLE_SUPPORT,
        support_interface_top_layers=Config.Manufacturing.SLICER_3D_PRINTING_SUPPORT_INTERFACE_TOP_LAYERS,
        support_interface_bottom_layers=Config.Manufacturing.SLICER_3D_PRINTING_SUPPORT_INTERFACE_BOTTOM_LAYERS,
        support_interface_filament=Config.Manufacturing.SLICER_3D_PRINTING_SUPPORT_INTERFACE_FILAMENT,
    )


def _export_stl_parts(
    case_parts: list[Part],
    base_parts: list[Part],
    additional_parts=None,
) -> str:
    """Exports all parts as individual STL files sorted into category subfolders."""
    export_root = os.path.join(_case_export_root(), "stl")
    folders = _create_export_folders(export_root)

    for category, part in _part_records(case_parts, base_parts, additional_parts):
        label = part.label
        export_stl(
            to_export=part,
            file_path=os.path.join(folders[category], f"{label}.stl"),
        )

    return export_root


def _mounting_point_count() -> int:
    """Returns the number of mounting points for the current case shape."""

    mapping = {
        CaseShape.SPHERE: Config.Sphere,
        CaseShape.SPHERE_WITH_FLANGE: Config.Sphere,
        CaseShape.SPHERE_WITH_FLANGE_ENCLOSED_TWO_SIDES: Config.Sphere,
        CaseShape.CYLINDER: Config.Cylinder,
    }
    case_cfg = mapping.get(Config.Puzzle.CASE_SHAPE)
    
    return case_cfg.NUMBER_OF_MOUNTING_POINTS if case_cfg else 0


def _add_mounting_objects(project, parts: list[Part], print_settings) -> None:
    """Adds mounting parts to the project with two special behaviours:

    - MOUNTING_RING_CLIP_START and START_INDICATOR are combined into one ModelObject
      so they print in place as a single unit.
    - MOUNTING_RING_CLIP_SINGLE is duplicated NUMBER_OF_MOUNTING_POINTS - 1 times
    """
    clip_start_label = CasePart.MOUNTING_RING_CLIP_START.value
    indicator_label = CasePart.START_INDICATOR.value
    clip_single_label = CasePart.MOUNTING_RING_CLIP_SINGLE.value

    by_label = {p.label: p for p in parts}
    clip_start = by_label.get(clip_start_label)
    indicator = by_label.get(indicator_label)
    clip_single = by_label.get(clip_single_label)

    special_labels = {clip_start_label, indicator_label, clip_single_label}

    for part in parts:
        if part.label not in special_labels:
            project.add_object(part, name=part.label, settings=print_settings)

    # Combine Mounting Clip Start + Start Indicator into one ModelObject.
    if clip_start is not None or indicator is not None:
        combined = [p for p in (clip_start, indicator) if p is not None]
        obj_name = clip_start_label if clip_start is not None else indicator_label
        obj = project.add_object(name=obj_name, settings=print_settings)
        for p in combined:
            obj.add_part(p, name=p.label)

    # Duplicate Mounting Clip Single for each remaining mounting point.
    if clip_single is not None:
        n_copies = _mounting_point_count() - 1
        for _ in range(n_copies):
            project.add_object(clip_single, name=clip_single_label, settings=print_settings)


def _export_3mf_parts(
    case_parts: list[Part],
    base_parts: list[Part],
    additional_parts=None,
) -> str:
    """Exports parts as per-category 3MF project files ready to slicer."""

    # Parts in these categories must remain stacked at their design positions 
    # when opened in the slicer, merging them into one a single ModelObject ensures this.
    _3MF_STACK_CATEGORIES = {"Puzzle", "Base"}

    export_root = os.path.join(_case_export_root(), "3mf")
    os.makedirs(export_root, exist_ok=True)
    print_settings = _default_3d_print_settings()

    grouped_parts: dict[str, list[Part]] = {
        "Puzzle": [],
        "Mounting": [],
        "Base": [],
    }
    for category, part in _part_records(case_parts, base_parts, additional_parts):
        if category in grouped_parts:
            grouped_parts[category].append(part)

    for category, parts in grouped_parts.items():
        if not parts:
            continue

        project = Project(
            info=ProjectInfo(
                title=category,
                designer="3D Marble Maze Generator",
                description=(
                    "Grouped model-only 3MF export"
                ),
            )
        )

        if category in _3MF_STACK_CATEGORIES:
            obj = project.add_object(name=category, settings=print_settings)
            for part in parts:
                obj.add_part(part, name=part.label)
        elif category == "Mounting":
            _add_mounting_objects(project, parts, print_settings)
        else:
            for part in parts:
                project.add_object(part, name=part.label, settings=print_settings)

        save_path = Path(export_root) / f"{category}.3mf"
        project.save(save_path, tolerance=1e-3)

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

    Returns the export root folder when exports are enabled, otherwise None.
    """
    if not Config.Manufacturing.EXPORT_STL and not Config.Manufacturing.EXPORT_3MF:
        return None

    if apply_manufacturing_preparation:
        _prepare_parts_for_manufacturing(case_parts)

    export_roots = []
    if Config.Manufacturing.EXPORT_STL:
        logger.info("Exporting STL parts to %s ...", _case_export_root())
        export_roots.append(_export_stl_parts(case_parts, base_parts, additional_parts))
    if Config.Manufacturing.EXPORT_3MF:
        logger.info("Exporting 3MF parts to %s ...", _case_export_root())
        export_roots.append(_export_3mf_parts(case_parts, base_parts, additional_parts))

    return export_roots[-1] if export_roots else None
