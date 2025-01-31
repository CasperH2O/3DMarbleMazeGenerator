# 3D marble puzzle obstacle track generator

Software application, written in Python to generate 3D printable design files (STL) of a marble obstacle track. Inspired by puzzle balls from Perplexus, Playtastic, Intrism, Magical Intellect and Sharper Image.

<p float="left">
    <img src="resources/path_visualization.png" alt="Path Visualization" width="200"/>
    <img src="resources/3d.png" alt="3D Image" width="200"/>
    <img src="resources/physical_result.jpg" alt="Physical Result" width="200"/>
</p>

## Usage

For practicality, the application can be run in separate parts. A puzzle generation with paths and plot visualization and a 3D solid modeller that generates a puzzle and then creates and visualizes the 3D model for export. Both rely on the parameters set in the config.py file

The config.py file contains parameters that can be adjusted for type, size and shape of enclosure, path types, theme colors and more.

**Puzzle generation**

The puzzle route, for paths, curve types and node grid can be generated and visualized separately. To generate a puzzle, based on settings in the config.py file and open a visualization (Plotly-generated HTML file) in your browser, run:

```Python
generate_puzzle.py
```

Results in a HTML file which opens in the browser to showcase the enclosure shape, node grid, paths and path curve types divided by segments:

<img src="resources/path_visualization_large.png" alt="Path Visualization Large" width="400"/></p>

**Solid modeller**

The 3D shape objects, physical enclosure are generated and visualized through the solid modeller. A puzzle is generated from which the to be made physical shapes are created by running:

```Python
solid_modeller.py
```

Results in a 3D model made out of separate solid bodies for the enclosure, path, path accent, support material and a marble path indicator:

<img src="resources/3d_large.png" alt="3D Large" width="400"/>

## Requirements
Python 3.11 <= due to library dependencies

For the 3D model visualization, CQ-Editor or Visual Studio Code OCP CAD Viewer extension are recommended.

## References
- For 3D modelling, this project relies heavily on Build123: [Build123D a python CAD library]( https://github.com/gumyr/build123d)
- OCP CAD Viewer extension for Visual Studio Code to visualize 3D models: [OCP CAD Viewer for VS Code](https://github.com/bernhard-42/vscode-ocp-cad-viewer)
- Plotly for graph visualization: [Plotly Python Graphing Library](https://plotly.com/python/)
