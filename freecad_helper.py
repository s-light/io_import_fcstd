#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Helper tools for FreeCAD python scripts."""


def print_obj_header(
    pre_line="", show_lists=False, show_list_details=False,
):
    """Print header for objects list."""
    print(
        pre_line + "{:<15} {:<25} {:<25}" "".format("Label", "Name", "TypeId"), end=""
    )
    if show_lists:
        print("{:>2} {:>2} {:>2} {:>2}" "".format("P", "I", "O", "G",), end="")
        if show_list_details:
            print(
                ("    {:<10}" * 4).format(
                    "[Parents]", "[InList]", "[OutList]", "[Group]"
                ),
                end="",
            )
    print()


def format_obj(
    obj, pre_line="", show_lists=False, show_list_details=False, tight_format=False
):
    """Print object nicely formated."""
    result = ""
    obj_label = "NONE"
    if obj:
        obj_label = obj.Label
    obj_name = "NONE"
    if obj:
        obj_name = obj.Name
    obj_type = "NONE"
    if obj:
        obj_type = obj.TypeId
    obj_format = "{:<25} {:<15} {:<25}"
    if tight_format:
        obj_format = "'{}' ('{}' <{}>)"
    result += pre_line + obj_format.format(obj_label, obj_name, obj_type)
    if show_lists:
        group_count = "_"
        if hasattr(obj, "Group"):
            group_count = len(obj.Group)
        result += "{:>2} {:>2} {:>2} {:>2}" "".format(
            len(obj.Parents), len(obj.InList), len(obj.OutList), group_count
        )
        if show_list_details:
            group = None
            if hasattr(obj, "Group"):
                group = obj.Group
            result += ("    {:<10}" * 4).format(
                str(obj.Parents), str(obj.InList), str(obj.OutList), str(group)
            )
    return result


def print_obj(
    obj, pre_line="", show_lists=False, show_list_details=False, end="\n",
):
    print(
        format_obj(
            obj=obj,
            pre_line=pre_line,
            show_lists=show_lists,
            show_list_details=show_list_details,
        ),
        end=end,
    )


def print_objects(
    objects,
    pre_line="",
    pre_list_entry="* ",
    show_lists=False,
    show_list_details=False,
):
    """Print objects list."""
    pre_list_entry_space = " " * len(pre_list_entry)
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


# ****************************************


def filtered_objects(objects, typeid_filter_list=None, include_only_visible=False):
    """Filter list of objects."""
    if typeid_filter_list is None:
        typeid_filter_list = [
            "App::Line",
            "App::Plane",
            "App::Origin",
            # 'GeoFeature',
            # 'PartDesign::CoordinateSystem',
            # 'Sketcher::SketchObject',
        ]
    result_objects = []
    for obj in objects:
        if obj.TypeId not in typeid_filter_list:
            if include_only_visible:
                if hasattr(obj, "Visibility"):
                    if obj.Visibility:
                        result_objects.append(obj)
                else:
                    print(
                        "filtered_objects: "
                        "obj '{}' has no Visibility attribute."
                        "it is excluded from results."
                        "".format(obj.Name)
                    )
            else:
                result_objects.append(obj)
    return result_objects


def get_filtered_objects(doc, typeid_filter_list=None):
    """Get filterd list of objects."""
    result_objects = filtered_objects(doc.Objects, typeid_filter_list)
    return result_objects


def get_root_objects(doc, filter_list=[]):
    """Get root list of objects."""
    typeid_filter_list = [
        "App::Line",
        "App::Plane",
        "App::Origin",
    ]
    typeid_filter_list = typeid_filter_list + filter_list
    result_objects = []
    for obj in doc.Objects:
        if obj.TypeId not in typeid_filter_list:
            if (len(obj.Parents) == 0) and (True):
                result_objects.append(obj)
    return result_objects


# ******************************************
# `is_toplevel_in_list` and `get_toplevel_objects`
# from forum post 'Get highest objects of model' by kbwbe
# https://forum.freecadweb.org/viewtopic.php?p=338214&sid=a6dd59fe66c1d807f8537f192fdb14dc#p338214


def is_toplevel_in_list(lst):
    """Check if objects in list are at top level."""
    if len(lst) == 0:
        return True
    for ob in lst:
        if ob.Name.startswith("Clone"):
            continue
        if ob.Name.startswith("Part__Mirroring"):
            continue
        else:
            return False
    return True


def get_toplevel_objects(doc):
    """Get top level list of objects."""
    topLevelShapes = []
    for ob in doc.Objects:
        if is_toplevel_in_list(ob.InList):
            topLevelShapes.append(ob)
        else:
            numBodies = 0
            numClones = 0
            invalidObjects = False
            # perhaps pairs of Clone/Bodies
            if len(ob.InList) % 2 == 0:
                for o in ob.InList:
                    if o.Name.startswith("Clone"):
                        numClones += 1
                    elif o.Name.startswith("Body"):
                        numBodies += 1
                    else:
                        invalidObjects = True
                        break
                if not invalidObjects:
                    if numBodies == numClones:
                        topLevelShapes.append(ob.Name)
    return topLevelShapes
