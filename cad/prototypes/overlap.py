from build123d import *
from ocp_vscode import show_all

# Two boxes
box1 = Box(10, 9, 10)
box2 = Box(10, 10, 10)

inter = box1 & box2
solids = inter.solids()

if not solids:
    print("No solids!")
else:
    print("Solids!")

show_all()
