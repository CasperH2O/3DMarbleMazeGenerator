# cad/cases/case_parts.py

from dataclasses import dataclass


# Data class to hold information about each part of the puzzle casing
@dataclass
class CasePart:
    name: str       # Name of the part
    obj: any        # The CAD object
    options: dict   # Display options (e.g., color, transparency, etc.)
