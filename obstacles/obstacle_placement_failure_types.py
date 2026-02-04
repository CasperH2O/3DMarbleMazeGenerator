# obstacles/obstacle_placement_failure_types.py

from enum import Enum


class ObstaclePlacementFailureType(Enum):
    """
    Enum representing the different types of obstacle placement failures.
    """

    OUTSIDE_GRID = "outside_grid"
    OCCUPIED_VS_OCCUPIED = "occupied_vs_occupied"
    OCCUPIED_VS_OVERLAP = "occupied_vs_overlap"
    OVERLAP_VS_OCCUPIED = "overlap_vs_occupied"

    def get_color(self) -> str:
        """
        Returns the visualization color hex code for this failure type.
        """
        colors = {
            self.OUTSIDE_GRID: "#FF0000",  # Red
            self.OCCUPIED_VS_OCCUPIED: "#FF4444",  # Red
            self.OCCUPIED_VS_OVERLAP: "#FF8C00",  # Orange
            self.OVERLAP_VS_OCCUPIED: "#FFD700",  # Gold
        }
        return colors.get(self, "#888888")  # Gray fallback

    def get_label(self) -> str:
        """
        Returns the human-readable label for this failure type.
        """
        labels = {
            self.OUTSIDE_GRID: "Outside Grid Boundary",
            self.OCCUPIED_VS_OCCUPIED: "Collision with Obstacle",
            self.OCCUPIED_VS_OVERLAP: "Collision with Overlap Zone",
            self.OVERLAP_VS_OCCUPIED: "Overlap Collision",
        }
        return labels.get(self, "Unknown Failure")
