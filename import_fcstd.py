
import sys
import bpy
import xml.sax
import zipfile
import os

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


#####
# typeid_filter_list = [
#     'App::Line',
#     'App::Plane',
#     'App::Origin',
#     # 'GeoFeature',
#     # 'PartDesign::CoordinateSystem',
#     'Sketcher::SketchObject',
# ]
# for obj in doc.Objects:
#     if obj.TypeId not in typeid_filter_list:
#         print(
#             "import_obj: {:<25} {:<15} {:<30}"
#             "".format(obj.TypeId, obj.Name, obj.Label),
#             end=''
#         )
#         print(obj.InList, end='')
#         print("  ", end='')
#         print(obj.OutList, end='')
#         print("  ", end='')
#         print(obj.Parents)
#####

class ImportFcstd(object):
    """Import fcstd files."""

    def __init__(
        self,
        filename=None,
        update=True,
        placement=True,
        tessellation=1.0,
        skiphidden=True,
        filter_sketch=False,
        scale=1.0,
        sharemats=True,
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
            "report": report,
        }
        print('config', self.config)
        self.guidata = {}
        self.fcstd_collection = None
        self.doc_filename = None

        self.typeid_filter_list = [
            'App::Line',
            'App::Plane',
            'App::Origin',
            # 'GeoFeature',
            # 'PartDesign::CoordinateSystem',
        ]
        if self.config['filter_sketch']:
            self.typeid_filter_list.append('Sketcher::SketchObject')

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

    def handle_material(self, obj, bobj, matindex, matdatabase):
        bmat = None
        if (
            matindex
            and ("DiffuseColor" in self.guidata[obj.Name])
            and (len(matindex) == len(
                self.guidata[obj.Name]["DiffuseColor"])
            )
        ):
            # we have per-face materials.
            # Create new mats and attribute faces to them
            fi = 0
            objmats = []
            for i in range(len(matindex)):
                # DiffuseColor stores int values, Blender use floats
                rgba = tuple([
                    float(x)/255.0
                    for x in self.guidata[obj.Name]["DiffuseColor"][i]
                ])
                # FreeCAD stores transparency, not alpha
                alpha = 1.0
                if rgba[3] > 0:
                    alpha = 1.0-rgba[3]
                rgba = rgba[:3]+(alpha,)
                bmat = None
                if self.config["sharemats"]:
                    if rgba in matdatabase:
                        bmat = matdatabase[rgba]
                        if rgba not in objmats:
                            objmats.append(rgba)
                            bobj.data.materials.append(bmat)
                if not bmat:
                    if rgba in objmats:
                        bmat = bobj.data.materials[objmats.index(rgba)]
                if not bmat:
                    bmat = bpy.data.materials.new(
                        name=obj.Name+str(len(objmats)))
                    bmat.use_nodes = True
                    principled = PrincipledBSDFWrapper(
                        bmat, is_readonly=False)
                    principled.base_color = rgba[:3]
                    if alpha < 1.0:
                        bmat.diffuse_color = rgba
                        principled.alpha = alpha
                        bmat.blend_method = "BLEND"
                    objmats.append(rgba)
                    bobj.data.materials.append(bmat)
                    if self.config["sharemats"]:
                        matdatabase[rgba] = bmat
                for fj in range(matindex[i]):
                    bobj.data.polygons[fi+fj].material_index = objmats.index(rgba)
                fi += matindex[i]
        else:
            # one material for the whole object
            alpha = 1.0
            rgb = (0.5, 0.5, 0.5)
            if "Transparency" in self.guidata[obj.Name]:
                if self.guidata[obj.Name]["Transparency"] > 0:
                    alpha = (100-self.guidata[obj.Name]["Transparency"])/100.0
            if "ShapeColor" in self.guidata[obj.Name]:
                rgb = self.guidata[obj.Name]["ShapeColor"]
            rgba = rgb+(alpha,)
            bmat = None
            if self.config["sharemats"]:
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
                if self.config["sharemats"]:
                    matdatabase[rgba] = bmat
            bobj.data.materials.append(bmat)

    def add_or_update_blender_obj(self, func_data):
        """Create or update object with mesh and material data."""
        bobj = None
        if self.config["update"]:
            # locate existing object (mesh with same name)
            for o in bpy.data.objects:
                if o.data.name == func_data["obj"].Name:
                    bobj = o
                    print("Replacing existing object:", func_data["obj"].Label)
        bmesh = bpy.data.meshes.new(name=func_data["obj"].Name)
        bmesh.from_pydata(
            func_data["verts"],
            func_data["edges"],
            func_data["faces"]
        )
        bmesh.update()
        if bobj:
            # update only the mesh of existing object. Don't touch materials
            bobj.data = bmesh
        else:
            # create new object
            bobj = bpy.data.objects.new(func_data["obj"].Label, bmesh)
            self.handle_placement(bobj)
            if func_data["obj"].Name in self.guidata:
                self.handle_material(
                    func_data["obj"],
                    bobj,
                    func_data["matindex"],
                    func_data["matdatabase"]
                )

        # TODO: on update: check if already there
        if self.config['update']:
            if bobj.name not in self.fcstd_collection.objects:
                self.fcstd_collection.objects.link(bobj)
            else:
                print(bobj.name, "already in collection", self.fcstd_collection)
        else:
            self.fcstd_collection.objects.link(bobj)
        # bpy.context.scene.objects.active = func_data["obj"]
        # obj.select = True

    def create_mesh_from_shape(self, func_data):
        """Create mesh from shape."""
        # a placeholder to store edges that belong to a face
        faceedges = []
        import Part
        shape = func_data["obj"].Shape
        if self.config["placement"]:
            self.config["placement"] = func_data["obj"].Placement
            shape = func_data["obj"].Shape.copy()
            shape.Placement = self.config["placement"].\
                inverse().multiply(shape.Placement)
        if shape.Faces:
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
        for edge in shape.Edges:
            # Treat remaining edges (that are not in faces)
            if not (edge.hashCode() in faceedges):
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

    def import_obj(self, obj):
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
        }
        # func_data["matindex"]

        if obj.isDerivedFrom("Part::Feature"):
            self.create_mesh_from_shape(func_data)
        elif obj.isDerivedFrom("Mesh::Feature"):
            self.create_mesh_from_mesh(func_data)
        # elif obj.isDerivedFrom("PartDesign::Feature"):
        #     self.create_mesh_from_PartDesign(func_data)
        else:
            if self.config["report"]:
                self.config["report"](
                    {'ERROR'},
                    "Unable to load {} of type {}. Not implemented yet."
                    "".format(obj.Label, obj.TypeId)
                )

        if func_data["verts"] and (func_data["faces"] or func_data["edges"]):
            self.add_or_update_blender_obj(func_data)
        # END import_obj

    # def check_visibility_recusiv(self, obj):
    #     result = self.check_visibility_recusiv(obj.Parents)

    def check_visibility(self, obj):
        """Check if obj is visible."""
        result = True
        if (
            self.config["skiphidden"]
            and obj.Name in self.guidata
            and "Visibility" in self.guidata[obj.Name]
        ):
            if self.guidata[obj.Name]["Visibility"] is False:
                result = False
            # else:
            #     if obj.TypeId not in self.typeid_filter_list:
            #         # check if a parent is invisible...
            #         # for obj_parent in obj.Parents:
            #         #     pass
            #         # result = self.check_visibility_recusiv()
            #         if (
            #             len(obj.Parents) > 0
            #             and "Visibility" in obj.Parents[0]
            #             and obj.Parents[0].Visibility is False
            #         ):
            #             result = False
        return result

    def import_doc_content(self, doc):
        for obj in doc.Objects:
            if obj.TypeId not in self.typeid_filter_list:
                print(
                    "import_obj: {:<25} {:<15} {:<25}"
                    "".format(obj.TypeId, obj.Name, obj.Label),
                    end=''
                )
                print(obj.InList, end='')
                print("  ", end='')
                print(obj.OutList, end='')
                print("  ", end='')
                print(obj.Parents)
                if self.check_visibility(obj):
                    print("  →  import.")
                    self.import_obj(obj)
                else:
                    # print(" → invisible Skipping.")
                    print("  →  skipping.")

    def prepare_collection(self):
        # TODO: on update: check if already there
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
        # except ModuleNotFoundError:
        except Exception:
            print(
                "Unable to import the FreeCAD Python module. \n"
                "Make sure it is installed on your system"
                "and compiled with Python3 (same version as Blender).\n"
                "It must also be found by Python, "
                "you might need to set its path in this Addon preferences"
                "(User preferences->Addons->expand this addon)."
            )
            if self.config["report"]:
                self.config["report"](
                    {'ERROR'},
                    "Unable to import the FreeCAD Python module. "
                    "Check Addon preferences."
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
                print("Unable to open the given FreeCAD file")
                if self.config["report"]:
                    self.config["report"](
                        {'ERROR'},
                        "Unable to open the given FreeCAD file"
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
