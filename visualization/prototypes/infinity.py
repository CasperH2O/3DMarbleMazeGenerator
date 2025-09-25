import numpy as np
import plotly.graph_objects as go

# Generate parameter t
t = np.linspace(0, 2 * np.pi, 100)

# Modified lemniscate of Bernoulli for infinity symbol
x = np.cos(t) / (1 + np.sin(t) ** 2)
y = (np.sin(t) * np.cos(t)) / (1 + np.sin(t) ** 2)

# Apply scaling to spread the arms more evenly
x_scaled = 2 * x
y_scaled = 2 * y

# Combine into Nx2 array
points = np.column_stack((x_scaled, y_scaled))

# Cut infinity symbol in half: keep points where x <= 0
filtered_points = points[points[:, 0] <= 0]

# Apply 2D rotation matrix for 45° CCW
theta = np.pi / 4  # 45 degrees in radians
rotation_matrix = np.array(
    [[np.cos(theta), -np.sin(theta)], [np.sin(theta), np.cos(theta)]]
)
rotated_points = filtered_points @ rotation_matrix.T

# Apply easing function to Z values
t_ease = np.linspace(0, 1, len(rotated_points))
z = (1 - np.cos(np.pi * t_ease)) / 2  # sine-based ease-in/ease-out

# Combine into 3D points
points_3d = np.column_stack((rotated_points, z))

# Plot the transformed points in 3D using Plotly
fig = go.Figure(
    data=go.Scatter3d(
        x=points_3d[:, 0],
        y=points_3d[:, 1],
        z=points_3d[:, 2],
        mode="lines",
        line=dict(color="purple", width=6),
    )
)

fig.update_layout(
    title="Half Infinity Symbol with Eased Z Gradient",
    scene=dict(xaxis_title="X", yaxis_title="Y", zaxis_title="Z", aspectmode="auto"),
    margin=dict(l=0, r=0, b=0, t=40),
)

fig.show()

# Print first 10 points for verification
print("First 10 eased 3D points:")
print(points_3d[:10])
