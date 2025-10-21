# assembly/casing.py

import logging

from build123d import Part, SortBy

from cad.cases.case_model_base import CasePart
from cad.cases.case_model_box import CaseBox
from cad.cases.case_model_cylinder import CaseCylinder
from cad.cases.case_model_sphere import CaseSphere
from cad.cases.case_model_sphere_with_flange import CaseSphereWithFlange
from cad.cases.case_model_sphere_with_flange_enclosed_two_sides import (
    CaseSphereWithFlangeEnclosedTwoSides,
)
from config import CaseShape, Config
from logging_config import configure_logging

configure_logging()
logger = logging.getLogger(__name__)


def puzzle_casing():
    """
    Create the puzzle case based on the configuration and return:
      - case_parts: A dictionary of CasePart instances belonging to the case
      - base_parts: Base components associated with the case
      - cut_shape: The shape used to cut paths from the case
    """
    # Create the appropriate case based on configuration
    if Config.Puzzle.CASE_SHAPE == CaseShape.SPHERE:
        case = CaseSphere()
    elif Config.Puzzle.CASE_SHAPE == CaseShape.BOX:
        case = CaseBox()
    elif Config.Puzzle.CASE_SHAPE == CaseShape.CYLINDER:
        case = CaseCylinder()
    elif Config.Puzzle.CASE_SHAPE == CaseShape.SPHERE_WITH_FLANGE:
        case = CaseSphereWithFlange()
    elif Config.Puzzle.CASE_SHAPE == CaseShape.SPHERE_WITH_FLANGE_ENCLOSED_TWO_SIDES:
        case = CaseSphereWithFlangeEnclosedTwoSides()
    else:
        raise ValueError(
            f"Unknown CASE_SHAPE '{Config.Puzzle.CASE_SHAPE}' specified in config.py."
        )

    # Retrieve parts from the case.
    case_parts = case.get_parts()
    base_parts = case.get_base_parts()

    # Obtain the shape used to cut paths from the case
    cut_shape = case.cut_shape

    return case_parts, base_parts, cut_shape


def merge_standard_paths_with_case(
    case_parts: list[Part], standard_paths: list[Part]
) -> None:
    """
    Merge standard path solids back into the appropriate case parts when needed.
    """

    if not standard_paths:
        return

    for idx, part in enumerate(case_parts):
        # Subtract the standard path for physical bridge
        if part.label == CasePart.MOUNTING_RING.value:
            # TODO improve this, need all objects to be same type, then it should remember label and color
            label = part.label
            color = part.color

            # Subtract all paths from the mounting ring
            case_parts[idx] = case_parts[idx] - standard_paths

            # Extract and sort the solids by volume
            sorted_solids = case_parts[idx].solids().sort_by(SortBy.VOLUME)

            # Get the largest solid (last one in ascending volume sort)
            largest_solid = sorted_solids[-1]

            # Convert it to a Part
            case_parts[idx] = largest_solid
            case_parts[idx].label = label
            case_parts[idx].color = color

        # Cut internal path bridges to be flush with paths,
        # merge each flush-bridge fragment with it's respective connected path
        if part.label == CasePart.INTERNAL_PATH_BRIDGES.value:
            # Use bridge solids separate
            bridge_solids = case_parts[idx].solids()

            # Match bridge with standard path
            for bridge in bridge_solids:
                matched_sp_idx = None
                for standard_path_idx, standard_path in enumerate(standard_paths):
                    # Check overlap, can only be with one, break once found
                    overlap = standard_path & bridge
                    if overlap is None:
                        continue  # Check next combination
                    if overlap.solids():
                        matched_sp_idx = standard_path_idx
                        break

                # If we can't find a match, something went wrong
                # and bridge does not connect to path.
                # Probably a path profile at a wrong orientation
                if matched_sp_idx is None:
                    logger.warning("Unable to match bridge with standard path segment.")
                    continue

                # Subtract the standard path from the bridge, to make it flush
                # Sort by volume, as we later use the smallest of the two
                fragments = (
                    (bridge - standard_paths[matched_sp_idx])
                    .solids()
                    .sort_by(SortBy.VOLUME)
                )

                if not fragments:
                    continue  # nothing left once subtracted

                # Take the smallest remaining fragment and merge it back
                smallest_fragment = fragments[0]
                standard_paths[matched_sp_idx] = (
                    standard_paths[matched_sp_idx] + smallest_fragment
                )

            # Remove the original bridge part from case_parts,
            # since its absorbed into standard_paths
            case_parts.pop(idx)
            break
