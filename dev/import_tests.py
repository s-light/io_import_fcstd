#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Import Tests

this script can be called from commandline or from within blender.
therefore we need some heavy tricks with the sys.path..
"""

import sys
import os
import importlib

try:
    import bpy
    print("\n"*2)
except ModuleNotFoundError as e:
    print("Blender 'bpy' not available.", e)
    bpy = None


# prepare directory helpers
# print(sys.argv[0])
print(os.path.realpath(__file__))
script_dir = ".."
if bpy:
    temp_path = os.path.join(__file__, "..")
    temp_path = os.path.join(temp_path, "..")
    script_dir = os.path.realpath(temp_path)
script_dir = os.path.realpath(script_dir)
print("script_dir", script_dir)

base_dir = ".."
if bpy:
    base_dir = os.path.join(script_dir, "..")
base_dir = os.path.realpath(base_dir)
print("base_dir", base_dir)

# Adds base_dir to python modules path.
if base_dir not in sys.path:
    sys.path.append(base_dir)
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
        print("Configured FreeCAD path:", path_to_freecad)
        if path_to_freecad not in sys.path:
            sys.path.append(path_to_freecad)
    else:
        if bpy:
            print("FreeCAD path is not configured in preferences correctly.")
        else:
            print("FreeCAD path is not correct.")


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


import freecad_helper  # noqa
importlib.reload(freecad_helper)


# ******************************************
#
#            Main experimetns
#
# ******************************************

def run_tests(doc):
    print("~"*42)
    print("get_filtered_objects")
    freecad_helper.print_objects(freecad_helper.get_filtered_objects(doc))

    print("~"*42)
    print("get_root_objects")
    objects = freecad_helper.get_root_objects(
        doc,
        filter_list=['Sketcher::SketchObject', ]
    )
    freecad_helper.print_objects(objects)

    print("~"*42)
    print("doc.RootObjects")
    freecad_helper.print_objects(doc.RootObjects)

    print("~"*42)
    print("get_toplevel_objects")
    freecad_helper.print_objects(freecad_helper.get_toplevel_objects(doc))

    print("~"*42)
    print("tests done :-)")


# ******************************************
def main_test():
    "Main Tests."
    if bpy:
        print("\n"*2)
    print("*"*42)
    print("run import_tests")

    # Context Managers not implemented..
    # see https://docs.python.org/3.8/reference/compound_stmts.html#with
    # with FreeCAD.open(self.config["filename"]) as doc:
    # so we use the classic try finally block:
    docname = ""
    try:
        filename_relative = "./dev/freecad_linking_example/assembly.FCStd"
        print("FreeCAD document:", filename_relative)
        filename = os.path.join(base_dir, filename_relative)
        doc = FreeCAD.open(filename)
        docname = doc.Name
        if not doc:
            print("Unable to open the given FreeCAD file")
        else:
            run_tests(doc)
    except Exception as e:
        raise e
    finally:
        if docname:
            FreeCAD.closeDocument(docname)
        print("*"*42)
        if bpy:
            print("\n"*2)


if __name__ == '__main__':
    main_test()
