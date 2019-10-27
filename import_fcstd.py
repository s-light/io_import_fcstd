#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Import FreeCAD files to blender."""

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
        """Init."""
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
        self.doc = None
        self.doc_filename = None
        self.guidata = {}

        self.fcstd_collection = None

        self.typeid_filter_list = [
            'GeoFeature',
            'PartDesign::CoordinateSystem',
        ]
        if self.config['filter_sketch']:
            self.typeid_filter_list.append('Sketcher::SketchObject')

    def print_report(self, mode, data):
        """Multi print handling."""
        b_helper.print_multi(mode, data, self.report)

    def print_obj(self, obj, pre_line="", post_line="", end="\n"):
        """Print object with nice formating."""
        message = (
            pre_line +
            "'{}' ('{}' <{}>)"
            "".format(obj.Label, obj.Name, obj.TypeId)
            + post_line
        )
        # print(message, end=end)
        self.config["report"](
            {'INFO'},
            message
        )

    def get_obj_label(self, obj):
        """Get object label with optional prefix."""
        label = None
        if hasattr(obj, "LinkedObject"):
            obj_linked_label = "NONE"
            if obj.LinkedObject:
                obj_linked_label = obj.LinkedObject.Label
            label = (
                obj_linked_label
                + "__"
                + obj.Label
            )
        else:
            obj_label = "NONE"
            if obj:
                obj_label = obj.Label
            label = obj_label
        if label:
            self.config["obj_name_prefix"] + label
        return label

    def get_linkedobj_label(self, obj):
        """Get linkedobject label with optional prefix."""
        label = None
        if hasattr(obj, "LinkedObject"):
            obj_linked_label = "NONE"
            if obj.LinkedObject:
                obj_linked_label = obj.LinkedObject.Label
            label = (
                self.config["obj_name_prefix"]
                + obj_linked_label
            )
        return label

    def rename_old_data(self, data, data_label):
        """Recusive add '_old' to data object."""
        if data_label in data:
            name_old = data[data_label].name + "_old"
            if name_old in data:
                # rename recusive..
                self.rename_old_data(data, name_old)
            data[data_label].name = name_old

    # material
    def get_obj_Transparency(self, obj_Name):
        """Get object Transparency and convert to blender units."""
        alpha = 1.0
        if "Transparency" in self.guidata[obj_Name]:
            if self.guidata[obj_Name]["Transparency"] > 0:
                alpha = (100 - self.guidata[obj_Name]["Transparency"]) / 100.0
        return alpha

    def get_obj_ShapeColor(self, obj_Name):
        """Get object ShapeColor and convert to blender units."""
        rgb = (0.5, 0.5, 0.5)
        if "ShapeColor" in self.guidata[obj_Name]:
            rgb = self.guidata[obj_Name]["ShapeColor"]
        return rgb

    def get_obj_DiffuseColor(self, obj_Name, i):
        """Get object DiffuseColor and convert to blender units."""
        # DiffuseColor stores int values, Blender use floats
        rgba = tuple([
            float(x) / 255.0
            for x in self.guidata[obj_Name]["DiffuseColor"][i]
        ])
        return rgba

    def get_obj_rgba(self, obj_Name, mat_index=None):
        """Get object rgba value in blender usable format."""
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
        """Create new blender material."""
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
        """Handle material for face."""
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
            bmat_name = self.get_obj_label(
                func_data["obj"]) + "_" + str(len(objmats))
            bmat = self.create_new_bmat(bmat_name, rgba, func_data)
            objmats.append(rgba)
            # TODO: please check if this is really correct..
            bobj.data.materials.append(bmat)

        # assigne materials to polygons
        for fj in range(func_data["matindex"][i]):
            bobj.data.polygons[fi+fj].material_index = objmats.index(rgba)
        fi += func_data["matindex"][i]

    def handle_material_multi(self, func_data, bobj):
        """Handle multi material."""
        # we have per-face materials.
        fi = 0
        objmats = []
        for i in range(len(func_data["matindex"])):
            self.handle_material_per_face(func_data, bobj, fi, objmats, i)

    def handle_material_single(self, func_data, bobj):
        """Handle single material."""
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
        """Handle material creation."""
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

    # ##########################################
    # object handling

    def hascurves(self, shape):
        """Check if shape has curves."""
        import Part
        for e in shape.Edges:
            if not isinstance(e.Curve, (Part.Line, Part.LineSegment)):
                return True
        return False

    def handle_placement(self, obj, bobj, enable_scale=True, relative=False):
        """Handle placement."""
        if self.config["placement"]:
            # print ("placement:",placement)
            new_loc = (obj.Placement.Base * self.config["scale"])
            # attention: multiply does in-place change.
            # so if you call it multiple times on the same value
            # you get really strange results...
            # new_loc = obj.Placement.Base.multiply(self.config["scale"])
            if relative:
                # print("new_loc", new_loc)
                # print("!!! relative")
                # print(
                #     "x: {} + {} = {}"
                #     "".format(
                #         bobj.location.x,
                #         new_loc.x,
                #         bobj.location.x + new_loc.x
                #     )
                # )
                bobj.location.x = bobj.location.x + new_loc.x
                bobj.location.y = bobj.location.y + new_loc.y
                bobj.location.z = bobj.location.z + new_loc.z
            else:
                bobj.location = new_loc
            m = bobj.rotation_mode
            bobj.rotation_mode = 'QUATERNION'
            if obj.Placement.Rotation.Angle:
                # FreeCAD Quaternion is XYZW while Blender is WXYZ
                q = (
                    (obj.Placement.Rotation.Q[3], )
                    + obj.Placement.Rotation.Q[:3]
                )
                bobj.rotation_quaternion = (q)
                bobj.rotation_mode = m
            if enable_scale:
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
                # rename old mesh -
                # this way the new mesh can get the original name.
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
            self.handle_placement(func_data["obj"], bobj)
            self.handle_material_new(func_data, bobj)
            func_data["bobj"] = bobj

        if self.config['update']:
            if bobj.name not in func_data["collection"].objects:
                func_data["collection"].objects.link(bobj)
                bobj.parent = func_data["bobj_parent"]
            else:
                print(
                    pre_line +
                    "'{}' already in collection '{}'"
                    "".format(bobj.name, func_data["collection"])
                )
        else:
            func_data["collection"].objects.link(bobj)
            bobj.parent = func_data["bobj_parent"]
        # bpy.context.scene.objects.active = func_data["obj"]
        # obj.select = True

    def sub_collection_add_or_update(self, func_data, collection_label):
        """Part-Collection handle add or update."""
        temp_collection = None
        temp_empty = None
        # if self.config["update"]:
        #     if collection_label in bpy.data.collections:
        #         temp_collection = bpy.data.collections[collection_label]
        # else:
        #     self.rename_old_data(bpy.data.collections, collection_label)
        # if temp_collection:
        #     bpy.context.scene.collection.children.link(self.fcstd_collection)
        # else:
        #     func_data["current_collection"] = \
        #         bpy.data.collections.new(collection_label)
        # check for collection
        if collection_label in bpy.data.collections:
            temp_collection = bpy.data.collections[collection_label]
        else:
            temp_collection = bpy.data.collections.new(collection_label)
            func_data["collection"].children.link(temp_collection)

        # check for empty
        if collection_label in bpy.data.objects:
            temp_empty = bpy.data.objects[collection_label]
        else:
            # create empty
            temp_empty = bpy.data.objects.new(
                name=collection_label,
                object_data=None
            )
            temp_collection.objects.link(temp_empty)
            temp_empty.parent = func_data["bobj_parent"]
        # update func_data links
        func_data["collection_parent"] = func_data["collection"]
        func_data["collection"] = temp_collection
        func_data["bobj_parent"] = temp_empty

    def handle__sub_objects(
        self,
        func_data,
        sub_objects,
        include_only_visible=True
    ):
        """Handle sub objects."""
        pre_line = func_data["pre_line"]
        sub_label = self.get_obj_label(func_data["obj"])
        # print(pre_line + "handle_part: '{}'".format(sub_label))
        self.sub_collection_add_or_update(func_data, sub_label)
        if len(sub_objects) > 0:
            sub_objects = fc_helper.filtered_objects(
                sub_objects,
                include_only_visible=include_only_visible
            )
            print(
                b_helper.colors.bold
                + b_helper.colors.fg.purple
                + pre_line + "Import Recusive:"
                + b_helper.colors.reset
            )
            for obj in sub_objects:
                self.print_obj(obj, pre_line + "- ")
                self.import_obj(
                    obj=obj,
                    collection=func_data["collection"],
                    collection_parent=func_data["collection_parent"],
                    bobj_parent=func_data["bobj_parent"],
                    pre_line=pre_line + '    '
                )
        else:
            print(
                b_helper.colors.fg.darkgrey
                + pre_line + "→ no childs."
                + b_helper.colors.reset
            )
        # reset current collection
        # func_data["collection"] = func_data["collection_parent"]
        # func_data["collection_parent"] = None

    # Arrays and similar
    def handle__ObjectWithElementList(self, func_data):
        """Handle Part::Feature objects."""
        # pre_line = func_data["pre_line"]
        # obj = func_data["obj"]
        # self.config["report"]({'WARNING'}, (
        #     pre_line +
        #     "'{}' ('{}') of type '{}': "
        #     "Warning: ElementList handling is highly experimental!!"
        #     "".format(obj.Label, obj.Name, obj.TypeId)
        # ))
        # fc_helper.print_objects(
        #     func_data["obj"].ElementList,
        #     pre_line=pre_line
        # )
        self.handle__sub_objects(
            func_data,
            func_data["obj"].ElementList,
            include_only_visible=False
        )

    # ##########################################
    # 'real' object types

    # Part::Feature
    def handle_shape_edge(self, func_data, edge):
        """Handle edges that are not part of a face."""
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

    def convert_face_to_polygon(self, func_data, face, faceedges):
        """Convert face to polygons."""
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
                # inverting func_data["verts"] order
                # if the direction is counterclockwise
                f.reverse()
            func_data["faces"].append(f)
            func_data["matindex"].append(1)
        for e in face.Edges:
            faceedges.append(e.hashCode())

    def handle_shape_faces(self, func_data, shape, faceedges):
        """Convert faces to polygons."""
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
                self.convert_face_to_polygon(func_data, face, faceedges)

    def create_mesh_from_shape(self, func_data):
        """Create mesh from shape."""
        # a placeholder to store edges that belong to a face
        faceedges = []
        shape = func_data["obj"].Shape
        if self.config["placement"]:
            shape = func_data["obj"].Shape.copy()
            shape.Placement = \
                func_data["obj"].Placement.inverse().multiply(shape.Placement)
        if shape.Faces:
            self.handle_shape_faces(func_data, shape, faceedges)
        # Treat remaining edges (that are not in faces)
        for edge in shape.Edges:
            if not (edge.hashCode() in faceedges):
                self.handle_shape_edge(func_data, edge)

    def handle__PartFeature(self, func_data):
        """Handle Part::Feature objects."""
        self.create_mesh_from_shape(func_data)

    # Part::FeaturePhython
    def handle__PartFeaturePython_Array(self, func_data):
        """Handle Part::Feature objects."""
        # pre_line = func_data["pre_line"]
        # print(
        #     pre_line + "ElementList:",
        #     func_data["obj"].ElementList
        # )
        # print(pre_line + "Count:", func_data["obj"].Count)
        # print(pre_line + "ExpandArray:", func_data["obj"].ExpandArray)
        # print(pre_line + "expand Array")
        # TODO: this currently has only any effect in the GUI
        func_data["obj"].ExpandArray = True
        self.doc.recompute()
        # print(pre_line + "ExpandArray:", func_data["obj"].ExpandArray)
        # print(
        #     pre_line + "ElementList:",
        #     func_data["obj"].ElementList
        # )
        self.handle__ObjectWithElementList(func_data)

    # Mesh::Feature
    def handle__MeshFeature(self, func_data):
        """Convert freecad mesh to blender mesh."""
        mesh = func_data["obj"].Mesh
        if self.config["placement"]:
            # in meshes, this zeroes the placement
            mesh = func_data["obj"].Mesh.copy()
        t = mesh.Topology
        func_data["verts"] = [[v.x, v.y, v.z] for v in t[0]]
        func_data["faces"] = t[1]

    # App::Part
    def handle__AppPart(self, func_data):
        """Handle App:Part type."""
        # pre_line = func_data["pre_line"]
        self.handle__sub_objects(
            func_data,
            func_data["obj"].Group
        )

    # App::Link*
    def add_or_update_collection_instance(
        self,
        func_data,
        obj,
        obj_label,
        obj_parent,
        linkedobj_label,
    ):
        """Add or update collection instance object."""
        pre_line = func_data["pre_line"]
        base_collection = None
        if linkedobj_label in bpy.data.collections:
            base_collection = bpy.data.collections[linkedobj_label]
            flag_new = False
            if obj_label not in bpy.data.objects:
                # create a instance of the collection
                result_bobj = bpy.data.objects.new(
                    name=obj_label,
                    object_data=None
                )
                result_bobj.instance_collection = base_collection
                result_bobj.instance_type = 'COLLECTION'
                print(pre_line + "result_bobj", result_bobj)
                flag_new = True
                result_bobj.empty_display_size = 0.01
                func_data["collection"].objects.link(result_bobj)
                # result_bobj.parent = func_data["bobj_parent"]
                result_bobj.parent = obj_parent
                bpy.context.scene.collection.objects.unlink(result_bobj)

            if self.config["update"] or flag_new:
                bobj = bpy.data.objects[obj_label]
                # print(pre_line + "bobj.location", str(bobj.location))
                self.handle_placement(obj, bobj, enable_scale=False)
                # print(pre_line + "bobj.location", bobj.location)
                # print(
                #     pre_line + "obj_parent.Placement.Base",
                #     obj_parent.Placement.Base
                # )
                self.handle_placement(
                    obj_parent,
                    bobj,
                    enable_scale=False,
                    relative=True
                )
                # print(pre_line + "bobj.location", bobj.location)
            else:
                self.config["report"]({'WARNING'}, (
                    pre_line +
                    "Warning: can't add or update instance. "
                    "'{}' collection not found."
                    "".format(linkedobj_label)
                ))
                return False

    def add_or_update_link_target(
        self,
        func_data,
        obj,
        obj_linked,
        linkedobj_label,
    ):
        """Add or update link target object."""
        pre_line = func_data["pre_line"]
        if linkedobj_label in bpy.data.collections:
            print(pre_line + "TODO: implement update.")
        else:
            # create new
            # print(pre_line + "create new!")
            self.print_obj(
                obj,
                pre_line=pre_line + "# ",
                post_line=" → import Link Target."
            )
            func_data = self.import_obj(
                obj=obj_linked,
                collection=func_data["collection"],
                collection_parent=func_data["collection_parent"],
                bobj_parent=func_data["bobj_parent"],
                pre_line=pre_line + '    '
            )
            # if func_data["bobj"]:
            #     base_collection = func_data["bobj"]
            if func_data["collection"]:
                base_collection = func_data["collection"]
            print(pre_line + "created object: ", base_collection)
            if base_collection:
                # hide this internal object.
                # we use only the instances..
                base_collection.hide_render = False
                base_collection.hide_select = True
                base_collection.hide_viewport = False
            func_data["collection"] = func_data["collection_parent"]
            func_data["collection_parent"] = None

    def handle__AppLink(self, func_data):
        """Handle App::Link objects."""
        pre_line = func_data["pre_line"]
        obj = func_data["obj"]
        obj_linked = func_data["obj"].LinkedObject
        print("handle__AppLink: obj", obj)
        self.config["report"]({'WARNING'}, (
            pre_line +
            "'{}' ('{}') of type '{}': "
            "Warning: App::Link handling is highly experimental!!"
            "".format(obj.Label, obj.Name, obj.TypeId)
        ))
        obj_label = self.get_obj_label(obj)
        print(pre_line + "obj_label:", obj_label)
        linkedobj_label = self.get_linkedobj_label(obj)
        print(pre_line + "linkedobj_label:", linkedobj_label)
        obj_linked_label = self.get_obj_label(obj_linked)
        print(pre_line + "obj_linked_label:", obj_linked_label)

        fc_helper.print_obj(obj, pre_line=pre_line)
        fc_helper.print_obj(obj_linked, pre_line=pre_line)
        if hasattr(obj_linked, "LinkedObject"):
            fc_helper.print_obj(obj_linked.LinkedObject, pre_line=pre_line)

        if len(obj.ElementList) > 0:
            self.handle__ObjectWithElementList(func_data)
        else:
            self.sub_collection_add_or_update(func_data, obj_label)
            self.handle__AppLinkElement(func_data)

    def handle__AppLinkElement(self, func_data):
        """Handle App::LinkElement objects."""
        pre_line = func_data["pre_line"]
        obj = func_data["obj"]
        obj_linked = func_data["obj"].LinkedObject
        if hasattr(obj_linked, "LinkedObject"):
            # if we have Arrays they  have a intermediet link object..
            # we skip this..
            obj_linked = obj_linked.LinkedObject
        obj_parent = obj.InList[0]
        # self.config["report"]({'ERROR'}, (
        #     pre_line +
        #     "'{}' ('{}') of type '{}': "
        #     "ERROR: handle__AppLinkElement EXPERIMENTAL!"
        #     "".format(obj.Label, obj.Name, obj.TypeId)
        # ))

        # print(pre_line + "collection:", func_data["collection"])

        obj_label = self.get_obj_label(obj)
        print(pre_line + "obj_label:", obj_label)
        linkedobj_label = self.get_linkedobj_label(obj)
        print(pre_line + "linkedobj_label:", linkedobj_label)
        # obj_linked_label = self.get_obj_label(obj_linked)
        # print(pre_line + "obj_linked_label:", obj_linked_label)
        fc_helper.print_obj(obj, pre_line=pre_line)
        fc_helper.print_obj(obj_linked, pre_line=pre_line)
        # fc_helper.print_obj(obj_linked.LinkedObject, pre_line=pre_line)

        self.add_or_update_link_target(
            func_data,
            obj,
            obj_linked,
            linkedobj_label,
        )

        self.add_or_update_collection_instance(
            func_data,
            obj,
            obj_label,
            obj_parent,
            linkedobj_label,
        )

    # ##########################################
    # main object import
    def import_obj(
        self,
        obj=None,
        collection=None,
        collection_parent=None,
        bobj_parent=None,
        pre_line=""
    ):
        """Import Object."""
        # import some FreeCAD modules needed below.
        # After "import FreeCAD" these modules become available
        # import Part
        # import PartDesign
        # print("import_obj: obj", obj)
        # dict for storing all data
        func_data = {
            "obj": obj,
            "bobj": None,
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
            "bobj_parent": bobj_parent,
            "pre_line": pre_line,
        }
        # func_data["matindex"]
        if obj:
            if (
                obj.isDerivedFrom("Part::FeaturePython")
                and hasattr(obj, 'ExpandArray')
                and hasattr(obj, 'ElementList')
            ):
                self.handle__PartFeaturePython_Array(func_data)
            elif obj.isDerivedFrom("Part::Feature"):
                self.handle__PartFeature(func_data)
            elif obj.isDerivedFrom("Mesh::Feature"):
                self.handle__MeshFeature(func_data)
            # elif obj.isDerivedFrom("PartDesign::Body"):
            #     self.create_mesh_from_Body(func_data)
            # elif obj.isDerivedFrom("XXXXXX"):
            #     self.handle__XXXXXX(func_data)
            elif obj.isDerivedFrom("App::Part"):
                self.handle__AppPart(func_data)
            elif obj.isDerivedFrom("App::LinkElement"):
                self.handle__AppLinkElement(func_data)
            elif obj.isDerivedFrom("App::Link"):
                self.handle__AppLink(func_data)
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
        return func_data

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
        """Import document content = filterd objects."""
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
                self.print_obj(obj, pre_line="- ")
                self.import_obj(
                    obj=obj,
                    collection=self.fcstd_collection,
                    pre_line="    ",
                )
            else:
                pre = b_helper.colors.fg.darkgrey + "- "
                post = " (hidden)" + b_helper.colors.reset
                self.print_obj(obj, pre_line=pre, post_line=post)

    def prepare_collection(self):
        """Prepare main import collection."""
        if self.config["update"]:
            if self.doc_filename in bpy.data.collections:
                self.fcstd_collection = bpy.data.collections[self.doc_filename]
        if not self.fcstd_collection:
            self.fcstd_collection = bpy.data.collections.new(self.doc_filename)
            bpy.context.scene.collection.children.link(self.fcstd_collection)

    def load_guidata(self):
        """Check if we have a GUI document."""
        self.config["report"]({'INFO'}, "load guidata..")
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
        self.config["report"]({'INFO'}, "load guidata done.")

    def prepare_freecad_import(self):
        """Prepare FreeCAD import."""
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
            # doc = FreeCAD.open(
            #     "/home/stefan/mydata/freecad/tests/linking_test/Linking.FCStd")
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
                self.config["report"](
                    {'INFO'},
                    "File Opend. '{}'"
                    "".format(self.config["filename"])
                )
                self.doc = doc
                self.config["report"]({'INFO'}, "recompute..")
                self.doc.recompute()
                # self.config["report"]({'INFO'}, "importLinks..")
                # self.doc.importLinks()
                # importLinks is currently not reliable..
                # self.config["report"]({'INFO'}, "recompute..")
                # self.doc.recompute()
                self.prepare_collection()
                self.import_doc_content(doc)
        except Exception as e:
            self.config["report"]({'ERROR'}, str(e))
            raise e
        finally:
            FreeCAD.closeDocument(docname)
        print("Import finished.")
        return {'FINISHED'}


def main_test():
    """Tests."""
    pass


if __name__ == '__main__':
    main_test()
