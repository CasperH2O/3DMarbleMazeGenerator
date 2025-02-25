# OSVAC M32 Adapter

from build123d import mirror, chamfer, GeomType, SortBy, Axis, BuildPart, BuildSketch, Plane, PolarLocations, Rectangle, Circle, Mode, extrude
from ocp_vscode import show_all

with BuildPart() as osvac_m32_adapter:
    with BuildSketch(Plane.XY.offset(amount=100)) as sk1:
        with PolarLocations(radius=100, count=4, start_angle=0, angular_range=360):
            Rectangle(30, 50)
    extrude(amount=25)
    with BuildSketch() as sk2:
        Circle(130)
        Circle(108, mode=Mode.SUBTRACT)
    extrude(amount=200, mode=Mode.SUBTRACT, both=True)

    chamfer(osvac_m32_adapter.edges().filter_by(Axis.Z), length=5)
    chamfer(osvac_m32_adapter.edges().filter_by(GeomType.CIRCLE).sort_by(SortBy.RADIUS)[-8:], length=5)

    mirror(about=Plane.XY)

    with BuildSketch() as sk3:
        Circle(110)
    extrude(amount=10, both=True)

    with BuildSketch() as sk3:
        Circle(95)
    extrude(amount=150, both=True)

    with BuildSketch() as sk4:
        Circle(80)
    extrude(amount=150, both=True, mode=Mode.SUBTRACT)

show_all()