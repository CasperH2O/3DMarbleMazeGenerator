import random

import plotly.graph_objects as go


def main() -> None:
    # Experiment to place nodes, and visualize a cube grid with adjacent nodes

    # Generate full grid 0,10,...,100 in each axis
    spacing = 10
    coords = list(range(0, 101, spacing))
    all_nodes = [(x, y, z) for x in coords for y in coords for z in coords]

    # Define hardcoded nodes and pick 3 extra random nodes
    hardcoded_nodes = {
        (50, 20, 20),
        (50, 20, 30),
        (50, 20, 40),
        (50, 30, 40),
        (50, 40, 40),
    }
    random.seed()
    remaining = list(set(all_nodes) - hardcoded_nodes)
    random_nodes = set(random.sample(remaining, 3))

    # Combine into final node set
    nodes = hardcoded_nodes.union(random_nodes)

    # Build shell: all cardinal neighbors of nodes, within grid, excluding nodes
    shell_offsets = [
        (spacing, 0, 0),
        (-spacing, 0, 0),
        (0, spacing, 0),
        (0, -spacing, 0),
        (0, 0, spacing),
        (0, 0, -spacing),
    ]
    shell_nodes = set()
    for sx, sy, sz in nodes:
        for dx, dy, dz in shell_offsets:
            nb = (sx + dx, sy + dy, sz + dz)
            if nb in all_nodes and nb not in nodes:
                shell_nodes.add(nb)

    # Prepare cube geometry
    d = spacing / 2
    offsets = [(dx, dy, dz) for dx in (-d, d) for dy in (-d, d) for dz in (-d, d)]
    edges = [
        (0, 1),
        (0, 2),
        (0, 4),
        (1, 3),
        (1, 5),
        (2, 3),
        (2, 6),
        (3, 7),
        (4, 5),
        (4, 6),
        (5, 7),
        (6, 7),
    ]

    fig = go.Figure()

    # Draw shell cubes first (thin, semi-transparent green)
    for cx, cy, cz in shell_nodes:
        verts = [(cx + dx, cy + dy, cz + dz) for dx, dy, dz in offsets]
        for i, j in edges:
            x0, y0, z0 = verts[i]
            x1, y1, z1 = verts[j]
            fig.add_trace(
                go.Scatter3d(
                    x=[x0, x1],
                    y=[y0, y1],
                    z=[z0, z1],
                    mode="lines",
                    line=dict(width=2, color="green"),
                    opacity=0.4,
                    showlegend=False,
                )
            )

    # Draw node cubes on top (thick, opaque red)
    for cx, cy, cz in nodes:
        verts = [(cx + dx, cy + dy, cz + dz) for dx, dy, dz in offsets]
        for i, j in edges:
            x0, y0, z0 = verts[i]
            x1, y1, z1 = verts[j]
            fig.add_trace(
                go.Scatter3d(
                    x=[x0, x1],
                    y=[y0, y1],
                    z=[z0, z1],
                    mode="lines",
                    line=dict(width=3, color="red"),
                    opacity=1.0,
                    showlegend=False,
                )
            )

    # Plot node centers
    # shell markers
    if nodes:
        bx, by, bz = zip(*nodes)
        fig.add_trace(
            go.Scatter3d(
                x=bx,
                y=by,
                z=bz,
                mode="markers",
                marker=dict(size=3, color="green"),
                name="Shell",
            )
        )
    # node markers
    if nodes:
        sx, sy, sz = zip(*nodes)
        fig.add_trace(
            go.Scatter3d(
                x=sx,
                y=sy,
                z=sz,
                mode="markers",
                marker=dict(size=5, color="red"),
                name="Seeds",
            )
        )

    # Layout with true data aspect ratio
    fig.update_layout(
        scene=dict(
            xaxis_title="X", yaxis_title="Y", zaxis_title="Z", aspectmode="data"
        ),
        title="3D Grid: Nodes (red) & Shell (green)",
        margin=dict(l=0, r=0, t=50, b=0),
    )

    # Show immediately
    fig.show()


if __name__ == "__main__":
    main()
