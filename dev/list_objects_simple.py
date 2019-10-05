#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
List Objects

Stand-alone / Copy&Paste version
"""

import sys
import os


def append_freecad_path():
    """Append the FreeCAD path."""
    path_to_freecad = "/usr/lib/freecad-daily-python3/lib/FreeCAD.so"
    if os.path.exists(path_to_freecad):
        if os.path.isfile(path_to_freecad):
            path_to_freecad = os.path.dirname(path_to_freecad)
        print("Configured FreeCAD path:", path_to_freecad)
        if path_to_freecad not in sys.path:
            sys.path.append(path_to_freecad)
    else:
        print("FreeCAD path is not correct.")


try:
    append_freecad_path()
    import FreeCAD
    print("FreeCAD version:", FreeCAD.Version())
except ModuleNotFoundError as e:
    print("FreeCAD import failed.", e)


# ******************************************
def print_obj_header():
    print(
        "     {:<15} {:<25} {:<25}"
        "".format("Name", "Label", "TypeId"),
        end=''
    )
    print("p [Parents]  ", end='')
    print("i [InList]  ", end='')
    print("o [OutList]  ", end='')
    print("g [Group]  ", end='')
    print()


def print_obj(obj):
    print(
        "obj: {:<15} {:<25} {:<25}"
        "".format(obj.Name, obj.Label, obj.TypeId),
        end=''
    )
    print("p:{}  ".format(len(obj.Parents)), end='')
    print("i:{}  ".format(len(obj.InList)), end='')
    print("o:{}  ".format(len(obj.OutList)), end='')
    if hasattr(obj, 'Group'):
        print("g:{}  ".format(len(obj.Group)), end='')
    print()


def print_objects(objects):
    print_obj_header()
    for obj in objects:
        print_obj(obj)


def print_obj_with_label(doc, label):
    obj = doc.getObjectsByLabel(label)
    # print(obj)
    if len(obj) > 0:
        obj = obj[0]
        print_obj(obj)
    else:
        print("object with label '{}' not found.".format(label))


# ******************************************
#
#            Main experimetns
#
# ******************************************

doc = FreeCAD.open(
    "/home/stefan/mydata/github/blender/"
    "io_import_fcstd/dev/freecad_linking_example/assembly.FCStd"
)
docname = doc.Name

# ******************************************
print("~"*42)
objects = doc.Objects
print("doc.Objects", len(objects))
print_objects(objects)
print("~"*42)

print_obj_with_label(doc, "my_final_assembly")
print_obj_with_label(doc, "octagon_part")
print_obj_with_label(doc, "octagon_body")

# t1 = doc.getObjectsByLabel("my_final_assembly")
# t2 = doc.getObjectsByLabel("octagon_part")
# t3 = doc.getObjectsByLabel("octagon_body")


print("tests done :-)")

FreeCAD.closeDocument(docname)
