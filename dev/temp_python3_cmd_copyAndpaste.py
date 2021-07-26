import sys
import os

path = "/usr/lib/freecad/lib"
sys.path.append(path)

import FreeCAD
print("FreeCAD version:", FreeCAD.Version())

path_base = FreeCAD.getResourceDir()
path = os.path.join(path_base, "Mod")
sys.path.append(path)

doc = FreeCAD.open("./BodyTest_Minimal.FCStd")
docname = doc.Name
objects = FreeCAD.ActiveDocument.Objects

print("doc.Objects", len(objects))

for o in objects:
    print(o, o.Name)

FreeCAD.closeDocument(docname)
