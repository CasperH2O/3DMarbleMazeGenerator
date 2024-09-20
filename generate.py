import numpy as np
import random
import heapq
import matplotlib.pyplot as plt

# Define the Node class with the new 'start' and 'end' properties
class Node:
    def __init__(self, x, y, z, occupied=False):
        self.x = x
        self.y = y
        self.z = z
        self.occupied = occupied
        self.waypoint = False  # Waypoint property
        self.start = False  # Start property
        self.end = False  # End property
        self.mounting = False  # Mounting property
        self.parent = None  # For path reconstruction
        self.g = float('inf')  # Cost from start to this node
        self.h = 0  # Heuristic cost to goal
        self.f = float('inf')  # Total cost

    def __repr__(self):
        return (f"Node(x={self.x}, y={self.y}, z={self.z}, "
                f"occupied={self.occupied}, waypoint={self.waypoint}, start={self.start}, end={self.end})")

    def __lt__(self, other):
        return self.f < other.f  # For priority queue (heapq)


class Puzzle:
    def __init__(self, diameter, shell_thickness, node_size, seed):
        self.diameter = diameter
        self.shell_thickness = shell_thickness
        self.node_size = node_size
        self.seed = seed

        # Calculate inner radius and effective radius
        self.inner_radius = (self.diameter / 2) - self.shell_thickness
        cube_half_diagonal = (self.node_size * np.sqrt(3)) / 2
        self.effective_radius = self.inner_radius - cube_half_diagonal

        # Initialize the nodes and node dictionary
        self.nodes = []
        self.node_dict = {}
        self.generate_nodes()

    def generate_nodes(self):
        # Generate nodes within the sphere centered at (0, 0, 0)
        nodes = []
        node_size = self.node_size
        effective_radius = self.effective_radius

        # Number of cubes along one axis
        num_cubes_along_axis = int(np.floor(2 * effective_radius / node_size))
        # Adjust num_cubes_along_axis to be odd
        if num_cubes_along_axis % 2 == 0:
            num_cubes_along_axis += 1

        # Start position to center the cubes
        start_pos = -(num_cubes_along_axis // 2) * node_size

        x_values = [start_pos + i * node_size for i in range(num_cubes_along_axis)]
        y_values = x_values
        z_values = x_values

        for x in x_values:
            for y in y_values:
                for z in z_values:
                    distance = np.sqrt(x ** 2 + y ** 2 + z ** 2)
                    if distance <= effective_radius:
                        node = Node(x, y, z)
                        nodes.append(node)

        self.nodes = nodes
        self.node_dict = {(node.x, node.y, node.z): node for node in self.nodes}

    # Method to define "mounting" waypoints along the circumference and select home
    def define_mounting_waypoints(self):
        random.seed(self.seed)

        # Determine the number of mounting waypoints (between 2 and 4)
        num_mounting_waypoints = random.randint(3, 5)

        # Get the outer radius at Z = 0
        outer_radius = self.inner_radius

        # Calculate the angle between waypoints
        angle_increment = 2 * np.pi / num_mounting_waypoints

        mounting_nodes = []

        for i in range(num_mounting_waypoints):
            angle = i * angle_increment + np.pi  # Start from angle π (180 degrees)

            # Calculate the (x, y) coordinates for this mounting node
            x = outer_radius * np.cos(angle)
            y = outer_radius * np.sin(angle)

            # Find the nearest unoccupied node at Z = 0
            nearest_node = min(
                (node for node in self.nodes if node.z == 0 and not node.occupied and node not in mounting_nodes),
                key=lambda node: np.sqrt((node.x - x) ** 2 + (node.y - y) ** 2)
            )
            nearest_node.mounting = True
            nearest_node.waypoint = True  # Mark as a waypoint to include in pathfinding

            # Set the 'start' property to True for the first mounting waypoint
            if i == 0:
                nearest_node.start = True

            mounting_nodes.append(nearest_node)

        print(f"Defined {len(mounting_nodes)} mounting waypoints: {mounting_nodes}")
        return mounting_nodes

    def randomly_occupy_nodes(self, min_percentage=0, max_percentage=0):
        # Fill puzzle with obstacles for route
        random.seed(self.seed)

        percentage_to_occupy = random.randint(min_percentage, max_percentage)
        print(f"Percentage to occupy: {percentage_to_occupy}%")

        num_cubes_to_occupy = int(len(self.nodes) * (percentage_to_occupy / 100))

        print(f"Number of nodes to occupy: {num_cubes_to_occupy}")
        print(f"Total number of nodes: {len(self.nodes)}")

        occupied_nodes = random.sample(self.nodes, num_cubes_to_occupy)
        for node in occupied_nodes:
            node.occupied = True

    def randomly_select_waypoints(self, num_waypoints=5, num_candidates=10):
        # Select unoccupied nodes
        unoccupied_nodes = [node for node in self.nodes if not node.occupied]
        if len(unoccupied_nodes) < num_waypoints:
            num_waypoints = len(unoccupied_nodes)
            print(f"Reduced number of waypoints to {num_waypoints} due to limited unoccupied nodes.")

        random.seed(self.seed)
        np.random.seed(self.seed)

        waypoints = []
        for _ in range(num_waypoints):
            # Generate candidates
            candidates = random.sample(unoccupied_nodes, min(num_candidates, len(unoccupied_nodes)))

            # Evaluate each candidate
            best_candidate = None
            max_min_dist = -1
            for candidate in candidates:
                candidate_pos = np.array([candidate.x, candidate.y, candidate.z])

                if not waypoints:
                    # If no waypoints yet, any candidate is acceptable
                    min_dist = float('inf')
                else:
                    # Compute distances to existing waypoints
                    dists = [
                        np.linalg.norm(candidate_pos - np.array([wp.x, wp.y, wp.z]))
                        for wp in waypoints
                    ]
                    min_dist = min(dists)

                # Select candidate with maximum minimum distance
                if min_dist > max_min_dist:
                    max_min_dist = min_dist
                    best_candidate = candidate

            # Mark the best candidate as a waypoint
            best_candidate.waypoint = True
            waypoints.append(best_candidate)
            unoccupied_nodes.remove(best_candidate)

        print(f"Selected {num_waypoints} waypoints using Mitchell's Best-Candidate Algorithm.")

    def reset_nodes(self):
        for node in self.nodes:
            node.g = float('inf')
            node.h = 0
            node.f = float('inf')
            node.parent = None

    def get_neighbors(self, node):
        neighbors = []
        node_size = self.node_size
        directions = [
            (node_size, 0, 0), (-node_size, 0, 0),
            (0, node_size, 0), (0, -node_size, 0),
            (0, 0, node_size), (0, 0, -node_size)
        ]
        for dx, dy, dz in directions:
            neighbor_coords = (node.x + dx, node.y + dy, node.z + dz)
            neighbor = self.node_dict.get(neighbor_coords)
            if neighbor and not neighbor.occupied:
                neighbors.append(neighbor)
        return neighbors

    def manhattan_distance(self, node_a, node_b):
        return (abs(node_a.x - node_b.x) +
                abs(node_a.y - node_b.y) +
                abs(node_a.z - node_b.z))

    def a_star(self, start_node, goal_node):
        open_set = []
        heapq.heappush(open_set, (start_node.f, start_node))
        closed_set = set()

        start_node.g = 0
        start_node.h = self.manhattan_distance(start_node, goal_node)
        start_node.f = start_node.h

        while open_set:
            current_f, current_node = heapq.heappop(open_set)
            if current_node == goal_node:
                return self.reconstruct_path(current_node)

            closed_set.add(current_node)

            for neighbor in self.get_neighbors(current_node):
                if neighbor in closed_set:
                    continue

                tentative_g = current_node.g + self.node_size

                if tentative_g < neighbor.g:
                    neighbor.parent = current_node
                    neighbor.g = tentative_g
                    neighbor.h = self.manhattan_distance(neighbor, goal_node)
                    neighbor.f = neighbor.g + neighbor.h

                    in_open_set = any(neighbor == item[1] for item in open_set)
                    if not in_open_set:
                        heapq.heappush(open_set, (neighbor.f, neighbor))

        return None  # Path not found

    def reconstruct_path(self, current_node):
        path = []
        while current_node:
            path.append(current_node)
            current_node = current_node.parent
        path.reverse()
        return path

    def occupy_path(self, path):
        for node in path:
            node.occupied = True
            node.g = float('inf')
            node.h = 0
            node.f = float('inf')
            node.parent = None

    def euclidean_distance(self, node_a, node_b):
        return np.sqrt((node_a.x - node_b.x) ** 2 +
                       (node_a.y - node_b.y) ** 2 +
                       (node_a.z - node_b.z) ** 2)

    def find_nearest_waypoint(self, current_node, unvisited_waypoints):
        # Sort unvisited waypoints by Euclidean distance
        unvisited_waypoints.sort(key=lambda node: self.euclidean_distance(current_node, node))
        for waypoint in unvisited_waypoints:
            self.reset_nodes()
            path = self.a_star(current_node, waypoint)
            if path:
                return waypoint, path
        return None, None

    def connect_waypoints(self):
        waypoints = [node for node in self.nodes if node.waypoint]
        if not waypoints:
            print("No waypoints to connect.")
            return []

        # Ensure the start node is the first node in the route
        start_node = next((node for node in self.nodes if node.start), None)
        if start_node:
            current_node = start_node
            waypoints.remove(start_node)  # Remove start node from waypoints if present
        else:
            # If no start node is set, use the first waypoint
            current_node = waypoints.pop(0)

        total_path = []

        first_iteration = True  # Flag to handle the first path differently

        while waypoints:
            next_waypoint, path = self.find_nearest_waypoint(current_node, waypoints)
            if next_waypoint and path:
                self.occupy_path(path)
                if first_iteration:
                    total_path.extend(path)
                    first_iteration = False
                else:
                    # Skip the first node to prevent duplication
                    total_path.extend(path[1:])
                waypoints.remove(next_waypoint)
                current_node = next_waypoint
            else:
                print("No more reachable waypoints.")
                break

        # Set the last node in the path as the end node
        if total_path:
            end_node = total_path[-1]
            end_node.end = True
            print(f"End node set at: {end_node}")

        # Print the path
        print("pts =", [(node.x, node.y, node.z) for node in total_path])

        return total_path

    # Method to set the start node at z=0, y=0, and lowest possible x
    def set_start_node(self):
        # Filter nodes where z=0 and y=0
        potential_start_nodes = [node for node in self.nodes if node.z == 0 and node.y == 0 and not node.occupied]

        # Check if any valid nodes exist at z=0 and y=0
        if not potential_start_nodes:
            print("No valid nodes available at z=0, y=0.")
            return None

        # Find the node with the lowest x-coordinate
        start_node = min(potential_start_nodes, key=lambda node: node.x)

        # Mark this node as the start node
        start_node.start = True
        start_node.waypoint = True  # It's also a waypoint

        print(f"Start node set at: {start_node}")
        return start_node

    # Visualize method
    def visualize_nodes_and_paths(self, total_path):
        fig = plt.figure()
        ax = fig.add_subplot(111, projection='3d')

        # Plot all nodes
        xs = [node.x for node in self.nodes]
        ys = [node.y for node in self.nodes]
        zs = [node.z for node in self.nodes]

        # Determine colors and sized based on node properties
        colors = []
        sizes = []
        for node in self.nodes:
            if node.start:
                colors.append('yellow')  # Start node
                sizes.append(40)
            elif node.end:
                colors.append('orange')  # End node
                sizes.append(40)
            elif node.mounting:
                colors.append('purple')  # Mounting nodes
                sizes.append(30)
            elif node.waypoint:
                colors.append('blue')  # Waypoints
                sizes.append(20)
            elif node.occupied:
                colors.append('red')  # Occupied nodes
                sizes.append(20)
            else:
                colors.append('green')  # Unoccupied nodes
                sizes.append(1)  # Smaller size for unoccupied nodes

        ax.scatter(xs, ys, zs, c=colors, marker='o', s=sizes)

        # Plot the path
        if total_path:
            path_xs = [node.x for node in total_path]
            path_ys = [node.y for node in total_path]
            path_zs = [node.z for node in total_path]
            ax.plot(path_xs, path_ys, path_zs, color='black', linewidth=0.75)

        # Plot the inner circle in the XY plane (z = 0)
        theta = np.linspace(0, 2 * np.pi, 100)
        x_circle_xy = self.inner_radius * np.cos(theta)
        y_circle_xy = self.inner_radius * np.sin(theta)
        z_circle_xy = np.zeros_like(theta)
        ax.plot(x_circle_xy, y_circle_xy, z_circle_xy, color='cyan', label='Inner Circle (XY plane)')

        # Plot the inner circle in the ZY plane (x = 0)
        y_circle_zy = self.inner_radius * np.cos(theta)
        z_circle_zy = self.inner_radius * np.sin(theta)
        x_circle_zy = np.zeros_like(theta)
        ax.plot(x_circle_zy, y_circle_zy, z_circle_zy, color='magenta', label='Inner Circle (ZY plane)')

        # Set axis labels
        ax.set_xlabel('X axis')
        ax.set_ylabel('Y axis')
        ax.set_zlabel('Z axis')

        plt.show()


if __name__ == "__main__":
    diameter = 100  # Diameter of the sphere in mm
    shell_thickness = 3  # Thickness of the shell in mm
    node_size = 10  # Node size in mm
    seed = 42  # Random seed

    # Create a Puzzle instance
    puzzle = Puzzle(diameter=diameter, shell_thickness=shell_thickness, node_size=node_size, seed=seed)

    # Define mounting waypoints and home
    mounting_nodes = puzzle.define_mounting_waypoints()

    # Randomly occupy nodes within the sphere as obstacles
    puzzle.randomly_occupy_nodes(min_percentage=0, max_percentage=0)

    # Randomly select waypoints
    puzzle.randomly_select_waypoints(num_waypoints=1)

    # Reset the nodes before pathfinding
    puzzle.reset_nodes()

    # Connect the waypoints
    total_path = puzzle.connect_waypoints()

    if total_path:
        print(f"Total path length: {len(total_path)}")
        # Visualize the nodes and the path
        puzzle.visualize_nodes_and_paths(total_path)
    else:
        print("No path could be constructed to connect all waypoints.")
