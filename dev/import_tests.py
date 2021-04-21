#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Import Tests.

this script can be called from commandline or from within blender.
therefore we need some heavy tricks with the sys.path..
"""

import sys
import os
import importlib

print("$"*42)
print("import_tests.py")
print("$"*42)

try:
    import bpy
except ModuleNotFoundError as e:
    print("Blender 'bpy' not available.", e)
    bpy = None


# prepare directory helpers
# print(sys.argv[0])
print(os.path.realpath(__file__))
script_dir = "."
if bpy:
    temp_path = os.path.join(__file__, "..")
    temp_path = os.path.join(temp_path, "..")
    script_dir = os.path.realpath(temp_path)
script_dir = os.path.realpath(script_dir)
print("script_dir", script_dir)
if script_dir not in sys.path:
    sys.path.append(script_dir)

base_dir = ".."
if bpy:
    base_dir = os.path.join(script_dir, "..")
base_dir = os.path.realpath(base_dir)
print("base_dir", base_dir)
if base_dir not in sys.path:
    sys.path.append(base_dir)

outside_package_dir = os.path.join(base_dir, "..")
outside_package_dir = os.path.realpath(outside_package_dir)
print("outside_package_dir", outside_package_dir)
if outside_package_dir not in sys.path:
    sys.path.append(outside_package_dir)

# print("sys.path:")
# for p in sys.path:
#     print(p)


# fallback path to FreeCAD daily
path_to_freecad = "/usr/lib/freecad-daily-python3/lib/FreeCAD.so"
path_to_system_packages = "/usr/lib/python3/dist-packages/"


def append_path(path, sub=""):
    if path and sub:
        path = os.path.join(path, sub)
        print("full path:", path)
    if path and os.path.exists(path):
        if os.path.isfile(path):
            path = os.path.dirname(path)
        print("Configured path:", path)
        if path not in sys.path:
            sys.path.append(path)
    else:
        print(
            "Path does not exist. Please check! "
            "'{}'".format(path)
        )


def get_preferences():
    """Get addon preferences."""
    __package__ = "io_import_fcstd"
    print("__package__: '{}'".format(__package__))
    addon_prefs = None
    # pref = bpy.context.preferences.addons["io_import_fcstd"].preferences
    if bpy:
        user_preferences = bpy.context.preferences
        addon_prefs = user_preferences.addons[__package__].preferences
    return addon_prefs


def get_path_to_freecad():
    """Get FreeCAD path from addon preferences."""
    # get the FreeCAD path specified in addon preferences
    addon_prefs = get_preferences()
    path = addon_prefs.filepath_freecad
    print("addon_prefs path_to freecad", path)
    return path


def get_path_to_system_packages():
    """Get FreeCAD path from addon preferences."""
    # get the FreeCAD path specified in addon preferences
    addon_prefs = get_preferences()
    path = addon_prefs.filepath_system_packages
    print("addon_prefs path_to system_packages", path)
    return path


def append_freecad_path():
    """Append the FreeCAD path."""
    global path_to_freecad
    global path_to_system_packages
    if bpy:
        # specified in addon preferences
        user_preferences = bpy.context.preferences
        addon_prefs = user_preferences.addons["io_import_fcstd"].preferences
        path_to_freecad = addon_prefs.filepath_freecad
        path_to_freecad = get_path_to_freecad()
        path_to_system_packages = get_path_to_system_packages()
    append_path(path_to_freecad)


try:
    append_freecad_path()
    import FreeCAD
    print("FreeCAD version:", FreeCAD.Version())
except ModuleNotFoundError as e:
    print("FreeCAD import failed.", e)

# try:
#     import Part
#     # import Draft
#     # import PartDesignGui
# except ModuleNotFoundError as e:
#     print("FreeCAD Workbench import failed:", e)

print("*"*42)
print("from io_import_fcstd import import_fcstd")
# pylama:ignore=E402
from io_import_fcstd import import_fcstd
importlib.reload(import_fcstd)
importlib.reload(import_fcstd.helper)
importlib.reload(import_fcstd.guidata)
importlib.reload(import_fcstd.material)
importlib.reload(import_fcstd.fc_helper)
importlib.reload(import_fcstd.b_helper)

# ******************************************
#
#            Main experimetns
#
# ******************************************

# def run_tests(doc):
#     print("~"*42)
#     print("get_filtered_objects")
#     freecad_helper.print_objects(freecad_helper.get_filtered_objects(doc))
#
#     print("~"*42)
#     print("get_root_objects")
#     objects = freecad_helper.get_root_objects(
#         doc,
#         filter_list=['Sketcher::SketchObject', ]
#     )
#     freecad_helper.print_objects(objects)
#
#     print("~"*42)
#     print("doc.RootObjects")
#     freecad_helper.print_objects(doc.RootObjects)
#
#     print("~"*42)
#     print("get_toplevel_objects")
#     freecad_helper.print_objects(freecad_helper.get_toplevel_objects(doc))
#
#     print("~"*42)
#     print("tests done :-)")


def freecad_python_console_copy_and_paste():
    """Copy into FreeCAD python console..."""
    # sys.path.append("/home/stefan/mydata/github/blender/io_import_fcstd")
    sys.path.append(outside_package_dir)
    import freecad_helper as fch  # noqa


# ******************************************
def main_test():
    """Run Tests."""
    print("*"*42)
    print("run import_tests")

    # get open document name
    doc_filename = os.path.splitext(os.path.basename(bpy.data.filepath))
    if doc_filename[1].endswith("blend"):
        doc_filename = doc_filename[0]
        doc_filename += ".FCStd"
        filename = os.path.join(".", doc_filename)
        filename = os.path.join(script_dir, filename)
    else:
        # fallback
        # filename = "./dev/freecad_linking_example/assembly.FCStd"
        filename = "./dev/freecad_linking_example/assembly__export.FCStd"
        filename = os.path.join(base_dir, filename)

    filename = os.path.realpath(filename)
    print("FreeCAD document to import:", filename)

    print(
        "purge '{}' unused data blocks."
        "".format(import_fcstd.b_helper.purge_all_unused())
    )
    print(
        "purge '{}' unused data blocks."
        "".format(import_fcstd.b_helper.purge_all_unused())
    )

    my_importer = import_fcstd.ImportFcstd(
        # update=True,
        # placement=True,
        # scale=0.001,
        # tessellation=0.10,
        # auto_smooth_use=True,
        # auto_smooth_angle=math.radians(85),
        # skiphidden=True,
        # filter_sketch=True,
        # sharemats=True,
        # update_materials=False,
        # obj_name_prefix="",
        # obj_name_prefix_with_filename=False,
        links_as_collectioninstance=False,
        path_to_freecad=path_to_freecad,
        path_to_system_packages=path_to_system_packages,
        # report=None
    )
    my_importer.import_fcstd(filename=filename)

    if bpy:
        print("\n"*2)


if __name__ == '__main__':
    main_test()
