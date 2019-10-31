#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Helper."""

# import bpy


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
