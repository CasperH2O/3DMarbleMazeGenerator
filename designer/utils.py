from pathlib import Path


def _clamp(value: int, minimum: int, maximum: int) -> int:
    return max(minimum, min(value, maximum))


def _load_stl_files(export_root: str | Path) -> list[Path]:
    root_path = Path(export_root)
    if not root_path.exists():
        return []
    return sorted(root_path.rglob("*.stl"))
