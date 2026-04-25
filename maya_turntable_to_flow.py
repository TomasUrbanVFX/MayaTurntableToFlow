import subprocess, os, tempfile, json, shutil

import maya.api.OpenMaya as om
import maya.cmds as cmds

from PySide6 import QtWidgets as Qtw
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPixmap

import shotgun_api3
from id_config import FLOW_SERVER_URL, FLOW_USERNAME, FLOW_PASSWORD


class UIWindow(Qtw.QMainWindow):
    """Builds the multipage UI window and keeps track of user input"""
    def __init__(self, parent=None):
        super(UIWindow, self).__init__(parent)

        # Always keep UI pinned on top
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)

        # Connecting classes----------------------
        self.cmdf = CommandFunctions(self)
        self.uif  = UIFunctions(self)

        # Path to mayapy.exe (normally in C:\Program Files\Autodesk\Maya2026\bin\mayapy.exe)
        self.mayapy_path = r"C:\Program Files\Autodesk\Maya2026\bin\mayapy.exe"

        # Variables-------------------------------
        self.object_list     = []
        self.current_page    = 0
        self.render_process  = None
        self.render_timer    = QTimer()
        self.save_path       = ""
        self.project_query   = []
        self.working_project = None

        # Shotgun controller----------------------
        self.sg = shotgun_api3.Shotgun(
            FLOW_SERVER_URL,
            login=FLOW_USERNAME,
            password=FLOW_PASSWORD
        )

        # Building the main window----------------
        self.window_title = "Turntable renderer"
        self.setWindowTitle(self.window_title)
        self.setMinimumSize(800, self.sizeHint().height())

        main_layout = self.uif.add_main_layout()
        main_layout.setContentsMargins(20, 20, 20, 20)

        # Create the stacked widget----------------
        self.stacked_widget = Qtw.QStackedWidget()

        # Create PAGES-----------------------------
        page1_widget = Qtw.QWidget()
        page1_layout = Qtw.QVBoxLayout(page1_widget)

        page2_widget = Qtw.QWidget()
        page2_layout = Qtw.QVBoxLayout(page2_widget)

        page3_widget = Qtw.QWidget()
        page3_layout = Qtw.QVBoxLayout(page3_widget)

        page4_widget = Qtw.QWidget()
        page4_layout = Qtw.QVBoxLayout(page4_widget)

        # Building the UI-------------------------

        #---- PAGE 01 - object selection

        self.list_box_objects = self.uif.add_list_box(label="3D objects to render:", parent=page1_layout)

        object_button_layout = Qtw.QHBoxLayout()
        self.btn_add_obj      = self.uif.add_button(label="  Add object  ", parent=object_button_layout)
        self.btn_rem_obj      = self.uif.add_button(label="  Remove object  ", parent=object_button_layout)
        page1_layout.addLayout(object_button_layout)

        self.div1             = self.uif.add_divider(parent=page1_layout)

        self.btn_render       = self.uif.add_button(label="  Render turntable  ", parent=page1_layout)

        #---- PAGE 02 - render progress

        self.page02_label     = self.uif.add_label(label="Turntable render in progress, please keep this window open", parent=page2_layout)

        #---- PAGE 03 - render preview

        self.output_preview   = self.uif.add_image(label="Image", parent=page3_layout)

        self.btn_preview_vid  = self.uif.add_button(label="  Preview video  ", parent=page3_layout)
        self.btn_go_to_upload = self.uif.add_button(label="  Proceed to upload page  ", parent=page3_layout)

        #---- PAGE 04 - flow upload

        self.projects_menu    = self.uif.add_dropdown_menu(parent=page4_layout)
        self.flow_tree        = self.uif.add_tree(parent=page4_layout)

        self.div2             = self.uif.add_divider(parent=page4_layout)

        output_path_layout       = Qtw.QHBoxLayout()
        self.txt_field_output    = self.uif.add_text_field(label='Optional file output:',lw=200, parent=output_path_layout, text=" Add path")
        self.btn_set_path_output = self.uif.add_button(label="  Set folder  ", parent=output_path_layout)
        page4_layout.addLayout(output_path_layout)

        self.div3                = self.uif.add_divider(parent=page4_layout)

        self.txt_field_notes     = self.uif.add_text_field(label='Notes:',lh=100, parent=page4_layout)
        self.btn_upload_to_flow  = self.uif.add_button(label="  Upload to Flow  ", parent=page4_layout)


        # Add pages------------------------------
        self.stacked_widget.addWidget(page1_widget)
        self.stacked_widget.addWidget(page2_widget)
        self.stacked_widget.addWidget(page3_widget)
        self.stacked_widget.addWidget(page4_widget)

        main_layout.addWidget(self.stacked_widget)


        # Connecting functionality----------------
        self.render_timer.timeout.connect(self.cmdf.check_render_complete)

        self.btn_add_obj.clicked.connect(self.cmdf.add_object)
        self.btn_rem_obj.clicked.connect(self.cmdf.remove_object)

        self.btn_render.clicked.connect(self.cmdf.export_turntable_scene)
        self.btn_render.clicked.connect(self.cmdf.run_subprocess)
        self.btn_render.clicked.connect(self.cmdf.go_to_next_page)

        self.btn_preview_vid.clicked.connect(self.cmdf.play_video)

        self.btn_go_to_upload.clicked.connect(self.cmdf.go_to_next_page)
        self.btn_go_to_upload.clicked.connect(self.cmdf.set_projects_to_menu)
        self.btn_go_to_upload.clicked.connect(self.cmdf.get_data_from_flow)

        self.projects_menu.currentTextChanged.connect(self.cmdf.update_working_project)

        self.btn_set_path_output.clicked.connect(self.cmdf.open_file_dialog)
        self.btn_upload_to_flow.clicked.connect(self.cmdf.upload_to_flow)


