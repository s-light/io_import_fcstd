#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Material Things."""

import bpy
from bpy_extras.node_shader_utils import PrincipledBSDFWrapper

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
        sharemats
    ):
        """Init."""
        self.guidata = guidata
        self.func_data = func_data
        self.bobj = bobj
        self.obj_label = obj_label
        self.sharemats = sharemats

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

    def handle_material_per_face(self, fi, objmats, i):
        """Handle material for face."""
        # Create new mats and attribute faces to them
        # DiffuseColor stores int values, Blender use floats
        rgba = self.get_obj_rgba(self.func_data["obj"].Name, i)
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
            # TODO: please check if this is really correct..
            self.bobj.data.materials.append(bmat)

        # assigne materials to polygons
        for fj in range(self.func_data["matindex"][i]):
            self.bobj.data.polygons[fi+fj].material_index = objmats.index(rgba)
        fi += self.func_data["matindex"][i]

    def handle_material_multi(self):
        """Handle multi material."""
        # we have per-face materials.
        fi = 0
        objmats = []
        for i in range(len(self.func_data["matindex"])):
            self.handle_material_per_face(fi, objmats, i)

    def handle_material_single(self):
        """Handle single material."""
        # one material for the whole object
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
        if self.func_data["obj"].Name in self.guidata:
            # check if we have 'per face' or 'object' coloring.
            if (
                self.func_data["matindex"]
                and ("DiffuseColor" in self.guidata[self.func_data["obj"].Name])
                and (len(self.func_data["matindex"]) == len(
                    self.guidata[self.func_data["obj"].Name]["DiffuseColor"])
                )
            ):
                self.handle_material_multi()
            else:
                self.handle_material_single()
