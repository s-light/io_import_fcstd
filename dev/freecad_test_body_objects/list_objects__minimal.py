#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
List Objects.

Stand-alone - run from commandline or copy & paste into python interpreter
"""

import sys
path_to_freecad = "/usr/lib/freecad-daily-python3/lib/"
sys.path.append(path_to_freecad)

import FreeCAD
print("FreeCAD version:", FreeCAD.Version())

doc = FreeCAD.open("./BodyTest_Minimal.FCStd")
docname = doc.Name
objects = FreeCAD.ActiveDocument.Objects

print("doc.Objects", len(objects))

for o in objects:
    print(o, o.Name)

FreeCAD.closeDocument(docname)
