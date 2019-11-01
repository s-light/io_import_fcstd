#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Helper."""

import bpy


def rename_old_data(data, data_label):
    """Recusive add '_old' to data object."""
    name_old = None
    if data_label in data:
        name_old = data[data_label].name + "_old"
        if name_old in data:
            # rename recusive..
            rename_old_data(data, name_old)
        data[data_label].name = name_old
    return name_old


def find_layer_collection_recusive(*, collection_name, layer_collection):
    """Recursivly transverse layer_collection for a particular name."""
    result_layer_collection = None
    if layer_collection.name == collection_name:
        result_layer_collection = layer_collection
    else:
        for lc in layer_collection.children:
            temp = find_layer_collection_recusive(
                collection_name=collection_name,
                layer_collection=lc
            )
            if temp:
                result_layer_collection = temp
    return result_layer_collection


# def find_layer_collection_in_view_layer(collection_name, view_layer):
#     """Find layer_collection in view_layer."""
#     result_layer_collection = find_layer_collection_recusive(
#         collection_name=collection_name,
#         layer_collection=view_layer.layer_collection
#     )
#     return result_layer_collection


def find_layer_collection_in_scene(*, collection_name, scene=None):
    """Find layer_collection in scene."""
    result_layer_collections = []
    if scene is None:
        # use active scene
        scene = bpy.context.scene
    for view_layer in scene.view_layers:
        result_layer_collections.append(
            find_layer_collection_recusive(
                collection_name=collection_name,
                layer_collection=view_layer.layer_collection
            )
        )
    return result_layer_collections
