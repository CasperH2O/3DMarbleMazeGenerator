from build123d import Line 
from ocp_vscode import show_all

# Define two lines
l1 = Line((-10, -2), (10, -2))   # Horizontal line
l2 = Line((2, -10), (2, 10))   # Vertical line

# Find intersection using `intersect`
intersection_point = l1.intersect(l2)

# Print the intersection point (if found)
if intersection_point:
    print("Intersection Point:", (intersection_point.X, intersection_point.Y))
else:
    print("No intersection found")

show_all()