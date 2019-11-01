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


def append_freecad_path():
    """Append the FreeCAD path."""
    global path_to_freecad
    if bpy:
        # specified in addon preferences
        user_preferences = bpy.context.preferences
        addon_prefs = user_preferences.addons["io_import_fcstd"].preferences
        path_to_freecad = addon_prefs.filepath
    if os.path.exists(path_to_freecad):
        if os.path.isfile(path_to_freecad):
            path_to_freecad = os.path.dirname(path_to_freecad)
        print("Configured path to FreeCAD:", path_to_freecad)
        if path_to_freecad not in sys.path:
            sys.path.append(path_to_freecad)
    else:
        if bpy:
            print(
                "FreeCAD path is not configured in preferences correctly. "
                "'{}'".format(path_to_freecad)
            )
        else:
            print(
                "Path to FreeCAD does not exist. Please check! "
                "'{}'".format(path_to_freecad)
            )


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

    my_importer = import_fcstd.ImportFcstd(
        # update=True,
        # placement=True,
        # scale=0.001,
        # tessellation=1.0,
        # skiphidden=True,
        # filter_sketch=True,
        # sharemats=True,
        # update_materials=False,
        # obj_name_prefix="",
        # obj_name_prefix_with_filename=False,
        # links_as_collectioninstance=True,
        path_to_freecad=path_to_freecad,
        # report=None
    )
    my_importer.import_fcstd(filename=filename)

    if bpy:
        print("\n"*2)


if __name__ == '__main__':
    main_test()
