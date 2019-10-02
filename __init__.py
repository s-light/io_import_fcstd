

import sys
import bpy
import xml.sax
import zipfile
import os

from bpy_extras.node_shader_utils import PrincipledBSDFWrapper


bl_info = {
    "name": "FreeCAD Importer",
    "category": "Import-Export",
    "author": "Yorik van Havre",
    "version": (5, 0, 0),
    "blender": (2, 80, 0),
    "location": "File > Import > FreeCAD",
    "description": "Imports a .FCStd file from FreeCAD",
    "warning": "This addon needs FreeCAD installed on your system. \
    Only Part- and Mesh-based objects supported at the moment.",
}

# brut force path loading:
# import sys; sys.path.append("/path/to/FreeCAD.so")

# pre git HISTORY
# v1.0.0 - 12 june 2018 - initial release - basically working
# v2.0.0 - 21 june 2018 - option to turn cycles mat on/off, per-face material support,
#                         use of polygons when possible, shared materials
# v3.0.0 - 06 february 2019 - ported to Blender 2.80
# v4.0.0 - 07 february 2019 - API changes + support of transparency
# v5.0.0 - 13 august 2019 - small fixes and better info messages if things go wrong


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


def import_fcstd(filename,
                 update=True,
                 placement=True,
                 tessellation=1.0,
                 skiphidden=True,
                 scale=1.0,
                 sharemats=True,
                 report=None):
    """Read a FreeCAD .FCStd file and creates Blender objects."""
    try:
        # append the FreeCAD path specified in addon preferences
        user_preferences = bpy.context.preferences
        addon_prefs = user_preferences.addons[__name__].preferences
        path = addon_prefs.filepath
        if path:
            if os.path.isfile(path):
                path = os.path.dirname(path)
            print("Configured FreeCAD path:", path)
            sys.path.append(path)
        else:
            print("FreeCAD path is not configured in preferences")
        import FreeCAD
    except:
        print(
            "Unable to import the FreeCAD Python module. "
            "Make sure it is installed on your system")
        print("and compiled with Python3 (same version as Blender).")
        print(
            "It must also be found by Python, "
            "you might need to set its path in this Addon preferences")
        print("(User preferences->Addons->expand this addon).")
        if report:
            report(
                {'ERROR'},
                "Unable to import the FreeCAD Python module. "
                "Check Addon preferences.")
        return {'CANCELLED'}
    # check if we have a GUI document
    guidata = {}
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
        # print ("guidata:",guidata)
    doc = FreeCAD.open(filename)
    docname = doc.Name
    if not doc:
        print("Unable to open the given FreeCAD file")
        if report:
            report({'ERROR'}, "Unable to open the given FreeCAD file")
        return {'CANCELLED'}
    # print ("Transferring",len(doc.Objects),"objects to Blender")

    # import some FreeCAD modules needed below. After "import FreeCAD" these modules become available
    import Part

    def hascurves(shape):

        for e in shape.Edges:
            if not isinstance(e.Curve, (Part.Line, Part.LineSegment)):
                return True
        return False

    # to store reusable materials
    matdatabase = {}

    fcstd_collection = bpy.data.collections.new("FreeCAD import")
    bpy.context.scene.collection.children.link(fcstd_collection)

    for obj in doc.Objects:
        # print("Importing",obj.Label)
        if skiphidden:
            if obj.Name in guidata:
                if "Visibility" in guidata[obj.Name]:
                    if guidata[obj.Name]["Visibility"] is False:
                        # print(obj.Label,"is invisible. Skipping.")
                        continue

        verts = []
        edges = []
        faces = []
        # face to material relationship
        matindex = []
        plac = None
        # a placeholder to store edges that belong to a face
        faceedges = []
        name = "Unnamed"

        if obj.isDerivedFrom("Part::Feature"):
            # create mesh from shape
            shape = obj.Shape
            if placement:
                placement = obj.Placement
                shape = obj.Shape.copy()
                shape.Placement = placement.inverse().multiply(shape.Placement)
            if shape.Faces:
                if TRIANGULATE:
                    # triangulate and make faces
                    rawdata = shape.tessellate(tessellation)
                    for v in rawdata[0]:
                        verts.append([v.x, v.y, v.z])
                    for f in rawdata[1]:
                        faces.append(f)
                    for face in shape.Faces:
                        for e in face.Edges:
                            faceedges.append(e.hashCode())
                else:
                    # write FreeCAD faces as polygons when possible
                    for face in shape.Faces:
                        if (
                            (len(face.Wires) > 1)
                            or (not isinstance(face.Surface, Part.Plane))
                            or hascurves(face)
                        ):
                            # face has holes or is curved, so we need to triangulate it
                            rawdata = face.tessellate(tessellation)
                            for v in rawdata[0]:
                                vl = [v.x, v.y, v.z]
                                if not vl in verts:
                                    verts.append(vl)
                            for f in rawdata[1]:
                                nf = []
                                for vi in f:
                                    nv = rawdata[0][vi]
                                    nf.append(verts.index([nv.x, nv.y, nv.z]))
                                faces.append(nf)
                            matindex.append(len(rawdata[1]))
                        else:
                            f = []
                            ov = face.OuterWire.OrderedVertexes
                            for v in ov:
                                vl = [v.X, v.Y, v.Z]
                                if not vl in verts:
                                    verts.append(vl)
                                f.append(verts.index(vl))
                            # FreeCAD doesn't care about verts order. Make sure our loop goes clockwise
                            c = face.CenterOfMass
                            v1 = ov[0].Point.sub(c)
                            v2 = ov[1].Point.sub(c)
                            n = face.normalAt(0, 0)
                            if (v1.cross(v2)).getAngle(n) > 1.57:
                                # inverting verts order if the direction is couterclockwise
                                f.reverse()
                            faces.append(f)
                            matindex.append(1)
                        for e in face.Edges:
                            faceedges.append(e.hashCode())
            for edge in shape.Edges:
                # Treat remaining edges (that are not in faces)
                if not (edge.hashCode() in faceedges):
                    if hascurves(edge):
                        # TODO use tessellation value
                        dv = edge.discretize(9)
                        for i in range(len(dv)-1):
                            dv1 = [dv[i].x, dv[i].y, dv[i].z]
                            dv2 = [dv[i+1].x, dv[i+1].y, dv[i+1].z]
                            if not dv1 in verts:
                                verts.append(dv1)
                            if not dv2 in verts:
                                verts.append(dv2)
                            edges.append([verts.index(dv1), verts.index(dv2)])
                    else:
                        e = []
                        for vert in edge.Vertexes:
                            # TODO discretize non-linear edges
                            v = [vert.X, vert.Y, vert.Z]
                            if not v in verts:
                                verts.append(v)
                            e.append(verts.index(v))
                        edges.append(e)

        elif obj.isDerivedFrom("Mesh::Feature"):
            # convert freecad mesh to blender mesh
            mesh = obj.Mesh
            if placement:
                placement = obj.Placement
                # in meshes, this zeroes the placement
                mesh = obj.Mesh.copy()
            t = mesh.Topology
            verts = [[v.x, v.y, v.z] for v in t[0]]
            faces = t[1]

        if verts and (faces or edges):
            # create or update object with mesh and material data
            bobj = None
            bmat = None
            if update:
                # locate existing object (mesh with same name)
                for o in bpy.data.objects:
                    if o.data.name == obj.Name:
                        bobj = o
                        print("Replacing existing object:", obj.Label)
            bmesh = bpy.data.meshes.new(name=obj.Name)
            bmesh.from_pydata(verts, edges, faces)
            bmesh.update()
            if bobj:
                # update only the mesh of existing object. Don't touch materials
                bobj.data = bmesh
            else:
                # create new object
                bobj = bpy.data.objects.new(obj.Label, bmesh)
                if placement:
                    # print ("placement:",placement)
                    bobj.location = placement.Base.multiply(scale)
                    m = bobj.rotation_mode
                    bobj.rotation_mode = 'QUATERNION'
                    if placement.Rotation.Angle:
                        # FreeCAD Quaternion is XYZW while Blender is WXYZ
                        q = (placement.Rotation.Q[3],)+placement.Rotation.Q[:3]
                        bobj.rotation_quaternion = (q)
                        bobj.rotation_mode = m
                    bobj.scale = (scale, scale, scale)
                if obj.Name in guidata:
                    if (
                        matindex
                        and ("DiffuseColor" in guidata[obj.Name])
                        and (len(matindex) == len(guidata[obj.Name]["DiffuseColor"]))
                    ):
                        # we have per-face materials. Create new mats and attribute faces to them
                        fi = 0
                        objmats = []
                        for i in range(len(matindex)):
                            # DiffuseColor stores int values, Blender use floats
                            rgba = tuple([float(x)/255.0 for x in guidata[obj.Name]["DiffuseColor"][i]])
                            # FreeCAD stores transparency, not alpha
                            alpha = 1.0
                            if rgba[3] > 0:
                                alpha = 1.0-rgba[3]
                            rgba = rgba[:3]+(alpha,)
                            bmat = None
                            if sharemats:
                                if rgba in matdatabase:
                                    bmat = matdatabase[rgba]
                                    if not rgba in objmats:
                                        objmats.append(rgba)
                                        bobj.data.materials.append(bmat)
                            if not bmat:
                                if rgba in objmats:
                                    bmat = bobj.data.materials[objmats.index(rgba)]
                            if not bmat:
                                bmat = bpy.data.materials.new(name=obj.Name+str(len(objmats)))
                                bmat.use_nodes = True
                                principled = PrincipledBSDFWrapper(bmat, is_readonly=False)
                                principled.base_color = rgba[:3]
                                if alpha < 1.0:
                                    bmat.diffuse_color = rgba
                                    principled.alpha = alpha
                                    bmat.blend_method = "BLEND"
                                objmats.append(rgba)
                                bobj.data.materials.append(bmat)
                                if sharemats:
                                    matdatabase[rgba] = bmat
                            for fj in range(matindex[i]):
                                bobj.data.polygons[fi+fj].material_index = objmats.index(rgba)
                            fi += matindex[i]
                    else:
                        # one material for the whole object
                        alpha = 1.0
                        rgb = (0.5, 0.5, 0.5)
                        if "Transparency" in guidata[obj.Name]:
                            if guidata[obj.Name]["Transparency"] > 0:
                                alpha = (100-guidata[obj.Name]["Transparency"])/100.0
                        if "ShapeColor" in guidata[obj.Name]:
                            rgb = guidata[obj.Name]["ShapeColor"]
                        rgba = rgb+(alpha,)
                        bmat = None
                        if sharemats:
                            if rgba in matdatabase:
                                bmat = matdatabase[rgba]
                            else:
                                # print("not found in db:",rgba,"in",matdatabase)
                                pass
                        if not bmat:
                            bmat = bpy.data.materials.new(name=obj.Name)
                            # no more internal engine!
                            # bmat.diffuse_color = rgb
                            # bmat.alpha = alpha
                            # if enablenodes:
                            bmat.use_nodes = True
                            principled = PrincipledBSDFWrapper(bmat, is_readonly=False)
                            principled.base_color = rgb
                            if alpha < 1.0:
                                bmat.diffuse_color = rgba
                            if sharemats:
                                matdatabase[rgba] = bmat
                        bobj.data.materials.append(bmat)

            fcstd_collection.objects.link(bobj)
            # bpy.context.scene.objects.active = obj
            # obj.select = True

    FreeCAD.closeDocument(docname)

    # why is this here? I don't remember. It doesn't seem to work anymore anyway...
    # for area in bpy.context.screen.areas:
    #    if area.type == 'VIEW_3D':
    #        for region in area.regions:
    #            if region.type == 'WINDOW':
    #                override = {'area': area, 'region': region, 'edit_object': bpy.context.edit_object}
    #                bpy.ops.view3d.view_all(override)

    print("Import finished without errors")
    return {'FINISHED'}