class UIFunctions:
    """Functions used to create and update UI without the user's direct interaction"""
    def __init__(self, ui_link):
        self.ui = ui_link

    def add_main_layout(self):
        """Constructs the main layout"""
        central_widget = Qtw.QWidget()
        self.ui.setCentralWidget(central_widget)
        main_layout = Qtw.QVBoxLayout(central_widget)
        return main_layout

    def add_label(self, label="Label", parent=None):
        """Constructs and adds a label to the parent layout"""
        local_layout = Qtw.QHBoxLayout()
        label_widget = Qtw.QLabel(label)
        local_layout.addWidget(label_widget)
        parent.addLayout(local_layout)
        return label_widget

    def add_button(self, label="Button", parent=None, align=None):
        """Constructs and adds a push button to the parent layout. Functionality for alignment to the left"""
        button = Qtw.QPushButton(label)
        local_layout = Qtw.QHBoxLayout()

        # Correct alignment of buttons
        if align== "left":
            local_layout.addWidget(button,alignment=Qt.AlignRight)
        else:
            local_layout.addWidget(button)

        parent.addLayout(local_layout)
        return button

    def add_divider(self, parent = None):
        """Constructs and adds a horizontal divider line to the parent layout"""
        div = Qtw.QLabel("")
        div.setStyleSheet(
            "QLabel {background-color: #3e3e3e; padding: 20; margin: 0; border-bottom: 1 solid #666; border-top: 1 solid #2a2a2a;}")
        div.setMaximumHeight(3)

        div2 = Qtw.QLabel("")
        div2.setMaximumHeight(6)

        local_layout = Qtw.QVBoxLayout()
        local_layout.addWidget(div2)
        local_layout.addWidget(div)
        local_layout.addWidget(div2)

        parent.addLayout(local_layout)
        return div

    def add_list_box(self, label="List Box", parent=None):
        """Constructs and adds a list box to the parent layout. Adds a placeholder item"""
        local_layout = Qtw.QVBoxLayout()

        box_label = Qtw.QLabel(label)
        list_box = Qtw.QListWidget()

        local_layout.addWidget(box_label)
        local_layout.addWidget(list_box)
        parent.addLayout(local_layout)

        # A placeholder item with instructions - it gets removed when an actual locator is added
        list_box.addItems("Select an object to render in the Outliner and press 'Add object' " for num in range(0,1))
        return list_box

    def add_text_field(self, label="Text Field", lw=150, lh=40, parent=None,text=None):
        """Constructs and adds a text field with a label to the parent layout. Functionality for placeholders"""
        text_field_label = Qtw.QLabel(label)
        text_field_label.setFixedSize(lw, lh)
        text_field_box = Qtw.QLineEdit()

        # Greys out placeholder text and sets font style to Italic
        if text:
            text_field_box.setPlaceholderText(text)
            text_field_box.setReadOnly(True)
            text_field_box.setStyleSheet("font-style: italic;")

        local_layout = Qtw.QHBoxLayout()
        local_layout.addWidget(text_field_label)
        local_layout.addWidget(text_field_box)

        parent.addLayout(local_layout)
        return text_field_box

    def add_tree(self, parent=None):
        """Constructs and adds a label to the parent layout"""
        local_layout = Qtw.QHBoxLayout()
        tree_widget = Qtw.QTreeWidget()

        local_layout.addWidget(tree_widget)
        parent.addLayout(local_layout)
        return tree_widget

    def add_image(self, label="Image", parent=None):
        """Constructs and adds an image to the parent layout"""
        pixmap = QPixmap()

        local_layout = Qtw.QHBoxLayout()
        label_widget = Qtw.QLabel(label)

        label_widget.setPixmap(pixmap)

        local_layout.addWidget(label_widget, alignment=Qt.AlignCenter)
        parent.addLayout(local_layout)

        return label_widget

    def add_dropdown_menu(self, label="Project: ", parent=None):
        """Constructs and adds a drop-down menu to the parent layout."""
        local_layout = Qtw.QHBoxLayout()

        menu_label = Qtw.QLabel(label)
        menu = Qtw.QComboBox()

        local_layout.addWidget(menu_label)
        local_layout.addWidget(menu)
        parent.addLayout(local_layout)

        return menu


