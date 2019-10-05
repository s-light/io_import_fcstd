#!/usr/bin/env python3
# -*- coding: utf-8 -*-


def print_obj_header(
    pre_line="",
    show_lists=False,
    show_list_details=False,
):
    print(
        pre_line +
        "{:<15} {:<25} {:<25}"
        "".format("Name", "Label", "TypeId"),
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
    print(
        pre_line +
        "{:<15} {:<25} {:<25}"
        "".format(obj.Name, obj.Label, obj.TypeId),
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


# ****************************************


def filtered_objects(objects, typeid_filter_list=None, include_only_visible=False):
    if typeid_filter_list is None:
        typeid_filter_list = [
            'App::Line',
            'App::Plane',
            'App::Origin',
            # 'GeoFeature',
            # 'PartDesign::CoordinateSystem',
            # 'Sketcher::SketchObject',
        ]
    result_objects = []
    for obj in objects:
        if (obj.TypeId not in typeid_filter_list):
            if include_only_visible:
                if hasattr(obj, 'Visibility'):
                    if obj.Visibility:
                        result_objects.append(obj)
                else:
                    print("obj has no Visibility attribute.")
            else:
                result_objects.append(obj)
    return result_objects


def get_filtered_objects(doc, typeid_filter_list=None):
    result_objects = filtered_objects(
        doc.Objects,
        typeid_filter_list
    )
    return result_objects


def get_root_objects(doc, filter_list=[]):
    typeid_filter_list = [
        'App::Line',
        'App::Plane',
        'App::Origin',
    ]
    typeid_filter_list = typeid_filter_list + filter_list
    result_objects = []
    for obj in doc.Objects:
        if obj.TypeId not in typeid_filter_list:
            if (len(obj.Parents) == 0):
                result_objects.append(obj)
    return result_objects


# ******************************************
# `is_toplevel_in_list` and `get_toplevel_objects`
# from forum post 'Get highest objects of model' by kbwbe
# https://forum.freecadweb.org/viewtopic.php?p=338214&sid=a6dd59fe66c1d807f8537f192fdb14dc#p338214

def is_toplevel_in_list(lst):
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
                    if o.Name.startswith('Clone'):
                        numClones += 1
                    elif o.Name.startswith('Body'):
                        numBodies += 1
                    else:
                        invalidObjects = True
                        break
                if not invalidObjects:
                    if numBodies == numClones:
                        topLevelShapes.append(ob.Name)
    return topLevelShapes
