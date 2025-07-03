from build123d import *
from ocp_vscode import *
a = import_svg('cad/prototypes/wood-grain-texture-6830.svg')

with BuildPart() as p:
    with Locations((218.5082668151336,170.6107028629496)): #from bbox
        Box(2191.9917332848663,1716.5643332169068,50,align=(Align.MIN,Align.MIN,Align.MAX))
    with BuildSketch() as s:
        add(a)
    extrude(amount=1)

show(p)