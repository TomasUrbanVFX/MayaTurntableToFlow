# Maya Turntable to Flow

## About
Renders a turntable animation of an asset in Maya and uploads it to Flow Production Tracking
-> a fast and streamlined method for sending assets for internal review.

A video demonstration: *To Be Added*

## Features
- Exports selected objects to a new scene and fits them into view
- Renders a turntable animation on the background via a subprocess 
- Full Arnold render with materials
- Creates a video preview with FFmpeg
- Displays all available Projects, Asset libraries and Assets from Flow
- Uploads a new version with the preview video to the selected asset

## Requirements
- **Autodesk Maya** (tested on 2026)
- **Arnold**
- Python packages: **shotgun-api3**, **Pyside6**
- **FFmpeg** installed and in PATH

## Instalation
1) Paste all files into a new directory

2) Fill out id_config.py with your Flow credentials

3) Paste this code into Maya's Python console and create a shelf tool:

```
import importlib
import sys
sys.path.append("path/to/your/folder/containing/the/scripts")
    
import maya_turntable_to_flow as cg
importlib.reload(cg)
```
4) Run the script!

