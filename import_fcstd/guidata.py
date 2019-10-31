#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""XML handler."""

import xml.sax
import zipfile


class FreeCAD_xml_handler(xml.sax.ContentHandler):
    """
    A XML handler to process the FreeCAD GUI xml data.

    this creates a dictionary where each key is a FC object name,
    and each value is a dictionary of property:value pairs
    """

    def __init__(self):
        """Init."""
        self.guidata = {}
        self.current = None
        self.properties = {}
        self.currentprop = None
        self.currentval = None

    def startElement(self, tag, attributes):
        """Call when an element starts."""
        if tag == "ViewProvider":
            self.current = attributes["name"]
        elif tag == "Property":
            name = attributes["name"]
            element_names = [
                "Visibility",
                "ShapeColor",
                "Transparency",
                "DiffuseColor"
            ]
            if name in element_names:
                self.currentprop = name
        elif tag == "Bool":
            if attributes["value"] == "true":
                self.currentval = True
            else:
                self.currentval = False
        elif tag == "PropertyColor":
            c = int(attributes["value"])
            r = float((c >> 24) & 0xFF)/255.0
            g = float((c >> 16) & 0xFF)/255.0
            b = float((c >> 8) & 0xFF)/255.0
            self.currentval = (r, g, b)
        elif tag == "Integer":
            self.currentval = int(attributes["value"])
        elif tag == "Float":
            self.currentval = float(attributes["value"])
        elif tag == "ColorList":
            self.currentval = attributes["file"]

    def endElement(self, tag):
        """Call when an elements ends."""
        if tag == "ViewProvider":
            if self.current and self.properties:
                self.guidata[self.current] = self.properties
                self.current = None
                self.properties = {}
        elif tag == "Property":
            if self.currentprop and (self.currentval is not None):
                self.properties[self.currentprop] = self.currentval
                self.currentprop = None
                self.currentval = None


def load_guidata(filename, report):
    """Check if we have a GUI document."""
    report({'INFO'}, "load guidata..")
    guidata = None
    zdoc = zipfile.ZipFile(filename)
    if zdoc:
        if "GuiDocument.xml" in zdoc.namelist():
            gf = zdoc.open("GuiDocument.xml")
            guidata = gf.read()
            gf.close()
            Handler = FreeCAD_xml_handler()
            xml.sax.parseString(guidata, Handler)
            guidata = Handler.guidata
            for key, properties in guidata.items():
                # open each diffusecolor files and retrieve values
                # first 4 bytes are the array length,
                # then each group of 4 bytes is abgr
                if "DiffuseColor" in properties:
                    # print ("opening:",guidata[key]["DiffuseColor"])
                    df = zdoc.open(guidata[key]["DiffuseColor"])
                    buf = df.read()
                    # print (buf," length ",len(buf))
                    df.close()
                    cols = []
                    for i in range(1, int(len(buf)/4)):
                        cols.append(
                            (buf[i*4+3], buf[i*4+2], buf[i*4+1], buf[i*4]))
                    guidata[key]["DiffuseColor"] = cols
        zdoc.close()
    report({'INFO'}, "load guidata done.")
    # print("guidata:", guidata)
    return guidata
