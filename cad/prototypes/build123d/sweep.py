from build123d import *
from ocp_vscode import *

length_width = 40.0

with BuildPart() as hook_part:
    with BuildLine() as hook:
        line_1 = Polyline([(0,20.0),(20.0,20.0),(20.0,0)])
    with BuildSketch(line_1 ^ 0) as b3:
        Rectangle(length_width,length_width)
    sweep(transition=Transition.ROUND)

show_object(hook_part)

print(hook_part.part.is_valid())
print(hook_part.part.is_manifold) # Holds water?