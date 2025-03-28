from build123d import *
from ocp_vscode import show_all

shape1 = Circle(radius=10)
shape2 = Circle(radius=10)

def areEqual(a,b):
    return (a - b).area + (b - a).area == 0.0

if areEqual(shape1,shape2):
    print(f"Same")
else:
    print(f"Not the same")

shape3 = Rectangle(10, 20)
shape4 = Rectangle(10, 20)

if shape3.is_equal(shape4):
    print(f"Equal")
else:
    print(f"Not equal")

shape5 = Box(10, 20, 30)
shape6 = Box(10, 20, 30)

if shape5 == shape6:
    print(f"Same")
else:
    print(f"Not the same")

show_all()