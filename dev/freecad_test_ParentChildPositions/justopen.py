#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Just open the file.

use from commandline or copy und paste content into running python3 instance
"""

import sys

path_to_freecad = "/usr/lib/freecad-daily-python3/lib/"
try:
    sys.path.append(path_to_freecad)
    import FreeCAD
    print("FreeCAD version:", FreeCAD.Version())
except ModuleNotFoundError as e:
    print("FreeCAD import failed.", e)


def open_file(filename):
    docname = ""
    try:
        print("FreeCAD document:", filename)
        print("open file..")
        doc = FreeCAD.open(filename)
        print("file is opened.")
        docname = doc.Name
        if not doc:
            print("Unable to open the given FreeCAD file")
        else:
            print("file contains {} objects.".format(len(doc.Objects)))
    except Exception as e:
        raise e
    finally:
        if docname:
            print("close file..")
            FreeCAD.closeDocument(docname)
            print("file is closed.")


# ******************************************
if __name__ == '__main__':
    "Main Tests."
    print("*"*42)
    filename = "./TestParentChildPositions_NoLinks.FCStd"
    filename = "./TestParentChildPositions.FCStd"
    open_file(filename)
    print("*"*42)
