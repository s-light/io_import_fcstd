

import sys
import os

import bpy


def prepare_freecad_import():
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


# ****************************************

def print_obj_header():
    print(
        "     {:<25} {:<15} {:<25}"
        "".format("TypeId", "Name", "Label"),
        end=''
    )
    print("[Parents]", end='')
    print("  ", end='')
    print("[InList]", end='')
    print("  ", end='')
    print("[OutList]", end='')
    print("  ", end='')
    print()


def print_obj(obj):
    print(
        "obj: {:<25} {:<15} {:<25}"
        "".format(obj.TypeId, obj.Name, obj.Label),
        end=''
    )
    print(obj.Parents, end='')
    print("  ", end='')
    print(obj.InList, end='')
    print("  ", end='')
    print(obj.OutList, end='')
    print("  ", end='')
    print()


def print_objects(objects):
    print_obj_header()
    for obj in objects:
        print_obj(obj)


# ****************************************

def get_filtered_objects(doc):
    typeid_filter_list = [
        'App::Line',
        'App::Plane',
        'App::Origin',
        # 'GeoFeature',
        # 'PartDesign::CoordinateSystem',
        #'Sketcher::SketchObject',
    ]
    result_objects = []
    for obj in doc.Objects:
        if obj.TypeId not in typeid_filter_list:
            result_objects.append(obj)
    return result_objects


def get_root_objects(doc):
    typeid_filter_list = [
        'App::Line',
        'App::Plane',
        'App::Origin',
    ]
    result_objects = []
    for obj in doc.Objects:
        if obj.TypeId not in typeid_filter_list:
            if (len(obj.Parents) == 0):
                result_objects.append(obj)
    return result_objects



def isTopLevelInList(lst):
    if len(lst) == 0: return True
    for ob in lst:
        if ob.Name.startswith("Clone"): continue
        if ob.Name.startswith("Part__Mirroring"): continue
        else: return False
    return True


def getTopLevelObjects(doc):
    topLevelShapes = []
    for ob in doc.Objects:
        if isTopLevelInList(ob.InList):
            topLevelShapes.append(ob)
        else:
            numBodies = 0
            numClones = 0
            invalidObjects = False
            if len(ob.InList) % 2 == 0: # perhaps pairs of Clone/Bodies
                for o in ob.InList:
                    if o.Name.startswith('Clone'):
                        numClones += 1
                    elif o.Name.startswith('Body'):
                        numBodies += 1
                    else:
                        invalidObjects = True
                        break
                if not invalidObjects:
                    if numBodies == numClones:
                        topLevelShapes.append(ob.Name)
    return topLevelShapes


###################################################################

def run_tests(doc):
    print("~"*42)
    print("get_filtered_objects")
    print_objects(get_filtered_objects(doc))
    
    print("~"*42)
    print("get_root_objects")
    print_objects(get_root_objects(doc))

    print("~"*42)
    print("doc.RootObjects")
    print_objects(doc.RootObjects)

    print("~"*42)
    print("getTopLevelObjects")
    print_objects(getTopLevelObjects(doc))
        
    print("~"*42)
    print("tests done :-)")



###################################################################
def main_test():
    "Main Tests."
    print("\n"*3)
    print("*"*42)
    print("run import_tests")
    
    prepare_freecad_import()
    import FreeCAD
    import Part
    #import Draft
    #import PartDesignGui
    
    # Context Managers not implemented..
    # see https://docs.python.org/3.8/reference/compound_stmts.html#with
    # with FreeCAD.open(self.config["filename"]) as doc:
    # so we use the classic try finally block:
    try:
        filename = "/home/stefan/mydata/freecad/tests/linking2/assembly.FCStd"
        doc = FreeCAD.open(filename)
        docname = doc.Name
        if not doc:
            print("Unable to open the given FreeCAD file")
        else:
            print("FreeCAD document:", filename)
            run_tests(doc)
    except Exception as e:
        raise e
    finally:
        FreeCAD.closeDocument(docname)
        print("*"*42)
        print("\n"*2)
        

if __name__ == '__main__':
    main_test()