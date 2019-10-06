# -*- coding: utf-8 -*-

"""create a simplifyed copy of selected objects."""

# FreeCAD basics
import FreeCAD
import FreeCADGui
import ImportGui

# regex
import re

import time
import os.path

#####################
# Begin command Part_SimpleCopy
doc = App.getDocument('lamp')
obj = doc.getObject('Body001')
__shape = Part.getShape(
    obj,
    '',
    needSubElement=False,
    refine=False
)
App.ActiveDocument.addObject('Part::Feature', 'Body001').Shape = __shape
App.ActiveDocument.ActiveObject.Label = obj.Label
obj_new = doc.getObject('Body001001')

obj_new.ViewObject.ShapeColor = \
    getattr(
        obj.getLinkedObject(True).ViewObject,
        'ShapeColor',
        obj_new.ViewObject.ShapeColor
    )
obj_new.ViewObject.LineColor = \
    getattr(
        obj.getLinkedObject(True).ViewObject,
        'LineColor',
        obj_new.ViewObject.LineColor
    )
obj_new.ViewObject.PointColor = \
    getattr(
        obj.getLinkedObject(True).ViewObject,
        'PointColor',
        obj_new.ViewObject.PointColor
    )
App.ActiveDocument.recompute()
# End command Part_SimpleCopy
#####################


def object_create_copy(obj_source):
    """Create a copy of an object."""
    obj_new = App.ActiveDocument.addObject(
        'Part::Feature',
        obj_source.Name + "__sc_export"
    )
    __shape_refined = Part.getShape(
        obj_source,
        '',
        needSubElement=False,
        refine=False
    )
    obj_new.Shape = __shape_refined
    obj_new.Label = obj_source.Label + "__sc_export"
    print(obj_source)

    # AttributeError: 'Part.Feature' object has no attribute 'BoundingBox'
    obj_new.ViewObject.BoundingBox = obj_source.ViewObject.BoundingBox
    obj_new.ViewObject.Deviation = obj_source.ViewObject.Deviation
    obj_new.ViewObject.DisplayMode = obj_source.ViewObject.DisplayMode
    obj_new.ViewObject.DrawStyle = obj_source.ViewObject.DrawStyle
    obj_new.ViewObject.Lighting = obj_source.ViewObject.Lighting
    obj_new.ViewObject.LineColor = obj_source.ViewObject.LineColor
    obj_new.ViewObject.LineMaterial = obj_source.ViewObject.LineMaterial
    obj_new.ViewObject.LineWidth = obj_source.ViewObject.LineWidth
    obj_new.ViewObject.PointColor = obj_source.ViewObject.PointColor
    obj_new.ViewObject.PointMaterial = obj_source.ViewObject.PointMaterial
    obj_new.ViewObject.PointSize = obj_source.ViewObject.PointSize
    obj_new.ViewObject.Selectable = obj_source.ViewObject.Selectable
    obj_new.ViewObject.ShapeColor = obj_source.ViewObject.ShapeColor
    obj_new.ViewObject.ShapeMaterial = obj_source.ViewObject.ShapeMaterial
    obj_new.ViewObject.Transparency = obj_source.ViewObject.Transparency
    obj_new.ViewObject.Visibility = obj_source.ViewObject.Visibility
    return obj_new


def simpleCopySelection():
    """Create a simplifyed copy of selected objects."""
    # ideas / tests / original:
    # App.ActiveDocument.addObject('Part::Feature','Box').Shape=App.ActiveDocument.Box.Shape
    # App.ActiveDocument.ActiveObject.Label=App.ActiveDocument.Box.Label
    # Gui.ActiveDocument.ActiveObject.ShapeColor=Gui.ActiveDocument.Fillet.ShapeColor
    # Gui.ActiveDocument.ActiveObject.LineColor=Gui.ActiveDocument.Fillet.LineColor
    # Gui.ActiveDocument.ActiveObject.PointColor=Gui.ActiveDocument.Fillet.PointColor
    # App.ActiveDocument.recompute()
    # for proplabel in Gui.ActiveDocument.Box.PropertiesList:
    #   App.ActiveDocument.ActiveObject[proplabel] =
    #   App.ActiveDocument.Box[proplabel]

    App = FreeCAD
    Gui = FreeCADGui

    selection = FreeCADGui.Selection.getSelection()

    for obj in selection:
        obj_new = object_create_copy(obj)
        obj_new.ViewObject.Visibility = True
        obj.ViewObject.Visibility = False
    #

    App.ActiveDocument.recompute()
#


# just do it:
simpleCopySelection()
