#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Material Things."""

import bpy
from bpy_extras.node_shader_utils import PrincipledBSDFWrapper

from .. import blender_helper as b_helper

# from . import helper


class MaterialManager(object):
    """
    Handle all Material related things.
    """

    def __init__(
        self,
        guidata,
        func_data,
        bobj,
        obj_label,
        sharemats,
        report=None,
        report_preline="",
    ):
        """Init."""
        self.report_fnc = report
        self.report_preline = report_preline
        self.guidata = guidata
        self.func_data = func_data
        self.bobj = bobj
        self.obj_label = obj_label
        self.sharemats = sharemats

    def report(self, data, mode=None, pre_line=None):
        if not mode:
            mode = {"INFO"}
        if not pre_line:
            pre_line = self.report_preline
        else:
            pre_line = self.report_preline + pre_line
        if self.report_fnc:
            return self.report_fnc(mode, data, pre_line=pre_line)
        else:
            print(pre_line + data)

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
        rgba = tuple(
            [float(x) / 255.0 for x in self.guidata[obj_Name]["DiffuseColor"][i]]
        )
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
            rgba = rgb + (alpha,)
        return rgba

    def create_new_bmat(self, bmat_name, rgba):
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
        if self.sharemats:
            self.func_data["matdatabase"][rgba] = bmat
        return bmat

    def handle_material_per_face(self, face_index, objmats, material_index):
        """Handle material for face."""
        # Create new mats and attribute faces to them
        # DiffuseColor stores int values, Blender use floats
        # self.report(
        #     b_helper.colors.fg.lightblue
        #     + "handle_material_per_face"
        #     + b_helper.colors.reset,
        #     pre_line="|  ",
        # )
        rgba = self.get_obj_rgba(self.func_data["obj"].Name, material_index)
        # get or create blender material
        bmat = None
        if self.sharemats:
            if rgba in self.func_data["matdatabase"]:
                bmat = self.func_data["matdatabase"][rgba]
                if rgba not in objmats:
                    objmats.append(rgba)
                    self.bobj.data.materials.append(bmat)
        if not bmat:
            if rgba in objmats:
                bmat = self.bobj.data.materials[objmats.index(rgba)]
        if not bmat:
            bmat_name = self.obj_label + "_" + str(len(objmats))
            bmat = self.create_new_bmat(bmat_name, rgba)
            objmats.append(rgba)
            self.bobj.data.materials.append(bmat)

        # at this point we should have a valid blender material

        # self.report(
        #     b_helper.colors.fg.lightblue
        #     + "objmats "
        #     + b_helper.colors.reset
        #     + "{}".format(objmats),
        #     pre_line="|  ",
        # )
        # self.report(
        #     b_helper.colors.fg.lightblue
        #     + "bmat "
        #     + b_helper.colors.reset
        #     + "{}".format(bmat),
        #     pre_line="|  ",
        # )
        # self.report(
        #     b_helper.colors.fg.lightblue
        #     + "face_index "
        #     + b_helper.colors.reset
        #     + "{}".format(face_index),
        #     pre_line="|  ",
        # )

        # assigne materials to polygons
        objmats_index = objmats.index(rgba)
        # self.report(
        #     b_helper.colors.fg.lightblue
        #     + "objmats_index "
        #     + b_helper.colors.reset
        #     + "{}".format(objmats_index),
        #     pre_line="|  ",
        # )
        # self.report(
        #     b_helper.colors.fg.lightblue
        #     + 'self.func_data["matindex"][material_index] '
        #     + b_helper.colors.reset
        #     + "{}".format(self.func_data["matindex"][material_index]),
        #     pre_line="|  ",
        # )

        for fj in range(self.func_data["matindex"][material_index]):
            # self.report(
            #     b_helper.colors.fg.lightblue
            #     + "fj "
            #     + b_helper.colors.reset
            #     + "{}".format(fj),
            #     pre_line="|  * ",
            # )
            # self.report(
            #     b_helper.colors.fg.lightblue
            #     + "face_index + fj "
            #     + b_helper.colors.reset
            #     + "{}".format(face_index + fj),
            #     pre_line="|  * ",
            # )
            self.bobj.data.polygons[face_index + fj].material_index = objmats_index
        face_index += self.func_data["matindex"][material_index]
        return face_index

    def handle_material_multi(self):
        """Handle multi material."""
        # we have per-face materials.
        # self.report(
        #     b_helper.colors.fg.lightgreen
        #     + "handle_material_multi"
        #     + b_helper.colors.reset,
        #     pre_line="|  ",
        # )
        face_index = 0
        objmats = []
        for material_index in range(len(self.func_data["matindex"])):
            face_index = self.handle_material_per_face(
                face_index, objmats, material_index
            )

    def handle_material_single(self):
        """Handle single material."""
        # one material for the whole object
        self.report(
            b_helper.colors.fg.lightgreen
            + "handle_material_single"
            + b_helper.colors.reset
        )
        rgba = self.get_obj_rgba(self.func_data["obj"].Name)
        bmat = None
        if self.sharemats:
            if rgba in self.func_data["matdatabase"]:
                bmat = self.func_data["matdatabase"][rgba]
            else:
                # print("not found in db:",rgba,"in",matdatabase)
                pass
        if not bmat:
            bmat_name = self.obj_label
            bmat = self.create_new_bmat(bmat_name, rgba)
        self.bobj.data.materials.append(bmat)

    def create_new(self):
        """Handle material creation."""
        # check if we have a material at all...
        # self.report(
        #     b_helper.colors.fg.lightgreen
        #     + "create_new material"
        #     + b_helper.colors.reset
        # )
        if self.func_data["obj"].Name in self.guidata:
            # check if we have 'per face' or 'object' coloring.
            # self.report(
            #     b_helper.colors.bold
            #     + b_helper.colors.fg.lightblue
            #     + 'self.func_data["matindex"]'
            #     + "  ({}):  ".format(len(self.func_data["matindex"]))
            #     + b_helper.colors.reset
            #     + "{}".format(self.func_data["matindex"])
            # )
            # # ############
            # # list colors:
            # self.report(
            #     b_helper.colors.bold
            #     + b_helper.colors.fg.lightblue
            #     + 'self.guidata[self.func_data["obj"].Name]["DiffuseColor"]'
            #     + "  ({}):".format(
            #         len(self.guidata[self.func_data["obj"].Name]["DiffuseColor"])
            #     )
            #     + b_helper.colors.reset
            # )
            # for index, color in enumerate(
            #     self.guidata[self.func_data["obj"].Name]["DiffuseColor"]
            # ):
            #     self.report("  {:>3} {}".format(index, color))
            # # ############
            #
            # self.report(
            #     b_helper.colors.fg.lightblue
            #     + "self.bobj.data.polygons "
            #     + b_helper.colors.reset
            #     + "{}".format(self.bobj.data.polygons)
            # )

            # # create a list with all faces
            # face_list = [face for face in self.bobj.data.polygons]
            # self.report(
            #     b_helper.colors.fg.lightblue + "face_list " + b_helper.colors.reset
            # )
            # for index, face in enumerate(face_list):
            #     self.report("  {:>3} {}".format(index, face))
            # # ############

            # check for multi material
            if (
                self.func_data["matindex"]
                and ("DiffuseColor" in self.guidata[self.func_data["obj"].Name])
                and (
                    len(self.func_data["matindex"])
                    == len(self.guidata[self.func_data["obj"].Name]["DiffuseColor"])
                )
            ):
                self.handle_material_multi()
            else:
                self.handle_material_single()
