import cadquery as cq
from ocp_vscode import *

result1 = cq.Workplane("front").box(2.0, 2.0, 0.5)
result2 = cq.Workplane("bottom").box(2.0, 2.0, 0.5)

show_object(result1, name="Box Alpha 1.0", options={"alpha": 1.0})
show_object(result2, name="Box Alpha 0.1", options={"alpha": 0.0})