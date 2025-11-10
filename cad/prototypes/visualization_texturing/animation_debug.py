import numpy as np
from build123d import *
from ocp_vscode import *

box1 = Box(1, 1, 1)
box1.label = "box1"
box2 = Pos(3, 0, 0) * Box(1, 1, 1)
box2.label = "box2"

show_object(box1, clear=True)
show_object(box2)

a = Animation(Part())
times = np.linspace(0, 2, 20)
rot = np.linspace(0, 360, 20)
a.add_track("/Group/box1", "rz", times, rot)

"""

red_box = Box(1, 1, 1)
red_box.label = "red_box"
red_box.color = "red"

blue_box = Pos(3, 0, 0) * Box(1, 1, 1)
blue_box.label = "blue_box"
blue_box.color = "blue"


show_object(red_box, clear=True)
show_object(blue_box)

a = Animation(Compound())  # <== empty assembly
a.paths = ["/Group/red_box"]  # <== Inject your path: validation is happy and
#     threejs doesn't care as long as the path is correct

times = np.linspace(0, 2, 20)
rot = np.linspace(0, 360, 20)
a.add_track("/Group/red_box", "rz", times, rot)

a.animate(1)
"""