# ==============================================================================
# Blender Operator class
# ==============================================================================


class IMPORT_OT_FreeCAD(bpy.types.Operator):
    """Imports the contents of a FreeCAD .FCStd file."""

    bl_idname = 'import_fcstd.import_freecad'
    bl_label = 'Import FreeCAD FCStd file'
    bl_options = {'REGISTER', 'UNDO'}

    # ImportHelper mixin class uses this
    filename_ext = ".fcstd"

    # Properties assigned by the file selection window.

    directory: bpy.props.StringProperty(
        maxlen=1024,
        subtype='FILE_PATH',
        options={'HIDDEN', 'SKIP_SAVE'}
    )
    files: bpy.props.CollectionProperty(
        type=bpy.types.OperatorFileListElement,
        options={'HIDDEN', 'SKIP_SAVE'}
    )
    option_skiphidden: bpy.props.BoolProperty(
        name="Skip hidden objects",
        default=True,
        description="Only import objects that where visible in FreeCAD"
    )
    option_update: bpy.props.BoolProperty(
        name="Update existing objects",
        default=True,
        description=(
            "Keep objects with same names in current scene and "
            "their materials, only replace the geometry"
        )
    )
    option_placement: bpy.props.BoolProperty(
        name="Use Placements",
        default=True,
        description="Set Blender pivot points to the FreeCAD placements"
    )
    option_tessellation: bpy.props.FloatProperty(
        name="Tessellation value",
        default=1.0,
        description="The tessellation value to apply when triangulating shapes"
    )
    option_scale: bpy.props.FloatProperty(
        name="Scaling value",
        default=0.001,
        description=(
            "A scaling value to apply to imported objects. "
            "Default value of 0.001 means one Blender unit = 1 meter"
        )
    )
    option_sharemats: bpy.props.BoolProperty(
        name="Share similar materials",
        default=True,
        description=(
            "Objects with same color/transparency will use the same material"
        )
    )

    def invoke(self, context, event):
        """Invoke is called when the user picks our Import menu entry."""
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):
        """Call when the user is done using the modal file-select window."""
        dir = self.directory
        for file in self.files:
            filestr = str(file.name)
            if filestr.lower().endswith(".fcstd"):
                return import_fcstd(filename=dir+filestr,
                                    update=self.option_update,
                                    placement=self.option_placement,
                                    tessellation=self.option_tessellation,
                                    skiphidden=self.option_skiphidden,
                                    scale=self.option_scale,
                                    sharemats=self.option_sharemats,
                                    report=self.report)
        return {'FINISHED'}


