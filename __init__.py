

import bpy

from . import import_fcstd

bl_info = {
    "name": "FreeCAD Importer",
    "category": "Import-Export",
    "author": "Yorik van Havre",
    "version": (6, 0, 0),
    "blender": (2, 80, 0),
    "location": "File > Import > FreeCAD",
    "description": "Imports a .FCStd file from FreeCAD",
    "warning": "This addon needs FreeCAD installed on your system. \
    Only Part- and Mesh-based objects supported at the moment.",
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


class IMPORT_OT_FreeCAD(bpy.types.Operator):
    """Imports the contents of a FreeCAD .FCStd file."""

    bl_idname = 'import_fcstd.import_freecad'
    bl_label = 'Import FreeCAD FCStd file'
    bl_options = {'REGISTER', 'UNDO'}

    # ImportHelper mixin class uses this
    filename_ext = ".fcstd"

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

    def invoke(self, context, event):
        """Invoke is called when the user picks our Import menu entry."""
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):
        """Call when the user is done using the modal file-select window."""
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
                    report=self.report
                )
                return my_importer.import_fcstd(filename=dir+filestr)
        return {'FINISHED'}


class IMPORT_OT_FreeCAD_Preferences(bpy.types.AddonPreferences):
    """A preferences settings dialog to set the path to the FreeCAD module."""

    bl_idname = __name__

    filepath: bpy.props.StringProperty(
            name="Path to FreeCAD.so (Mac/Linux) or FreeCAD.pyd (Windows)",
            subtype='FILE_PATH',
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
