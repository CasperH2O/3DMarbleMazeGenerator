from typing import Any

from config import Config


def _color_to_rgb(color: Any) -> tuple[float, float, float]:
    if isinstance(color, str) and color.startswith("#"):
        hex_value = color.lstrip("#")
        if len(hex_value) in {6, 8}:
            r = int(hex_value[0:2], 16) / 255
            g = int(hex_value[2:4], 16) / 255
            b = int(hex_value[4:6], 16) / 255
            return (r, g, b)

    if hasattr(color, "r") and hasattr(color, "g") and hasattr(color, "b"):
        return (float(color.r), float(color.g), float(color.b))

    if isinstance(color, (tuple, list)) and len(color) >= 3:
        return tuple(float(component) for component in color[:3])  # type: ignore[misc]

    return (0.7, 0.7, 0.7)


def _color_from_mesh_name(name: str) -> tuple[float, float, float]:
    name_lower = name.lower()

    if name_lower.startswith("standard path"):
        try:
            index = int(name_lower.split("standard path")[-1]) - 1
        except ValueError:
            index = 0
        colors = Config.Puzzle.PATH_COLORS
        return _color_to_rgb(colors[index % len(colors)])

    if "support path" in name_lower:
        return _color_to_rgb(Config.Puzzle.SUPPORT_MATERIAL_COLOR)

    if "accent color path" in name_lower:
        return _color_to_rgb(Config.Puzzle.PATH_ACCENT_COLOR)

    if "mounting ring" in name_lower or "mounting clip" in name_lower:
        return _color_to_rgb(Config.Puzzle.MOUNTING_RING_COLOR)

    if "path bridges" in name_lower:
        return _color_to_rgb(Config.Puzzle.PATH_COLORS[0])

    if name_lower.startswith("base top"):
        return _color_to_rgb(Config.Puzzle.PATH_COLORS[0])

    if name_lower.startswith("base bottom"):
        return _color_to_rgb(Config.Puzzle.MOUNTING_RING_COLOR)

    if name_lower.startswith("base edge"):
        return _color_to_rgb(Config.Puzzle.PATH_ACCENT_COLOR)

    if "base" in name_lower:
        return _color_to_rgb(Config.Puzzle.PATH_COLORS[0])

    if "case" in name_lower or "casing" in name_lower or "dome" in name_lower:
        return _color_to_rgb(Config.Puzzle.TRANSPARENT_CASE_COLOR)

    return _color_to_rgb(Config.Puzzle.PATH_COLORS[0])
