# path_profiles_overview.py

from build123d import (
    BuildLine,
    BuildPart,
    BuildSketch,
    Polyline,
    add,
    sweep,
)
from ocp_vscode import Camera, set_defaults, show_object

import config
from cad.path_profile_type_shapes import (
    ACCENT_REGISTRY,
    PROFILE_TYPE_FUNCTIONS,
    SUPPORT_REGISTRY,
    PathProfileType,
)


def get_params(pt: PathProfileType) -> tuple[dict, bool]:
    """Return (params, missing) for this profile type."""
    params = config.Path.PATH_PROFILE_TYPE_PARAMETERS.get(pt.value, {})
    return params, len(params) == 0


def pick_colour(pt: PathProfileType, missing: bool) -> str:
    """Colour priority: red if parameters missing, else role colour."""
    if missing:
        return ERROR_COLOR
    if pt in ACCENT_TYPES:
        return config.Puzzle.PATH_ACCENT_COLOR
    if pt in SUPPORT_TYPES:
        return config.Puzzle.SUPPORT_MATERIAL_COLOR
    return config.Puzzle.PATH_COLORS[0]


def sweep_single_section_profile(profile_sketch, path_wire, label=None, color=None):
    """Sweep one closed Sketch along a one-section path."""
    with BuildPart() as result:
        with BuildLine():
            add(path_wire)
        with BuildSketch(path_wire ^ 0):
            add(profile_sketch)
        sweep()
    if label:
        result.part.label = label
    if color:
        result.part.color = color
    show_object(result, name=result.part.label)


# Constants
ERROR_COLOR = "#FF1A1AFF"
ACCENT_TYPES = set(ACCENT_REGISTRY.values())
SUPPORT_TYPES = set(SUPPORT_REGISTRY.values())

# Layout parameters
NODE_SIZE = config.Puzzle.NODE_SIZE  # spacing grid
PATH_LEN = NODE_SIZE * 8  # Y-length of every demo path
X_SPACING = NODE_SIZE * 2  # gap between neighbouring paths

# Set the default camera position, to not adjust on new show
set_defaults(reset_camera=Camera.KEEP)

# Iterate over every registered profile type, sweep it main profile and accent and or support if applicable
for idx, profile_type in enumerate(PathProfileType):
    # Build the path (straight polyline along Y+), use spacing
    x_offset = idx * X_SPACING
    path = Polyline(
        (x_offset, 0, 0),
        (x_offset, PATH_LEN, 0),
    )

    # Main profile
    params_main, missing_main = get_params(profile_type)
    profile_func = PROFILE_TYPE_FUNCTIONS[profile_type]
    main_sketch = profile_func(**params_main, rotation_angle=-90)

    sweep_single_section_profile(
        main_sketch,
        path,
        label=f"{profile_type.value} - main",
        color=pick_colour(profile_type, missing_main),
    )

    # Accent profile (if any)
    accent_type = ACCENT_REGISTRY.get(profile_type)
    if accent_type:
        params_acc, missing_acc = get_params(accent_type)
        accent_func = PROFILE_TYPE_FUNCTIONS[accent_type]
        accent_sk = accent_func(**params_acc, rotation_angle=-90)

        sweep_single_section_profile(
            accent_sk,
            path,
            label=f"{profile_type.value} - accent",
            color=pick_colour(accent_type, missing_acc),
        )

    # Support profile (if any)
    support_type = SUPPORT_REGISTRY.get(profile_type)
    if support_type:
        params_sup, missing_sup = get_params(support_type)
        support_func = PROFILE_TYPE_FUNCTIONS[support_type]
        support_sk = support_func(**params_sup, rotation_angle=-90)

        sweep_single_section_profile(
            support_sk,
            path,
            label=f"{profile_type.value} - support",
            color=pick_colour(support_type, missing_sup),
        )
