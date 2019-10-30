

import bpy

# ImportHelper is a helper class, defines filename and
# invoke() function which calls the file selector.
# from bpy_extras.io_utils import ImportHelper
# not sure what this brings us...

from . import import_fcstd

bl_info = {
    "name": "FreeCAD Importer",
    "category": "Import-Export",
    "author": "Yorik van Havre; Stefan Krüger",
    "version": (6, 1, 1),
    "blender": (2, 80, 0),
    "location": "File > Import > FreeCAD",
    "description": "Imports a .FCStd file from FreeCAD",
    "warning": (
        "This addon needs FreeCAD installed on your system.  "
        "Only Part- and Mesh-based objects supported at the moment.  "
        "It is currently in an Experimental State.."
    ),
}

# brut force path loading:
# import sys; sys.path.append("/path/to/FreeCAD.so")

# pre git HISTORY
# v1.0.0 - 12 june 2018 - initial release - basically working
# v2.0.0 - 21 june 2018 - option to turn cycles mat on/off, per-face material support,
#                         use of polygons when possible, shared materials
# v3.0.0 - 06 february 2019 - ported to Blender 2.80
# v4.0.0 - 07 february 2019 - API changes + support of transparency
# v5.0.0 - 13 august 2019 - small fixes and better info messages if things go wrong


# ==============================================================================
# Blender Operator class
# ==============================================================================

# https://docs.blender.org/api/current/bpy.types.AddonPreferences.html#module-bpy.types

class IMPORT_OT_FreeCAD_Preferences(bpy.types.AddonPreferences):
    """A preferences settings dialog to set the path to the FreeCAD module."""
    # this must match the add-on name, use '__package__'
    # when defining this in a submodule of a python package.
    # bl_idname = __name__
    bl_idname = __package__

    filepath: bpy.props.StringProperty(
        subtype='FILE_PATH',
        name="Path to FreeCAD lib",
        description=(
            "Path to \n"
            "FreeCAD.so (Mac/Linux) \n"
            "or \n"
            "FreeCAD.pyd (Windows)"
        ),
        default="/usr/lib/freecad-daily-python3/lib/FreeCAD.so",
    )

    def draw(self, context):
        """Draw Preferences."""
        layout = self.layout
        layout.label(text=(
            "FreeCAD must be installed on your system, and its path set below."
            " Make sure both FreeCAD and Blender use the same Python version "
            "(check their Python console)"
        ))
        layout.prop(self, "filepath")


# class IMPORT_OT_FreeCAD(bpy.types.Operator, ImportHelper):
class IMPORT_OT_FreeCAD(bpy.types.Operator):
    """Imports the contents of a FreeCAD .FCStd file."""

    bl_idname = 'io_import_fcstd.import_freecad'
    bl_label = 'Import FreeCAD FCStd file'
    bl_options = {'REGISTER', 'UNDO'}

    # ImportHelper mixin class uses this
    filename_ext = ".fcstd"

    # https://blender.stackexchange.com/a/7891/16634
    # see Text -> Templates -> Python -> Operator File Export
    filter_glob: bpy.props.StringProperty(
        default="*.FCStd; *.fcstd",
        options={'HIDDEN'},
    )

    # Properties assigned by the file selection window.
    directory: bpy.props.StringProperty(
        maxlen=1024,
        subtype='FILE_PATH',
        options={'HIDDEN', 'SKIP_SAVE'}
    )
    files: bpy.props.CollectionProperty(
        type=bpy.types.OperatorFileListElement,
        options={'HIDDEN', 'SKIP_SAVE'}
    )

    # user import options
    option_skiphidden: bpy.props.BoolProperty(
        name="Skip hidden objects",
        default=True,
        description="Only import objects that where visible in FreeCAD"
    )
    option_filter_sketch: bpy.props.BoolProperty(
        name="Filter Sketch objects",
        default=True,
        description="Filter Sketch objects out."
    )
    option_update: bpy.props.BoolProperty(
        name="Update existing objects",
        default=True,
        description=(
            "Keep objects with same names in current scene and "
            "their materials, only replace the geometry"
        )
    )
    option_placement: bpy.props.BoolProperty(
        name="Use Placements",
        default=True,
        description="Set Blender pivot points to the FreeCAD placements"
    )
    option_tessellation: bpy.props.FloatProperty(
        name="Tessellation value",
        default=1.0,
        description="The tessellation value to apply when triangulating shapes"
    )
    option_scale: bpy.props.FloatProperty(
        name="Scaling value",
        default=0.001,
        description=(
            "A scaling value to apply to imported objects. "
            "Default value of 0.001 means one Blender unit = 1 meter"
        )
    )
    option_sharemats: bpy.props.BoolProperty(
        name="Share similar materials",
        default=True,
        description=(
            "Objects with same color/transparency will use the same material"
        )
    )
    # option_create_tree: bpy.props.BoolProperty(
    #     name="Recreate FreeCAD Object-Tree",
    #     default=True,
    #     description=(
    #         "Try to recreate the same parent-child relationships "
    #         "as in the FreeCAD Object-Tree."
    #     )
    # )

    def invoke(self, context, event):
        """Invoke is called when the user picks our Import menu entry."""
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def get_preferences(self):
        """Get addon preferences."""
        user_preferences = bpy.context.preferences
        addon_prefs = user_preferences.addons["io_import_fcstd"].preferences
        return addon_prefs

    def get_freecad_path(self):
        """Get FreeCAD path from addon preferences."""
        # get the FreeCAD path specified in addon preferences
        addon_prefs = self.get_preferences()
        path_to_freecad = addon_prefs.filepath
        print("addon_prefs path_to_freecad", path_to_freecad)
        return path_to_freecad

    def execute(self, context):
        """Call when the user is done using the modal file-select window."""
        path_to_freecad = self.get_freecad_path()
        dir = self.directory
        for file in self.files:
            filestr = str(file.name)
            if filestr.lower().endswith(".fcstd"):
                my_importer = import_fcstd.ImportFcstd(
                    update=self.option_update,
                    placement=self.option_placement,
                    tessellation=self.option_tessellation,
                    skiphidden=self.option_skiphidden,
                    filter_sketch=self.option_filter_sketch,
                    scale=self.option_scale,
                    sharemats=self.option_sharemats,
                    report=self.report,
                    path_to_freecad=path_to_freecad
                )
                return my_importer.import_fcstd(filename=dir+filestr)
        return {'FINISHED'}


# ==============================================================================
# Register plugin with Blender
# ==============================================================================

classes = (
    IMPORT_OT_FreeCAD,
    IMPORT_OT_FreeCAD_Preferences,
)


def menu_func_import(self, context):
    """Needed if you want to add into a dynamic menu."""
    self.layout.operator(IMPORT_OT_FreeCAD.bl_idname, text="FreeCAD (.FCStd)")


def register():
    """Register."""
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)


def unregister():
    """Unregister."""
    from bpy.utils import unregister_class
    for cls in reversed(classes):
        unregister_class(cls)
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)


if __name__ == "__main__":
    register()
