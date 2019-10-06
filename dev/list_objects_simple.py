#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
List Objects.

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

def print_obj_header(
    pre_line="",
    show_lists=False,
    show_list_details=False,
):
    """Print header for objects list."""
    print(
        pre_line +
        "{:<15} {:<25} {:<25}"
        "".format("Label", "Name", "TypeId"),
        end=''
    )
    if show_lists:
        print(
            "{:>2} {:>2} {:>2} {:>2}"
            "".format(
                "P",
                "I",
                "O",
                "G",
            ),
            end=''
        )
        if show_list_details:
            print(
                (
                    "    {:<10}" * 4
                ).format(
                    '[Parents]',
                    '[InList]',
                    '[OutList]',
                    '[Group]'
                ),
                end=''
            )
    print()


def print_obj(
    obj,
    pre_line="",
    show_lists=False,
    show_list_details=False,
    end="\n",
):
    """Print object nicely formated."""
    print(
        pre_line +
        "{:<25} {:<15} {:<25}"
        "".format(obj.Label, obj.Name, obj.TypeId),
        end=''
    )
    if show_lists:
        group_count = '_'
        if hasattr(obj, 'Group'):
            group_count = len(obj.Group)
        print(
            "{:>2} {:>2} {:>2} {:>2}"
            "".format(
                len(obj.Parents),
                len(obj.InList),
                len(obj.OutList),
                group_count
            ),
            end=''
        )
        if show_list_details:
            group = None
            if hasattr(obj, 'Group'):
                group = obj.Group
            print(
                (
                    "    {:<10}" * 4
                ).format(
                    str(obj.Parents),
                    str(obj.InList),
                    str(obj.OutList),
                    str(group)
                ),
                end=''
            )
    print("", end=end)


def print_objects(
    objects,
    pre_line="",
    pre_list_entry="* ",
    show_lists=False,
    show_list_details=False,
):
    """Print objects list."""
    pre_list_entry_space = " "*len(pre_list_entry)
    print_obj_header(
        pre_line=pre_line + pre_list_entry_space,
        show_lists=show_lists,
        show_list_details=show_list_details,
    )
    for obj in objects:
        print_obj(
            obj,
            pre_line=pre_line + pre_list_entry,
            show_lists=show_lists,
            show_list_details=show_list_details,
        )


def print_obj_with_label(doc, label):
    """Print object with given label."""
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
