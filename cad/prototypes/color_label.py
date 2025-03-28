from build123d import Box, Cylinder, Part, Color, Pos
from ocp_vscode import show


b = Box(3, 1, 1)
b.label = "A box"
b.color = Color("Blue")

c = Cylinder(1, 2)
c.label = "A cylinder"
c.color = Color("Cyan")

sub = b - c
print(f"{sub.label=}, {sub.color=}")

sub_part = Part(b - c)
print(f"{sub_part.label=}")

sub_part2 = Part() + [b - c]
print(f"{sub_part2.label=}")

show(b, Pos(Z=2) * c, Pos(Y=2) * sub)
