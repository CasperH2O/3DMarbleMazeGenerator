from build123d import *
from ocp_vscode import show

# Create a base part (e.g., a block)
with BuildPart() as part:
    Box(20, 20, 10)

    # Subtract a tapered hole (cone)
    with Locations((0, 0, 5)):  # Position at center of block
        CounterSinkHole(radius=3, counter_sink_radius=5, depth=6, counter_sink_angle=80, mode=Mode.SUBTRACT)

show(part)
