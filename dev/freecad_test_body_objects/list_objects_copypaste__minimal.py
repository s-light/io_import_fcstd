#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
List Objects.

Copy&Paste this complete script into the FreeCAD Python console!
"""





import FreeCAD
print("FreeCAD version:", FreeCAD.Version())

objects = FreeCAD.ActiveDocument.Objects

print("doc.Objects", len(objects))

for o in objects:
    print(o, o.Name)
