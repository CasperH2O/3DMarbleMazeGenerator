from build123d import * 
from ocp_vscode import show_all

width = 30
length = 10
extrude_up = 5
extrude_down = 2

with BuildPart() as leg_1:
    with BuildSketch() as rectangle_sketch:
        Rectangle(width=width, height=length)
    extrude(amount=extrude_up)
    extrude(amount=-extrude_down)

show_all()