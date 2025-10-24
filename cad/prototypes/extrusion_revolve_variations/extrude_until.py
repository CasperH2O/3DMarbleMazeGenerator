from build123d import (
    BuildPart,
    BuildSketch,
    Mode,
    Plane,
    Rectangle,
    RegularPolygon,
    Until,
    extrude,
)

top_plane = Plane.XY.offset(20)

with BuildPart():
    # Make the stop slab as a PRIVATE solid on the offset plane
    with BuildSketch(top_plane):
        Rectangle(1000, 1000)  # big enough to cover the extrusion footprint
    stop_slab = extrude(
        amount=1, mode=Mode.PRIVATE
    )  # returns a Solid, but doesn't join the part due to PRIVATE

    # Your profile on the base plane (default is Plane.XY)
    with BuildSketch():
        RegularPolygon(20, 6)

    # Extrude up to the slab
    extrude(until=Until.NEXT, target=stop_slab)
