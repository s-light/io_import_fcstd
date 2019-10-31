#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Import FreeCAD files to blender."""

import sys
import bpy
import os

from .. import freecad_helper as fc_helper
from .. import blender_helper as b_helper

from . import guidata

from bpy_extras.node_shader_utils import PrincipledBSDFWrapper

# set to True to triangulate all faces (will loose multimaterial info)
TRIANGULATE = False


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
        path_to_freecad=None,
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
        self.path_to_freecad = path_to_freecad
        self.report = report

        print('config', self.config)
        self.doc = None
        self.doc_filename = None
        self.guidata = {}

        self.fcstd_collection = None
        self.fcstd_empty = None

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
        if obj:
            obj_label = "NONE"
            obj_label = obj.Label
            label = obj_label
        if label:
            self.config["obj_name_prefix"] + label
        return label

    def get_obj_linkedobj_label(self, obj):
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

    def get_obj_combined_label(self, parent_obj, obj):
        """Get object label with optional prefix."""
        label = (
            parent_obj.Label
            + "__"
            + obj.Label
        )
        if label:
            self.config["obj_name_prefix"] + label
        return label

    def rename_old_data(self, data, data_label):
        """Recusive add '_old' to data object."""
        name_old = None
        if data_label in data:
            name_old = data[data_label].name + "_old"
            if name_old in data:
                # rename recusive..
                self.rename_old_data(data, name_old)
            data[data_label].name = name_old
        return name_old

    def check_obj_visibility(self, obj):
        """Check if obj is visible."""
        result = True
        if (
            obj.Name in self.guidata
            and "Visibility" in self.guidata[obj.Name]
        ):
            if self.guidata[obj.Name]["Visibility"] is False:
                result = False
        return result

    def check_obj_visibility_with_skiphidden(self, obj, obj_visibility=None):
        """Check if obj is visible."""
        result = True
        if self.config["skiphidden"]:
            # print("obj_visibility: '{}'".format(obj_visibility))
            if obj_visibility is not None:
                result = obj_visibility
            else:
                result = self.check_obj_visibility(obj)
        return result

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

    def handle_placement(
        self,
        obj,
        bobj,
        enable_scale=True,
        relative=False
    ):
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
        func_data["bobj"] = bobj

    def sub_collection_add_or_update(self, func_data, collection_label):
        """Part-Collection handle add or update."""
        print(
            func_data["pre_line"] +
            "sub_collection_add_or_update: '{}'".format(collection_label)
        )
        temp_collection = None

        if self.config["update"]:
            if collection_label in bpy.data.collections:
                temp_collection = bpy.data.collections[collection_label]
        else:
            self.rename_old_data(bpy.data.collections, collection_label)

        if not temp_collection:
            # create new
            temp_collection = bpy.data.collections.new(collection_label)
            func_data["collection"].children.link(temp_collection)
        else:
            # bpy.context.scene.collection.children.link(self.fcstd_collection)
            pass

        # update func_data links
        func_data["collection_parent"] = func_data["collection"]
        func_data["collection"] = temp_collection

    def set_obj_parent_and_collection(self, pre_line, func_data, bobj):
        """Set Object parent and collection."""
        bobj.parent = func_data["bobj_parent"]
        # print(
        #     pre_line +
        #     "'{}' set parent to '{}' "
        #     "".format(bobj, func_data["bobj_parent"])
        # )

        # add object to current collection
        collection = func_data["collection"]
        if not collection:
            collection = self.fcstd_collection
        if bobj.name not in collection.objects:
            collection.objects.link(bobj)
            # print(
            #     pre_line +
            #     "'{}' add to '{}' "
            #     "".format(bobj, collection)
            # )

    def parent_empty_add_or_update(self, func_data, parent_label):
        """Parent Empty handle add or update."""
        print(
            func_data["pre_line"] +
            "parent_empty_add_or_update: '{}'".format(parent_label)
        )
        pre_line = func_data["pre_line"] + " → "
        parent_empty = None

        obj = func_data["obj"]

        if parent_label in bpy.data.objects:
            # print(
            #     pre_line +
            #     "'{}' already in objects list.".format(parent_label)
            # )
            if self.config["update"]:
                    parent_empty = bpy.data.objects[parent_label]
                    # print(
                    #     pre_line +
                    #     "update: '{}'".format(parent_empty)
                    # )
            else:
                renamed_to = self.rename_old_data(
                    bpy.data.objects, parent_label)
                print(
                    pre_line +
                    "overwrite - renamed to "
                    "'{}'".format(renamed_to)
                )

        flag_new = False
        if parent_empty is None:
            print(pre_line + "create new parent_empty")
            parent_empty = bpy.data.objects.new(
                name=parent_label,
                object_data=None
            )
            self.set_obj_parent_and_collection(
                pre_line, func_data, parent_empty)

        if self.config["update"] or flag_new:
            # set position of empty
            if obj:
                self.handle_placement(
                    obj,
                    parent_empty,
                    enable_scale=False,
                )
                # print(
                #     pre_line +
                #     "'{}' set position"
                #     "".format(parent_empty)
                #     # "'{}' set position to '{}'"
                #     # "".format(parent_empty, position)
                # )

        # update func_data links
        func_data["obj_parent"] = obj
        func_data["bobj_parent"] = parent_empty
        return parent_empty

    def create_collection_instance(
        self,
        func_data,
        obj_label,
        base_collection
    ):
        """Create instance of given collection."""
        result_bobj = bpy.data.objects.new(
            name=obj_label,
            object_data=None
        )
        result_bobj.instance_collection = base_collection
        result_bobj.instance_type = 'COLLECTION'
        result_bobj.empty_display_size = 0.01

        # TODO: CHECK where to add this!
        if func_data["collection"]:
            func_data["collection"].objects.link(result_bobj)
        # result_bobj.parent = func_data["bobj_parent"]
        # result_bobj.parent = obj_parent
        if result_bobj.name in bpy.context.scene.collection.objects:
            bpy.context.scene.collection.objects.unlink(result_bobj)

        return result_bobj

    def handle__object_with_sub_objects(
        self,
        func_data,
        sub_objects,
        include_only_visible=True,
    ):
        """Handle sub objects."""
        pre_line = func_data["pre_line"]
        parent_label = self.get_obj_label(func_data["obj"])
        print(
            pre_line +
            "handle__object_with_sub_objects '{}'".format(parent_label)
        )
        # print(
        #     pre_line +
        #     "include_only_visible '{}'".format(include_only_visible)
        # )
        # pre_line += "→ "
        # self.sub_collection_add_or_update(func_data, parent_label)
        self.parent_empty_add_or_update(func_data, parent_label)
        if len(sub_objects) > 0:
            print(
                pre_line +
                "→  len(sub_objects) '{}'".format(len(sub_objects))
            )
            # print(
            #     pre_line +
            #     "→  include_only_visible '{}'".format(include_only_visible)
            # )

            sub_filter_visible = False
            if not isinstance(include_only_visible, list):
                # convert True or False to list
                include_only_visible = [None] * len(sub_objects)
                sub_filter_visible = True
            # print(
            #     pre_line +
            #     "include_only_visible '{}'"
            #     "".format(include_only_visible)
            # )

            sub_objects = fc_helper.filtered_objects(
                sub_objects,
                include_only_visible=sub_filter_visible
            )
            print(
                b_helper.colors.bold
                + b_helper.colors.fg.purple
                + pre_line
                + "Import {} Recusive:".format(len(sub_objects))
                + b_helper.colors.reset
            )

            for index, obj in enumerate(sub_objects):
                self.print_obj(obj, pre_line + "- ")
                # TODO: find way to get real Visibility state.
                # Issue: #10
                # https://github.com/s-light/io_import_fcstd/issues/10
                # print(
                #     pre_line +
                #     "include_only_visible[index] '{}'"
                #     "".format(include_only_visible[index])
                # )
                if self.check_obj_visibility_with_skiphidden(
                    obj,
                    include_only_visible[index]
                ):
                    self.import_obj(
                        obj=obj,
                        collection=func_data["collection"],
                        collection_parent=func_data["collection_parent"],
                        obj_parent=func_data["obj_parent"],
                        bobj_parent=func_data["bobj_parent"],
                        pre_line=pre_line + "    "
                    )
                else:
                    print(
                        b_helper.colors.fg.darkgrey
                        + pre_line
                        + "    "
                        + "skipping - is hidden"
                        + b_helper.colors.reset
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

    # ##########################################
    # Arrays and similar
    def handle__ObjectWithElementList(self, func_data):
        """Handle Part::Feature objects."""
        pre_line = func_data["pre_line"]
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
        include_only_visible = [*func_data["obj"].VisibilityList]
        print(
            pre_line +
            "handle__ObjectWithElementList "
            "VisibilityList: '{}'"
            "".format(include_only_visible)
        )
        self.handle__object_with_sub_objects(
            func_data,
            func_data["obj"].ElementList,
            include_only_visible=include_only_visible
        )

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

    # App::Part
    def handle__AppPart(self, func_data):
        """Handle App:Part type."""
        # pre_line = func_data["pre_line"]
        self.handle__object_with_sub_objects(
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
        print(
            pre_line +
            "add_or_update_collection_instance '{}'"
            "".format(obj_label)
        )
        pre_line = pre_line + ">  "
        print(pre_line + "obj_label '{}'".format(obj_label))
        print(pre_line + "linkedobj_label '{}'".format(linkedobj_label))
        print(
            pre_line +
            "func_data[collection] '{}'"
            "".format(func_data["collection"])
        )

        base_collection = None
        bobj = None
        if linkedobj_label in bpy.data.collections:
            base_collection = bpy.data.collections[linkedobj_label]
            flag_new = False
            if obj_label in bpy.data.objects:
                bobj = bpy.data.objects[obj_label]
            else:
                # create a instance of the collection
                bobj = self.create_collection_instance(
                    func_data,
                    obj_label,
                    base_collection
                )
                flag_new = True
                # print(pre_line + "bobj", bobj)
            print(
                pre_line +
                "bobj '{}'; new:{}"
                "".format(bobj, flag_new)
            )

            if self.config["update"] or flag_new:
                self.set_obj_parent_and_collection(
                    pre_line, func_data, bobj)

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
        obj_linkedobj_label,
    ):
        """Add or update link target object."""
        pre_line = func_data["pre_line"]
        if obj_linkedobj_label in bpy.data.collections:
            print(pre_line + "TODO: implement update.")
        else:
            self.print_obj(
                obj,
                pre_line=pre_line + "# ",
                post_line=" → import Link Target '{}'.".format(
                    obj_linkedobj_label
                )
            )
            # if obj_linkedobj_label in bpy.data.objects:
            #     self.config["report"]({'INFO'}, (
            #         pre_line +
            #         "skipping import. '{}' already in objects list."
            #         "".format(obj_linkedobj_label)
            #     ))
            # else:
            func_data_obj_linked = self.import_obj(
                obj=obj_linked,
                collection=func_data["collection"],
                collection_parent=func_data["collection_parent"],
                bobj_parent=func_data["bobj_parent"],
                pre_line=pre_line + '    '
            )
            bobj = func_data_obj_linked["bobj"]
            # print(">> bobj", bobj)
            print(
                pre_line + "$ created bobj: ",
                bobj
            )
            print(
                pre_line + "$ bobj_parent: ",
                func_data_obj_linked["bobj_parent"]
            )
            print(
                pre_line + "$ collection: ",
                func_data_obj_linked["collection"]
            )
            print(
                pre_line + "$ collection_parent: ",
                func_data_obj_linked["collection_parent"]
            )
            # created collection for new link target
            self.sub_collection_add_or_update(
                func_data_obj_linked, obj_linkedobj_label)
            # self.parent_empty_add_or_update(
            #     func_data_obj_linked, obj_linkedobj_label)
            # add new object to collection.
            func_data_obj_linked["collection"].objects.link(bobj)
            # bobj.parent = func_data_obj_linked["bobj_parent"]
            if func_data_obj_linked["collection"]:
                base_collection = func_data_obj_linked["collection"]
                print(
                    pre_line + "$ base_collection: ",
                    base_collection
                )
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
        print(func_data["pre_line"] + "handle__AppLink:")
        func_data["pre_line"] += "* "
        pre_line = func_data["pre_line"]

        obj = func_data["obj"]
        obj_linkedobj = func_data["obj"].LinkedObject
        self.config["report"]({'WARNING'}, (
            pre_line +
            "'{}' ('{}') of type '{}': "
            "".format(obj.Label, obj.Name, obj.TypeId)
        ))
        self.config["report"]({'WARNING'}, (
            pre_line +
            "  Warning: App::Link handling is highly experimental!!"
        ))
        obj_label = self.get_obj_label(obj)
        # obj_linkedobj_label = self.get_obj_linkedobj_label(obj)
        # obj_linked_label = self.get_obj_label(obj_linkedobj)

        print(pre_line + "obj_label:", obj_label)
        # print(pre_line + "obj_linkedobj_label:", obj_linkedobj_label)
        # print(pre_line + "obj_linked_label:", obj_linked_label)
        fc_helper.print_obj(
            obj,
            pre_line=pre_line + "obj          : ")
        fc_helper.print_obj(
            obj_linkedobj,
            pre_line=pre_line + "obj_linkedobj: ")
        if hasattr(obj_linkedobj, "LinkedObject"):
            fc_helper.print_obj(obj_linkedobj.LinkedObject, pre_line=pre_line)

        if obj_linkedobj:
            if len(obj.ElementList) > 0:
                print(pre_line + "ElementList > 0")
                self.handle__ObjectWithElementList(func_data)
            else:
                print(pre_line + "ElementList == 0")
                # self.sub_collection_add_or_update(func_data, obj_label)
                # self.parent_empty_add_or_update(func_data, obj_label)
                self.handle__AppLinkElement(func_data)
        else:
            self.config["report"]({'WARNING'}, (
                pre_line +
                "Warning: '{}' LinkedObject is NONE → skipping."
                "".format(obj_label)
            ))
        print(pre_line + "handle__AppLink   DONE")

    def handle__AppLinkElement(self, func_data):
        """Handle App::LinkElement objects."""
        print(func_data["pre_line"] + "handle__AppLinkElement:")
        func_data["pre_line"] += "| "
        pre_line = func_data["pre_line"]

        obj = func_data["obj"]
        obj_linkedobj = func_data["obj"].LinkedObject
        if hasattr(obj_linkedobj, "LinkedObject"):
            # if we have Arrays they  have a intermediet link object..
            # we skip this..
            obj_linkedobj = obj_linkedobj.LinkedObject
        # obj_parent = obj.InList[0]
        obj_parent = func_data["obj_parent"]
        # self.config["report"]({'ERROR'}, (
        #     pre_line +
        #     "'{}' ('{}') of type '{}': "
        #     "ERROR: handle__AppLinkElement EXPERIMENTAL!"
        #     "".format(obj.Label, obj.Name, obj.TypeId)
        # ))

        obj_parent_label = self.get_obj_label(obj_parent)
        obj_label = self.get_obj_combined_label(obj_parent, obj)
        obj_linkedobj_label = self.get_obj_linkedobj_label(obj)

        # print(pre_line + "collection:", func_data["collection"])
        print(pre_line + "obj_parent_label:", obj_parent_label)
        print(pre_line + "obj_label:", obj_label)
        print(pre_line + "obj_linkedobj_label:", obj_linkedobj_label)
        fc_helper.print_obj(
            obj_parent,
            pre_line=pre_line + "obj_parent   : ")
        fc_helper.print_obj(
            obj,
            pre_line=pre_line + "obj          : ")
        fc_helper.print_obj(
            obj_linkedobj,
            pre_line=pre_line + "obj_linkedobj: ")
        # fc_helper.print_obj(obj_linked.LinkedObject, pre_line=pre_line)

        self.add_or_update_link_target(
            func_data,
            obj,
            obj_linkedobj,
            obj_linkedobj_label,
        )

        self.add_or_update_collection_instance(
            func_data,
            obj,
            obj_label,
            obj_parent,
            obj_linkedobj_label,
        )
        print(pre_line + "handle__AppLinkElement   DONE")

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

    # ##########################################
    # main object import
    def import_obj(
        self,
        obj=None,
        collection=None,
        collection_parent=None,
        obj_parent=None,
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
            "obj_parent": obj_parent,
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

    def import_doc_content(self, doc):
        """Import document content = filterd objects."""
        obj_list = fc_helper.get_root_objects(
            doc,
            filter_list=self.typeid_filter_list
        )
        print("-"*21)

        self.config["report"]({'INFO'}, (
            "found {} root objects in '{}'"
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
            if self.check_obj_visibility_with_skiphidden(obj):
                self.print_obj(obj, pre_line="- ")
                self.import_obj(
                    obj=obj,
                    collection=self.fcstd_collection,
                    bobj_parent=self.fcstd_empty,
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

    def prepare_root_empty(self):
        """Prepare import file root empty."""
        func_data = {
            "obj": None,
            "obj_parent": None,
            "bobj_parent": None,
            "collection": self.fcstd_collection,
            "pre_line": "",
        }
        self.fcstd_empty = self.parent_empty_add_or_update(
            func_data,
            self.doc_filename
        )

    def prepare_freecad_import(self):
        """Prepare FreeCAD import."""
        # append the FreeCAD path specified in addon preferences
        path = self.path_to_freecad
        if path and os.path.exists(path):
            if os.path.isfile(path):
                path = os.path.dirname(path)
            print("Configured path to FreeCAD:", path)
            if path not in sys.path:
                sys.path.append(path)
        else:
            self.config["report"]({'WARNING'}, (
                "Path to FreeCAD does not exist. Please check! "
                "'{}'".format(path)
            ))

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
                "Make sure it is installed on your system \n"
                "and compiled with Python3 (same version as Blender).\n"
                "It must also be found by Python, \n"
                "you might need to set its path in this Addon preferences "
                "(User preferences->Addons->expand this addon).\n"
                "\n"
                + str(e)
            )
            return {'CANCELLED'}

        self.guidata = guidata.load_guidata(
            self.config["filename"],
            self.config["report"],
        )

        # Context Managers not implemented..
        # see https://docs.python.org/3.8/reference/compound_stmts.html#with
        # with FreeCAD.open(self.config["filename"]) as doc:
        # so we use the classic try finally block:
        try:
            # doc = FreeCAD.open(
            #     "/home/stefan/mydata/freecad/tests/linking_test/Linking.FCStd")
            self.config["report"](
                {'INFO'},
                "open FreeCAD file. '{}'"
                "".format(self.config["filename"])
            )
            try:
                doc = FreeCAD.open(self.config["filename"])
            except Exception as e:
                print(e)
            docname = doc.Name
            self.doc_filename = docname + ".FCStd"
            if doc:
                self.config["report"](
                    {'INFO'},
                    "File '{}' successfully opened."
                    "".format(self.doc_filename)
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
                self.prepare_root_empty()
                self.import_doc_content(doc)
            else:
                self.config["report"](
                    {'ERROR'},
                    "Unable to open the given FreeCAD file '{}'"
                    "".format(self.config["filename"])
                )
                return {'CANCELLED'}
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
