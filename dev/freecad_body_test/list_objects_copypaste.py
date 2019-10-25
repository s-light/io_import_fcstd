#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
List Objects.

Copy&Paste this complete script into the FreeCAD Python console!
"""

import FreeCAD


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

doc = FreeCAD.ActiveDocument
docname = doc.Name

# ******************************************
objects = doc.Objects
print("doc.Objects", len(objects))
print_objects(objects)

# ******************************************

print_obj_with_label(doc, "World_Body")
print_obj_with_label(doc, "Sun_Sphere")
print_obj_with_label(doc, "Seagull_Body")

# ******************************************
print("tests done :-)")
