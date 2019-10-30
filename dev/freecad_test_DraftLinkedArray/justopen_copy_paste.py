#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Just opens a file.

copy und paste content into running python3 instance
"""

import sys
sys.path.append("/usr/lib/freecad-daily-python3/lib/")
import FreeCAD

print("FreeCAD version:", FreeCAD.Version())
print("*"*42)
doc = FreeCAD.open("./Test_DraftLinkedArray.FCStd")


print("file contains {} objects.".format(len(doc.Objects)))
FreeCAD.closeDocument(doc.Name)
print("file closed.")
