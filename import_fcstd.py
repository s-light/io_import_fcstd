#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import bpy
import xml.sax
import zipfile
import os

from . import freecad_helper as fc_helper
from . import blender_helper as b_helper


from bpy_extras.node_shader_utils import PrincipledBSDFWrapper

# set to True to triangulate all faces (will loose multimaterial info)
TRIANGULATE = False


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
            if name in ["Visibility", "ShapeColor", "Transparency", "DiffuseColor"]:
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


class ImportFcstd(object):
    """Import fcstd files."""

    def __init__(
        self,
        filename=None,
        update=True,
        placement=True,
        tessellation=1.0,
        skiphidden=True,
        filter_sketch=True,
        scale=0.001,
        sharemats=True,
        update_materials=False,
        obj_name_prefix="",
        report=None
    ):
        super(ImportFcstd, self).__init__()
        self.config = {
            "filename": filename,
            "update": update,
            "placement": placement,
            "tessellation": tessellation,
            "skiphidden": skiphidden,
            "filter_sketch": filter_sketch,
            "scale": scale,
            "sharemats": sharemats,
            "update_materials": update_materials,
            "obj_name_prefix": obj_name_prefix,
            "report": self.print_report,
        }
        self.report = report

        print('config', self.config)
        self.guidata = {}
        self.fcstd_collection = None
        self.doc_filename = None

        self.typeid_filter_list = [
            'GeoFeature',
            'PartDesign::CoordinateSystem',
        ]
        if self.config['filter_sketch']:
            self.typeid_filter_list.append('Sketcher::SketchObject')

    def print_report(self, mode, data):
        b_helper.print_multi(mode, data, self.report)

    def get_obj_label(self, obj):
        return self.config["obj_name_prefix"] + obj.Label

    def rename_old_data(self, data, data_label):
        if data_label in data:
            name_old = data[data_label].name + "_old"
            if name_old in data:
                # rename recusive..
                self.rename_old_data(data, name_old)
            data[data_label].name = name_old

    # material
    def get_obj_Transparency(self, obj_Name):
        alpha = 1.0
        if "Transparency" in self.guidata[obj_Name]:
            if self.guidata[obj_Name]["Transparency"] > 0:
                alpha = (100 - self.guidata[obj_Name]["Transparency"]) / 100.0
        return alpha

    def get_obj_ShapeColor(self, obj_Name):
        rgb = (0.5, 0.5, 0.5)
        if "ShapeColor" in self.guidata[obj_Name]:
            rgb = self.guidata[obj_Name]["ShapeColor"]
        return rgb

    def get_obj_DiffuseColor(self, obj_Name, i):
        # DiffuseColor stores int values, Blender use floats
        rgba = tuple([
            float(x) / 255.0
            for x in self.guidata[obj_Name]["DiffuseColor"][i]
        ])
        return rgba

    def get_obj_rgba(self, obj_Name, mat_index=None):
        if mat_index:
            rgba = self.get_obj_DiffuseColor(obj_Name, mat_index)
            # FreeCAD stores transparency, not alpha
            alpha = 1.0
            if rgba[3] > 0:
                alpha = 1.0 - rgba[3]
            rgba = rgba[:3] + (alpha,)
        else:
            alpha = self.get_obj_Transparency(obj_Name)
            rgb = self.get_obj_ShapeColor(obj_Name)
            rgba = rgb+(alpha,)
        return rgba

    def create_new_bmat(self, bmat_name, rgba, func_data):
        bmat = bpy.data.materials.new(name=bmat_name)
        bmat.use_nodes = True
        # link bmat to PrincipledBSDFWrapper
        principled = PrincipledBSDFWrapper(bmat, is_readonly=False)
        principled.base_color = rgba[:3]
        # check for alpha
        if rgba[3] < 1.0:
            bmat.diffuse_color = rgba
            principled.alpha = rgba[3]
            bmat.blend_method = "BLEND"
        if self.config["sharemats"]:
            func_data["matdatabase"][rgba] = bmat
        return bmat

    def handle_material_per_face(self, func_data, bobj, fi, objmats, i):
        # Create new mats and attribute faces to them
        # DiffuseColor stores int values, Blender use floats
        rgba = self.get_obj_rgba(func_data["obj"].Name, i)
        bmat = None
        if self.config["sharemats"]:
            if rgba in func_data["matdatabase"]:
                bmat = func_data["matdatabase"][rgba]
                if rgba not in objmats:
                    objmats.append(rgba)
                    bobj.data.materials.append(bmat)
        if not bmat:
            if rgba in objmats:
                bmat = bobj.data.materials[objmats.index(rgba)]
        if not bmat:
            bmat_name = self.get_obj_label(func_data["obj"]) + "_" + str(len(objmats))
            bmat = self.create_new_bmat(bmat_name, rgba, func_data)
            objmats.append(rgba)
            # TODO: please check if this is really correct..
            bobj.data.materials.append(bmat)

        # assigne materials to polygons
        for fj in range(func_data["matindex"][i]):
            bobj.data.polygons[fi+fj].material_index = objmats.index(rgba)
        fi += func_data["matindex"][i]

    def handle_material_multi(self, func_data, bobj):
        # we have per-face materials.
        fi = 0
        objmats = []
        for i in range(len(func_data["matindex"])):
            self.handle_material_per_face(func_data, bobj, fi, objmats, i)

    def handle_material_single(self, func_data, bobj):
        # one material for the whole object
        rgba = self.get_obj_rgba(func_data["obj"].Name)
        bmat = None
        if self.config["sharemats"]:
            if rgba in func_data["matdatabase"]:
                bmat = func_data["matdatabase"][rgba]
            else:
                # print("not found in db:",rgba,"in",matdatabase)
                pass
        if not bmat:
            bmat_name = self.get_obj_label(func_data["obj"])
            bmat = self.create_new_bmat(bmat_name, rgba, func_data)
        bobj.data.materials.append(bmat)

    def handle_material_new(self, func_data, bobj):
        # check if we have a material at all...
        if func_data["obj"].Name in self.guidata:
            # check if we have 'per face' or 'object' coloring.
            if (
                func_data["matindex"]
                and ("DiffuseColor" in self.guidata[func_data["obj"].Name])
                and (len(func_data["matindex"]) == len(
                    self.guidata[func_data["obj"].Name]["DiffuseColor"])
                )
            ):
                self.handle_material_multi(func_data, bobj)
            else:
                self.handle_material_single(func_data, bobj)

    # object handling
    def hascurves(self, shape):
        """Check if shape has curves."""
        import Part
        for e in shape.Edges:
            if not isinstance(e.Curve, (Part.Line, Part.LineSegment)):
                return True
        return False

    def handle_placement(self, bobj):
        """Handle placement."""
        if self.config["placement"]:
            # print ("placement:",placement)
            bobj.location = self.config["placement"].Base.multiply(
                self.config["scale"])
            m = bobj.rotation_mode
            bobj.rotation_mode = 'QUATERNION'
            if self.config["placement"].Rotation.Angle:
                # FreeCAD Quaternion is XYZW while Blender is WXYZ
                q = (
                    (self.config["placement"].Rotation.Q[3], )
                    + self.config["placement"].Rotation.Q[:3]
                )
                bobj.rotation_quaternion = (q)
                bobj.rotation_mode = m
            bobj.scale = (
                self.config["scale"],
                self.config["scale"],
                self.config["scale"]
            )

    def add_or_update_blender_obj(self, func_data):
        """Create or update object with mesh and material data."""
        pre_line = func_data["pre_line"]
        bobj = None
        obj_label = self.get_obj_label(func_data["obj"])
        if self.config["update"]:
            # locate existing object (object with same name)
            if obj_label in bpy.data.objects:
                bobj = bpy.data.objects[obj_label]
                print(
                    pre_line +
                    "Replacing existing object mesh: {}"
                    "".format(obj_label)
                )
                # rename old mesh - this way the new mesh can get the orig. name.
                self.rename_old_data(bpy.data.meshes, obj_label)

        bmesh = bpy.data.meshes.new(name=obj_label)
        bmesh.from_pydata(
            func_data["verts"],
            func_data["edges"],
            func_data["faces"]
        )
        bmesh.update()
        if bobj:
            # update only the mesh of existing object.
            # copy old materials to new mesh:
            for mat in bobj.data.materials:
                bmesh.materials.append(mat)
            bobj.data = bmesh
            # self.handle_material_update(func_data, bobj)
        else:
            # create new object
            bobj = bpy.data.objects.new(obj_label, bmesh)
            self.handle_placement(bobj)
            self.handle_material_new(func_data, bobj)

        if self.config['update']:
            if bobj.name not in func_data["collection"].objects:
                func_data["collection"].objects.link(bobj)
            else:
                print(
                    pre_line +
                    "'{}' already in collection '{}'"
                    "".format(bobj.name, func_data["collection"])
                )
        else:
            func_data["collection"].objects.link(bobj)
        # bpy.context.scene.objects.active = func_data["obj"]
        # obj.select = True

    # shape
    def handle_shape_edge(self, func_data, edge):
        if self.hascurves(edge):
            # TODO use tessellation value
            dv = edge.discretize(9)
            for i in range(len(dv)-1):
                dv1 = [dv[i].x, dv[i].y, dv[i].z]
                dv2 = [dv[i+1].x, dv[i+1].y, dv[i+1].z]
                if dv1 not in func_data["verts"]:
                    func_data["verts"].append(dv1)
                if dv2 not in func_data["verts"]:
                    func_data["verts"].append(dv2)
                func_data["edges"].append([
                    func_data["verts"].index(dv1),
                    func_data["verts"].index(dv2)
                ])
        else:
            e = []
            for vert in edge.Vertexes:
                # TODO discretize non-linear edges
                v = [vert.X, vert.Y, vert.Z]
                if v not in func_data["verts"]:
                    func_data["verts"].append(v)
                e.append(func_data["verts"].index(v))
            func_data["edges"].append(e)

    def handle_shape_face_as_polygon(self, func_data, face, faceedges):
        import Part
        if (
            (len(face.Wires) > 1)
            or (not isinstance(face.Surface, Part.Plane))
            or self.hascurves(face)
        ):
            # face has holes or is curved, so we need to triangulate it
            rawdata = face.tessellate(self.config["tessellation"])
            for v in rawdata[0]:
                vl = [v.x, v.y, v.z]
                if vl not in func_data["verts"]:
                    func_data["verts"].append(vl)
            for f in rawdata[1]:
                nf = []
                for vi in f:
                    nv = rawdata[0][vi]
                    nf.append(func_data["verts"].index([nv.x, nv.y, nv.z]))
                func_data["faces"].append(nf)
            func_data["matindex"].append(len(rawdata[1]))
        else:
            f = []
            ov = face.OuterWire.OrderedVertexes
            for v in ov:
                vl = [v.X, v.Y, v.Z]
                if vl not in func_data["verts"]:
                    func_data["verts"].append(vl)
                f.append(func_data["verts"].index(vl))
            # FreeCAD doesn't care about func_data["verts"] order.
            # Make sure our loop goes clockwise
            c = face.CenterOfMass
            v1 = ov[0].Point.sub(c)
            v2 = ov[1].Point.sub(c)
            n = face.normalAt(0, 0)
            if (v1.cross(v2)).getAngle(n) > 1.57:
                # inverting func_data["verts"] order if the direction is couterclockwise
                f.reverse()
            func_data["faces"].append(f)
            func_data["matindex"].append(1)
        for e in face.Edges:
            faceedges.append(e.hashCode())

    def handle_shape_faces(self, func_data, shape, faceedges):
        if TRIANGULATE:
            # triangulate and make faces
            rawdata = shape.tessellate(self.config["tessellation"])
            for v in rawdata[0]:
                func_data["verts"].append([v.x, v.y, v.z])
            for f in rawdata[1]:
                func_data["faces"].append(f)
            for face in shape.Faces:
                for e in face.Edges:
                    faceedges.append(e.hashCode())
        else:
            # write FreeCAD faces as polygons when possible
            for face in shape.Faces:
                self.handle_shape_face_as_polygon(func_data, face, faceedges)

    def create_mesh_from_shape(self, func_data):
        """Create mesh from shape."""
        # a placeholder to store edges that belong to a face
        faceedges = []
        shape = func_data["obj"].Shape
        if self.config["placement"]:
            self.config["placement"] = func_data["obj"].Placement
            shape = func_data["obj"].Shape.copy()
            shape.Placement = self.config["placement"].\
                inverse().multiply(shape.Placement)
        if shape.Faces:
            self.handle_shape_faces(func_data, shape, faceedges)
        # Treat remaining edges (that are not in faces)
        for edge in shape.Edges:
            if not (edge.hashCode() in faceedges):
                self.handle_shape_edge(func_data, edge)

    # mesh
    def create_mesh_from_mesh(self, func_data):
        # convert freecad mesh to blender mesh
        mesh = func_data["obj"].Mesh
        if self.config["placement"]:
            self.config["placement"] = func_data["obj"].Placement
            # in meshes, this zeroes the placement
            mesh = func_data["obj"].Mesh.copy()
        t = mesh.Topology
        func_data["verts"] = [[v.x, v.y, v.z] for v in t[0]]
        func_data["faces"] = t[1]

    # part
    def part_collection_add_or_update(self, func_data, collection_label):
        temp_collection = None
        # if self.config["update"]:
        #     if collection_label in bpy.data.collections:
        #         temp_collection = bpy.data.collections[collection_label]
        # else:
        #     self.rename_old_data(bpy.data.collections, collection_label)
        # if temp_collection:
        #     bpy.context.scene.collection.children.link(self.fcstd_collection)
        # else:
        #     func_data["current_collection"] = bpy.data.collections.new(collection_label)
        if collection_label in bpy.data.collections:
            temp_collection = bpy.data.collections[collection_label]
        else:
            temp_collection = bpy.data.collections.new(collection_label)
            func_data["collection"].children.link(temp_collection)
        func_data["collection_parent"] = func_data["collection"]
        func_data["collection"] = temp_collection

    def handle_part(self, func_data):
        """Handle part."""
        pre_line = func_data["pre_line"]
        part_label = self.get_obj_label(func_data["obj"])
        print(pre_line + "handle_part: '{}'".format(part_label))
        self.part_collection_add_or_update(func_data, part_label)
        # print(pre_line + "check sub elements")
        group = func_data["obj"].Group
        if len(group) > 0:
            # print(pre_line + "Group: ", group)
            # print(pre_line + "***")
            # fc_helper.print_objects(group)
            sub_objects = fc_helper.filtered_objects(
                group,
                include_only_visible=True
            )
            pre_sub = pre_line + "|   "
            print(pre_line + "|" + ("*"*42))
            print(pre_sub)
            print(pre_sub + "Filterd SUB objects")
            fc_helper.print_objects(sub_objects, pre_line=pre_sub)
            print(pre_sub + "Import Recusive:")
            for obj in sub_objects:
                self.import_obj(
                    obj=obj,
                    collection=func_data["collection"],
                    collection_parent=func_data["collection_parent"],
                    pre_line=pre_sub
                )
            print(pre_sub)
            print(pre_line + "|" + ("*"*42))
        else:
            print("→ no group childs.")
        # reset current collection
        func_data["collection"] = func_data["collection_parent"]
        func_data["collection_parent"] = None

    # main object import
    def import_obj(self, obj=None, collection=None, collection_parent=None, pre_line=""):
        "Import Object."
        # import some FreeCAD modules needed below.
        # After "import FreeCAD" these modules become available
        # import Part
        # import PartDesign

        # dict for storing all data
        func_data = {
            "obj": obj,
            "verts": [],
            "edges": [],
            "faces": [],
            # face to material relationship
            "matindex": [],
            # to store reusable materials
            "matdatabase": {},
            # name: "Unnamed",
            "collection": collection,
            "collection_parent": collection_parent,
            "pre_line": pre_line,
        }
        # func_data["matindex"]

        if obj:
            if obj.isDerivedFrom("Part::Feature"):
                self.create_mesh_from_shape(func_data)
            elif obj.isDerivedFrom("Mesh::Feature"):
                self.create_mesh_from_mesh(func_data)
            # elif obj.isDerivedFrom("PartDesign::Body"):
            #     self.create_mesh_from_Body(func_data)
            elif obj.isDerivedFrom("App::Part"):
                self.handle_part(func_data)
            # elif obj.isDerivedFrom("App::Link"):
            #     self.config["report"]({'WARNING'}, (
            #         pre_line +
            #         "'{}' ('{}') of type '{}': "
            #         "Warning: Link handling is highly experimental!!"
            #         "".format(obj.Label, obj.Name, obj.TypeId)
            #     ))
            #     self.handle_link(func_data)
            else:
                self.config["report"]({'WARNING'}, (
                    pre_line +
                    "Unable to load '{}' ('{}') of type '{}'. "
                    "(Type Not implemented yet)."
                    "".format(obj.Label, obj.Name, obj.TypeId)
                ))

            if (
                func_data["verts"]
                and (func_data["faces"] or func_data["edges"])
            ):
                self.add_or_update_blender_obj(func_data)

    def check_visibility_skip(self, obj):
        """Check if obj is visible."""
        result = True
        if (
            self.config["skiphidden"]
            and obj.Name in self.guidata
            and "Visibility" in self.guidata[obj.Name]
        ):
            if self.guidata[obj.Name]["Visibility"] is False:
                result = False
        return result

    def import_doc_content(self, doc):
        obj_list = fc_helper.get_root_objects(
            doc,
            filter_list=self.typeid_filter_list
        )
        print("-"*21)

        self.config["report"]({'INFO'}, (
            "found {} objects in '{}'"
            "".format(len(obj_list), self.doc_filename)
        ))
        fc_helper.print_objects(
            obj_list,
            show_lists=True,
            show_list_details=True
        )
        print("-"*21)
        self.config["report"]({'INFO'}, "Import:")
        for obj in obj_list:
            if self.check_visibility_skip(obj):
                fc_helper.print_obj(obj)
                self.import_obj(obj=obj, collection=self.fcstd_collection)

    def prepare_collection(self):
        if self.config["update"]:
            if self.doc_filename in bpy.data.collections:
                self.fcstd_collection = bpy.data.collections[self.doc_filename]
        if not self.fcstd_collection:
            self.fcstd_collection = bpy.data.collections.new(self.doc_filename)
            bpy.context.scene.collection.children.link(self.fcstd_collection)

    def load_guidata(self):
        """Check if we have a GUI document."""
        zdoc = zipfile.ZipFile(self.config["filename"])
        if zdoc:
            if "GuiDocument.xml" in zdoc.namelist():
                gf = zdoc.open("GuiDocument.xml")
                self.guidata = gf.read()
                gf.close()
                Handler = FreeCAD_xml_handler()
                xml.sax.parseString(self.guidata, Handler)
                self.guidata = Handler.guidata
                for key, properties in self.guidata.items():
                    # open each diffusecolor files and retrieve values
                    # first 4 bytes are the array length,
                    # then each group of 4 bytes is abgr
                    if "DiffuseColor" in properties:
                        # print ("opening:",self.guidata[key]["DiffuseColor"])
                        df = zdoc.open(self.guidata[key]["DiffuseColor"])
                        buf = df.read()
                        # print (buf," length ",len(buf))
                        df.close()
                        cols = []
                        for i in range(1, int(len(buf)/4)):
                            cols.append(
                                (buf[i*4+3], buf[i*4+2], buf[i*4+1], buf[i*4]))
                        self.guidata[key]["DiffuseColor"] = cols
            zdoc.close()
        # print ("self.guidata:",self.guidata)

    def prepare_freecad_import(self):
        # append the FreeCAD path specified in addon preferences
        user_preferences = bpy.context.preferences
        addon_prefs = user_preferences.addons["io_import_fcstd"].preferences
        path = addon_prefs.filepath
        if path:
            if os.path.isfile(path):
                path = os.path.dirname(path)
            print("Configured FreeCAD path:", path)
            sys.path.append(path)
        else:
            print("FreeCAD path is not configured in preferences")

    def import_fcstd(self, filename=None):
        """Read a FreeCAD .FCStd file and creates Blender objects."""
        if filename:
            self.config["filename"] = filename
        try:
            self.prepare_freecad_import()
            import FreeCAD
        # except ModuleNotFoundError as e:
        except Exception as e:
            self.config["report"](
                {'ERROR'},
                "Unable to import the FreeCAD Python module. \n"
                "\n"
                "Make sure it is installed on your system"
                "and compiled with Python3 (same version as Blender).\n"
                "It must also be found by Python, "
                "you might need to set its path in this Addon preferences"
                "(User preferences->Addons->expand this addon).\n"
                + str(e)
            )
            return {'CANCELLED'}

        self.load_guidata()

        # Context Managers not implemented..
        # see https://docs.python.org/3.8/reference/compound_stmts.html#with
        # with FreeCAD.open(self.config["filename"]) as doc:
        # so we use the classic try finally block:
        try:
            # doc = FreeCAD.open('/home/stefan/mydata/freecad/tests/linking_test/Linking.FCStd')
            doc = FreeCAD.open(self.config["filename"])
            docname = doc.Name
            self.doc_filename = docname + ".FCStd"
            if not doc:
                self.config["report"](
                    {'ERROR'},
                    "Unable to open the given FreeCAD file '{}'"
                    "".format(self.config["filename"])
                )
                return {'CANCELLED'}
            else:
                # print ("Transferring",len(doc.Objects),"objects to Blender")
                self.prepare_collection()
                self.import_doc_content(doc)
        except Exception as e:
            self.config["report"]({'ERROR'}, str(e))
            raise e
        finally:
            # FreeCAD.closeDocument('Linking')
            FreeCAD.closeDocument(docname)
        print("Import finished without errors")
        return {'FINISHED'}


def main_test():
    "Main Tests."
    pass


if __name__ == '__main__':
    main_test()