class IMPORT_OT_FreeCAD_Preferences(bpy.types.AddonPreferences):
    """A preferences settings dialog to set the path to the FreeCAD module."""

    bl_idname = __name__

    filepath: bpy.props.StringProperty(
            name="Path to FreeCAD.so (Mac/Linux) or FreeCAD.pyd (Windows)",
            subtype='FILE_PATH',
            )

    def draw(self, context):
        """Draw Preferences."""
        layout = self.layout
        layout.label(text=(
            "FreeCAD must be installed on your system, and its path set below."
            " Make sure both FreeCAD and Blender use the same Python version "
            "(check their Python console)"
        ))
        layout.prop(self, "filepath")


# ==============================================================================
# Register plugin with Blender
# ==============================================================================

classes = (
    IMPORT_OT_FreeCAD,
    IMPORT_OT_FreeCAD_Preferences,
)


def menu_func_import(self, context):
    """Needed if you want to add into a dynamic menu."""
    self.layout.operator(IMPORT_OT_FreeCAD.bl_idname, text="FreeCAD (.FCStd)")


def register():
    """Register."""
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)


def unregister():
    """Unregister."""
    from bpy.utils import unregister_class
    for cls in reversed(classes):
        unregister_class(cls)
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)


if __name__ == "__main__":
    register()
