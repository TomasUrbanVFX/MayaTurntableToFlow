from maya import standalone
standalone.initialize()

from maya import cmds
from mtoa import utils as mutils

import json, sys


def load_file(maya_file_to_open:str):
    # Open file
    cmds.file(maya_file_to_open, open=True)
    print(f"Loaded: {cmds.ls(geometry=True)}")


def create_turntable_group():
    # Get all props
    meshes = cmds.ls(type='mesh', noIntermediate=True)

    # Get their parent transforms
    props_to_render = cmds.listRelatives(meshes, parent=True, fullPath=True)
    print(props_to_render)

    # Create turntable group
    turntable_group = cmds.group(em=True, name="turntable_group")

    # Add all props into the group
    for prop in props_to_render:
        cmds.parent(prop, turntable_group)


def create_render_camera():
    # Create camera
    cam = cmds.camera(name="turntable_render_cam")
    cam_shape = cam[1]

    # Move camera
    cmds.viewPlace(cam_shape, eye=(24.5,4,0), lookAt=(0,0,0))


def create_dome_light():
    mutils.createLocator("aiSkyDomeLight", asLight=True)


def fit_view_to_asset():
    group_name = "turntable_group"
    camera_name = 'turntable_render_cam1'

    # Get the bounding box of the group
    bbox = cmds.exactWorldBoundingBox(group_name)
    # bbox returns [xmin, ymin, zmin, xmax, ymax, zmax]

    # Calculate the center of the bounding box
    center_x = (bbox[0] + bbox[3]) / 2.0
    center_y = (bbox[1] + bbox[4]) / 2.0
    center_z = (bbox[2] + bbox[5]) / 2.0

    # Move the group so its center is at origin
    cmds.move(-center_x, -center_y, -center_z, group_name, relative=True)

    # Move the pivot to world origin (0,0,0)
    cmds.xform(group_name, pivots=[0, 0, 0], worldSpace=True)

    # Frame the object in the camera view
    cmds.select(group_name)
    cmds.viewFit(camera_name, fitFactor=0.5)  # Adjust fitFactor for tighter/looser framing

    print(f"Centered {group_name} at origin and framed in {camera_name}")


def rotation_animation(end_frame:int):
    # Set initial keyframe
    time = 0
    value = 0
    cmds.setKeyframe("turntable_group.rotateY", time=time, value=value, itt="linear", ott="linear")

    # Set final keyframe (full rotation)
    time = end_frame
    value = 360
    cmds.setKeyframe("turntable_group.rotateY", time=time, value=value, itt="linear", ott="linear")


def set_render_settings(end_frame:int):
    # Set frame range and fps
    cmds.playbackOptions(minTime=0, maxTime=end_frame, framesPerSecond=25)
    cmds.setAttr('defaultRenderGlobals.animationRange', 0)
    cmds.setAttr('defaultRenderGlobals.startFrame', 0)
    cmds.setAttr('defaultRenderGlobals.endFrame', end_frame)

    # Set resolution
    cmds.setAttr('defaultResolution.width', 1920)
    cmds.setAttr('defaultResolution.height', 1080)
    cmds.setAttr('defaultResolution.deviceAspectRatio', 1920/1080)

    # Set export format
    cmds.setAttr('defaultArnoldDriver.aiTranslator', "png", type='string')

    # Set color space - safer method
    cmds.colorManagementPrefs(e=True, cmEnabled=True)

    # Arnold driver color management (this is the important one for output)
    cmds.setAttr("defaultArnoldDriver.colorManagement", 1)

    # Try to set color space attribute if it exists
    if cmds.attributeQuery("colorSpace", node="defaultArnoldDriver", exists=True):
        cmds.setAttr("defaultArnoldDriver.colorSpace", "sRGB", type="string")


def arnold_render(end_frame: int, folder: str, name: str):
    for frame in range(0, end_frame+1):
        cmds.currentTime(frame)

        save_filename = folder + name + "_" + str(frame).zfill(4)
        cmds.setAttr("defaultRenderGlobals.imageFilePrefix", save_filename, type="string")

        cmds.arnoldRender(batch=True, camera="turntable_render_cam1")
        print(f"Rendered frame: {frame} / {end_frame}")



with open(sys.argv[1], "r") as f:
    config = json.load(f)

# Variables
save_folder  = config["save_folder"]
assets_file  = config["assets_file"]
print(f"Save tempdir: {save_folder}")
print(f"Loading file: {assets_file}")

render_duration = 72 # Duration of one turntable turn in frames
image_name = r"\\turntable_image"

# File setup
load_file(assets_file)
create_turntable_group()
create_render_camera()
create_dome_light()
fit_view_to_asset()
rotation_animation(render_duration)


# Render process
set_render_settings(render_duration)
arnold_render(render_duration, save_folder, image_name)

