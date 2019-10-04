#!/usr/bin/env python3
# -*- coding: utf-8 -*-


def print_obj_header():
    print(
        "     {:<15} {:<25} {:<25} "
        "".format("Name", "Label", "TypeId"),
        end=''
    )
    print("[Parents]", end='')
    print("    ", end='')
    print("[InList]", end='')
    print("    ", end='')
    print("[OutList]", end='')
    print("    ", end='')
    print()


def print_obj(obj):
    print(
        "obj: {:<15} {:<25} {:<25}"
        "".format(obj.Name, obj.Label, obj.TypeId),
        end=''
    )
    print(obj.Parents, end='')
    print("    ", end='')
    print(obj.InList, end='')
    print("    ", end='')
    print(obj.OutList, end='')
    print("    ", end='')
    print()


def print_objects(objects):
    print_obj_header()
    for obj in objects:
        print_obj(obj)


# ****************************************

def get_filtered_objects(doc, typeid_filter_list=None):
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
    for obj in doc.Objects:
        if obj.TypeId not in typeid_filter_list:
            result_objects.append(obj)
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