class CommandFunctions:
    """Functions used after user's direct interaction with the UI"""
    def __init__(self, ui_link):
        self.ui = ui_link

    def go_to_next_page(self):
        """Go to the next page in the UI"""
        self.ui.current_page += 1
        self.ui.stacked_widget.setCurrentIndex(self.ui.current_page)


    def add_object(self):
        """If not already selected for rendering, adds selected object to the turntable scene """
        # Get currently selected objects in Maya
        sel = cmds.ls(selection=True)

        if not sel:
            om.MGlobal.displayWarning("No object selected in Outliner.")
            return

        # Take the first selected object
        obj = sel[0]

        # Remove placeholder if it exists
        if self.ui.list_box_objects.count() == 1:
            first_item = self.ui.list_box_objects.item(0).text()
            if "Select an object" in first_item:
                self.ui.list_box_objects.takeItem(0)

        # Add to internal list and UI if not already there
        if obj not in self.ui.object_list:
            self.ui.object_list.append(obj)
            self.ui.list_box_objects.addItem(obj)

        else:
            om.MGlobal.displayWarning(f"'{obj}' is already in the list.")


    def remove_object(self):
        """Removes selected list item from turntable scene"""
        row = self.ui.list_box_objects.currentRow()

        if row < 0:
            return

        item_text = self.ui.list_box_objects.item(row).text()

        # Remove from internal list
        if item_text in self.ui.object_list:
            self.ui.object_list.remove(item_text)

        # Remove from UI
        self.ui.list_box_objects.takeItem(row)

    #------------------------------------

    def export_turntable_scene(self):
        """Export object list to a new scene in a tempdir, edit config .json, then run the subprocess"""
        # Make tempdir
        temp_directory        = tempfile.mkdtemp(prefix="turntable_temp_materials_")
        render_scene_filename = temp_directory + r"\turntable_render.mb"
        print(f"Render scene saved at: {render_scene_filename}")

        # Verify that selected objects still exist
        for obj in self.ui.object_list:
            try:
                cmds.select(obj)
            except:
                self.ui.object_list.remove(obj)

        # Only select objects in object list
        if self.ui.object_list is not None:
            cmds.select(self.ui.object_list)
        else:
            om.MGlobal.displayWarning("No objects in the list.")
            return

        # Get current Maya scene name
        scene_original_name = cmds.file(q=True, sn=True)

        # Export selection to a .mb file
        cmds.file(rename=render_scene_filename)
        cmds.file(exportSelected=True, type="mayaBinary", force=True)

        # Rename scene back to original name
        cmds.file(rename=scene_original_name)

        # Find json file
        script_dir = os.path.dirname(os.path.abspath(__file__))
        render_config = os.path.join(script_dir, "render_config.json")

        # Edit json values to point to tempdir and .mb scene
        with open(render_config, 'r+') as f:
            data = json.load(f)
            data['save_folder'] = temp_directory
            data['assets_file'] = render_scene_filename
            # Reset file position
            f.seek(0)
            json.dump(data, f, indent=4)
            f.truncate()
            f.close()


    def run_subprocess(self):
        """Runs the turntable render as subprocess (render_subprocess.py)"""
        # Create absolute path no matter the working directory
        script_dir = os.path.dirname(os.path.abspath(__file__))
        turntable_script = os.path.join(script_dir, "render_subprocess.py")
        render_config = os.path.join(script_dir, "render_config.json")

        # Skip user setup (causes crashes)
        env = os.environ.copy()
        env["MAYA_SKIP_USERSETUP_PY"] = "1"

        try:
            self.ui.render_process = subprocess.Popen(
                [self.ui.mayapy_path, turntable_script, render_config],
                env=env
            )

            self.ui.render_timer.start(1000)

        except Exception as e:
            om.MGlobal.displayWarning(f"Could not render, check your mayapy.exe path and script folder: {e}")


    def check_render_complete(self):
        """If the render is complete, converts images to video and switches to next page"""
        if self.ui.render_process.poll() is not None:
            self.ui.render_timer.stop()
            # Run FFMPEG conversion from images to mp4
            self.turn_images_to_mp4()
            # Then switch page
            self.go_to_next_page()
            self.set_preview_image()

    #-----------------------------------

    def turn_images_to_mp4(self):
        frames_folder, output_video = self.read_json_file()

        # Stitch images into video
        subprocess.run([
            "ffmpeg",
            "-framerate", "25",
            "-i", frames_folder + r"\turntable_image_%04d.png",
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            output_video
        ])


    @staticmethod
    def read_json_file() -> [str, str] :
        """Reads the json file and returns the frames folder and output video paths"""
        # Find json file
        script_dir = os.path.dirname(os.path.abspath(__file__))
        render_config = os.path.join(script_dir, "render_config.json")

        # Get output and images
        with open(render_config, "r") as f:
            f.seek(0)
            config = json.load(f)

        frames_folder = config["save_folder"]
        output_video = frames_folder + r"\output.mp4"

        return frames_folder, output_video

    #------------------------------------

    def set_preview_image(self):
        frames_folder, output_video = self.read_json_file()
        image = frames_folder + r"\turntable_image_0000.png"
        print(image)

        pixmap = QPixmap()
        pixmap.load(image)

        width = 500
        height = 500
        pixmap = pixmap.scaled(width, height, Qt.KeepAspectRatio, Qt.SmoothTransformation)

        self.ui.output_preview.setPixmap(pixmap)


    def play_video(self):
        """Opens the preview video"""
        frames_folder, output_video = self.read_json_file()
        os.startfile(output_video)


    def open_file_dialog(self):
        """Opens a file dialog for choosing the CSV path"""
        # Open dialog
        path, _ = Qtw.QFileDialog.getSaveFileName(
            self.ui,
            "Save File As...",
            "",
            "MP4 files (*.mp4);;All Files (*)"
        )

        if path:  # User pressed OK
            self.ui.txt_field_output.setText(path)    # Update the text field
            self.ui.txt_field_output.setToolTip(path) # Update the tool tip (hover over textfield)
            self.ui.save_path = path                  # Set the internal save_path variable

    #------------------------------------

    def set_projects_to_menu(self):
        """Fetches the available flow projects and populates the menus"""
        # Clear the menus
        self.ui.projects_menu.clear()

        # Find all projects
        filters = [["name", "not_contains", "Template"],["name", "is_not", "Start from Scratch"]]
        fields        = ["name"]
        self.ui.project_query = self.ui.sg.find("Project", filters, fields)

        # Repopulate the menus with the new projects
        for project in self.ui.project_query:
            self.ui.projects_menu.addItem(project["name"])

        self.ui.working_project = self.ui.project_query[0]


    def update_working_project(self):
        self.ui.working_project = self.ui.project_query[self.ui.projects_menu.currentIndex()]
        self.get_data_from_flow()


    def get_data_from_flow(self):
        """Gets the asset data needed to build the tree"""

        # Find all assets and asset libraries in the working project
        filters = [["project", "is", self.ui.working_project]]
        fields  = ["id", "code", "sg_asset_library"]

        asset_lib_query = self.ui.sg.find("AssetLibrary", filters, fields)
        asset_query     = self.ui.sg.find("Asset", filters, fields)

        # project{asset_lib: {asset_name: {data}, asset_name: {data}}, asset_lib: {asset_name: {data}}}
        final_structure = {}
        unassigned_assets = {}  # Assets with no library

        # Structure the asset data in a dict
        for asset in asset_query:
            if asset['sg_asset_library'] is None:
                unassigned_assets[asset["code"]] = asset
            else:

                for asset_library in asset_lib_query:
                    asset_library_structure = {}

                    for asset in asset_query:

                        if asset['sg_asset_library'] is not None and asset['sg_asset_library']["id"] == asset_library["id"]:
                            asset_library_structure[asset["code"]] = asset

                    final_structure[asset_library["code"]] = asset_library_structure

        self.populate_tree(final_structure, unassigned_assets)


    def populate_tree(self, flow_data, unassigned_assets):
        """Populates the flow_tree with project, asset libs and assets"""
        # Clears the tree
        self.ui.flow_tree.clear()

        # Create the root object (Project)
        project_item = Qtw.QTreeWidgetItem()
        self.ui.flow_tree.addTopLevelItem(project_item)
        project_item.setText(0,f"Project id:{self.ui.working_project['id']}")
        project_item.setExpanded(True)

        # Create asset library and asset objects
        for asset_library in flow_data:
            ass_lib_item = Qtw.QTreeWidgetItem()
            ass_lib_item.setText(0, asset_library)
            project_item.addChild(ass_lib_item)
            ass_lib_item.setExpanded(True)


            for asset in flow_data[asset_library]:
                asset_item   = Qtw.QTreeWidgetItem()
                asset_item.setText(0, asset)
                asset_item.setData(1,0,flow_data[asset_library][asset])
                ass_lib_item.addChild(asset_item)

        for asset in unassigned_assets:
            asset_item = Qtw.QTreeWidgetItem()
            asset_item.setText(0, asset)
            asset_item.setData(1, 0, asset)
            project_item.addChild(asset_item)

    #-------------------------------------

    def upload_to_flow(self):
        """Create a new version and upload a video to it"""
        selected_asset = self.ui.flow_tree.currentItem()
        upload_parent  = selected_asset.data(1,0)

        # Check if selected object is an Asset
        if selected_asset.data(1,0) is None:
            om.MGlobal.displayWarning(f"You can only upload to Assets")
            return

        folder_path, video_path = self.read_json_file()
        notes = self.ui.txt_field_notes.text()

        # Find all previous versions of the Asset
        filters = [["entity", "is", upload_parent]]
        fields = ["id", "code"]
        older_versions = self.ui.sg.find("Version", filters, fields)

        # Try to upversion the latest uploaded version
        if older_versions is not None:
            try:
                name = str(older_versions[-1]["code"]).split("_")[0]
                num  = str(int(str(older_versions[-1]["code"]).split("_")[-1]) + 1)
                version_name = name+"_"+num.zfill(3)
            except:
                print("Naming convention for versions: version_000")
                version_name = "version_000"
        else:
            version_name = "version_000"

        # Set up new version
        data = {
            "project": self.ui.working_project,
            "code": version_name,
            "entity": upload_parent,
            "sg_path_to_movie": video_path,
            "description": notes
        }

        # Create new version on selected object and upload output video and notes to it
        new_version = self.ui.sg.create("Version", data)
        self.ui.sg.upload("Version", new_version["id"], video_path, "sg_uploaded_movie")
        print("VIDEO UPLOADED, deleting temp folder...")

        # Optional saving of the video to specified folder
        if self.ui.save_path != "":
            try:
                shutil.copy(video_path, self.ui.save_path)
            except:
                om.MGlobal.displayWarning(f"Couldn't copy output, you can find it in: {video_path}")
                return

        # Tempdir cleanup
        try:
            shutil.rmtree(folder_path)
        except Exception as e:
            om.MGlobal.displayWarning(f"Couldn't delete tmp folder: {e}")



def show_ui():
    """Closes the main window if it was previously created. Makes a new main window."""
    global simple_window
    try:
        simple_window.close()  # Close if it exists
    except:
        pass
    simple_window = UIWindow()
    simple_window.show()


# Run the UI
show_ui()
