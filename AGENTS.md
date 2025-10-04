# Agent Instructions

## Environment Setup
- This repository relies on the Build123D/OpenCascade toolchain, which requires system OpenGL libraries.
- Before running any tests or code that imports `build123d`, ensure the following packages are installed:
  ```bash
  apt-get update
  apt-get install -y libgl1-mesa-glx libglu1-mesa libegl1 libxrender1 libxi6 libxtst6
  ```
- You can verify the installation with:
  ```bash
  ldconfig -p | grep libGL
  ```
  A listed `libGL.so.1` confirms the runtime is available.

## Collaboration Conventions
- All answers, code, and code comments must be written in English.
- Unless otherwise specified, assume:
  - Python is the default programming language.
  - Plotly is the default plotting and graphing library.
  - Build123D is the default 3D modeling library.
- Do not shorten variable names to single letters (e.g., use `node`, not `n`).
- When modifying existing code, preserve any relevant comments already present in the file.

## Development Workflow Tips
- Install Python dependencies with `pip install -r requirements.txt` before running project scripts or tests.
- Run targeted tests with `pytest <path>`, e.g., `pytest tests/test_path_architect.py`.