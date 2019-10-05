hello all,

i have setup a test at
https://github.com/s-light/io_import_fcstd/blob/master/dev/list_objects.py#L98

it uses ~4 different concepts to find the 'root' objects. (mostly from this thread..)
you can find them at
https://github.com/s-light/io_import_fcstd/blob/master/freecad_helper.py#L43

in my FreeCAD test file (freecad_linking_example/assembly.FCStd) i have used a bunch of different objects-
Part (grouping) / Part (Mesh) / one hidden / PartDesign Body / Links & Clones:
[img]https://raw.githubusercontent.com/s-light/io_import_fcstd/master/dev/freecad_linking_example/assembly_tree.png[/img]

the really funny thing is - the results are different from inside FreeCAD and from external Python console:

Intern:
[code]
>>> print("FreeCAD version:", FreeCAD.Version())
FreeCAD version: ['0', '19', '', 'https://code.launchpad.net/~vcs-imports/freecad/trunk', '2019/10/04 07:36:31']
>>> run_tests(FreeCAD.ActiveDocument)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
get_filtered_objects 29
     Name            Label                     TypeId                   p [Parents]    i [InList]    o [OutList]    g [Group]
obj: Part            my_final_assembly         App::Part                p 0    i 0    o 7    g 6
obj: Link            box_panel_part            App::Link                p 1    i 1    o 3    g 1
obj: Link001         front_panel_part          App::Link                p 1    i 1    o 1    g 1
obj: Link_i0         Link_i0                   App::LinkElement         p 2    i 2    o 3    g 1
obj: Link_i1         Link_i1                   App::LinkElement         p 2    i 2    o 3    g 1
obj: Link002         lamp_part                 App::Link                p 2    i 2    o 1    g 2
obj: Array           lamp_Array                Part::FeaturePython      p 1    i 1    o 3
obj: Body            floor_body                PartDesign::Body         p 1    i 2    o 5    g 3
obj: Sketch          floor_Sketch              Sketcher::SketchObject   p 1    i 2    o 1
obj: Pad             floor_Pad                 PartDesign::Pad          p 1    i 3    o 1
obj: Box             Cube_Hidden               Part::Box                p 0    i 0    o 0
obj: Sphere          world_sphere              Part::Sphere             p 0    i 0    o 0
obj: Part001         octagon_part              App::Part                p 0    i 0    o 2    g 1
obj: Body001         octagon_Body              PartDesign::Body         p 1    i 1    o 5    g 3
obj: Sketch001       octagon_sketch            Sketcher::SketchObject   p 1    i 2    o 1
obj: Pad001          octagon_Pad               PartDesign::Pad          p 1    i 3    o 1
obj: Fillet          octagon_Fillet            PartDesign::Fillet       p 2    i 2    o 2
obj: Fillet001       Fillet001                 PartDesign::Fillet       p 2    i 2    o 2
obj: Cone            blue_cone                 Part::Cone               p 0    i 0    o 0
obj: Box001          cube_colorfull            Part::Box                p 0    i 1    o 0
obj: Part002         floor_part                App::Part                p 0    i 0    o 2    g 1
obj: Body002         root_body                 PartDesign::Body         p 0    i 0    o 5    g 3
obj: Sketch002       Sketch002                 Sketcher::SketchObject   p 1    i 2    o 1
obj: Pad002          Pad002                    PartDesign::Pad          p 1    i 3    o 1
obj: Fillet002       Fillet002                 PartDesign::Fillet       p 2    i 2    o 2
obj: Body003         cube_part_clone_Body      PartDesign::Body         p 0    i 0    o 3    g 1
obj: Clone           cube_part_clone           PartDesign::FeatureBase  p 2    i 2    o 1
obj: Body004         floor_body_clone_Body     PartDesign::Body         p 0    i 0    o 3    g 1
obj: Clone001        floor_body_clone          PartDesign::FeatureBase  p 2    i 2    o 1
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
get_root_objects 10
     Name            Label                     TypeId                   p [Parents]    i [InList]    o [OutList]    g [Group]
obj: Part            my_final_assembly         App::Part                p 0    i 0    o 7    g 6
obj: Box             Cube_Hidden               Part::Box                p 0    i 0    o 0
obj: Sphere          world_sphere              Part::Sphere             p 0    i 0    o 0
obj: Part001         octagon_part              App::Part                p 0    i 0    o 2    g 1
obj: Cone            blue_cone                 Part::Cone               p 0    i 0    o 0
obj: Box001          cube_colorfull            Part::Box                p 0    i 1    o 0
obj: Part002         floor_part                App::Part                p 0    i 0    o 2    g 1
obj: Body002         root_body                 PartDesign::Body         p 0    i 0    o 5    g 3
obj: Body003         cube_part_clone_Body      PartDesign::Body         p 0    i 0    o 3    g 1
obj: Body004         floor_body_clone_Body     PartDesign::Body         p 0    i 0    o 3    g 1
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
doc.RootObjects 9
     Name            Label                     TypeId                   p [Parents]    i [InList]    o [OutList]    g [Group]
obj: Part            my_final_assembly         App::Part                p 0    i 0    o 7    g 6
obj: Box             Cube_Hidden               Part::Box                p 0    i 0    o 0
obj: Sphere          world_sphere              Part::Sphere             p 0    i 0    o 0
obj: Part001         octagon_part              App::Part                p 0    i 0    o 2    g 1
obj: Cone            blue_cone                 Part::Cone               p 0    i 0    o 0
obj: Part002         floor_part                App::Part                p 0    i 0    o 2    g 1
obj: Body002         root_body                 PartDesign::Body         p 0    i 0    o 5    g 3
obj: Body003         cube_part_clone_Body      PartDesign::Body         p 0    i 0    o 3    g 1
obj: Body004         floor_body_clone_Body     PartDesign::Body         p 0    i 0    o 3    g 1
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
get_toplevel_objects 10
     Name            Label                     TypeId                   p [Parents]    i [InList]    o [OutList]    g [Group]
obj: Part            my_final_assembly         App::Part                p 0    i 0    o 7    g 6
obj: Box             Cube_Hidden               Part::Box                p 0    i 0    o 0
obj: Sphere          world_sphere              Part::Sphere             p 0    i 0    o 0
obj: Part001         octagon_part              App::Part                p 0    i 0    o 2    g 1
obj: Cone            blue_cone                 Part::Cone               p 0    i 0    o 0
obj: Box001          cube_colorfull            Part::Box                p 0    i 1    o 0
obj: Part002         floor_part                App::Part                p 0    i 0    o 2    g 1
obj: Body002         root_body                 PartDesign::Body         p 0    i 0    o 5    g 3
obj: Body003         cube_part_clone_Body      PartDesign::Body         p 0    i 0    o 3    g 1
obj: Body004         floor_body_clone_Body     PartDesign::Body         p 0    i 0    o 3    g 1
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
tests done :-)
>>>
>>>
>>>
[/code]

Extern:
[code]
stefan@stefan-Latitude-E6510:~/mydata/github/blender/io_import_fcstd/dev (master +)$ python3 -i ./list_objects.py
Blender 'bpy' not available. No module named 'bpy'
/home/stefan/mydata/github/blender/io_import_fcstd/dev/list_objects.py
script_dir /home/stefan/mydata/github/blender/io_import_fcstd
base_dir /home/stefan/mydata/github/blender/io_import_fcstd
Configured FreeCAD path: /usr/lib/freecad-daily-python3/lib
Sheet Metal workbench loaded
FreeCAD version: ['0', '19', '', 'https://code.launchpad.net/~vcs-imports/freecad/trunk', '2019/10/04 07:36:31']
******************************************
run import_tests
FreeCAD document: ./dev/freecad_linking_example/assembly.FCStd
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
get_filtered_objects 16
     Name            Label                     TypeId                   p [Parents]    i [InList]    o [OutList]    g [Group]    
obj: Part            my_final_assembly         App::Part                p 0    i 0    o 7    g 6    
obj: Link            box_panel_part            App::Link                p 1    i 1    o 3    g 0    
obj: Link001         front_panel_part          App::Link                p 1    i 1    o 1    g 0    
obj: Link_i0         Link_i0                   App::LinkElement         p 2    i 2    o 3    g 0    
obj: Link_i1         Link_i1                   App::LinkElement         p 2    i 2    o 3    g 0    
obj: Link002         lamp_part                 App::Link                p 1    i 2    o 1    g 0    
obj: Array           lamp_Array                Part::FeaturePython      p 1    i 1    o 3    
obj: Sketch          floor_Sketch              Sketcher::SketchObject   p 0    i 0    o 1    
obj: Box             Cube_Hidden               Part::Box                p 0    i 0    o 0    
obj: Sphere          world_sphere              Part::Sphere             p 0    i 0    o 0    
obj: Part001         octagon_part              App::Part                p 0    i 0    o 1    g 0    
obj: Sketch001       octagon_sketch            Sketcher::SketchObject   p 0    i 0    o 1    
obj: Cone            blue_cone                 Part::Cone               p 0    i 0    o 0    
obj: Box001          cube_colorfull            Part::Box                p 0    i 0    o 0    
obj: Part002         floor_part                App::Part                p 0    i 0    o 1    g 0    
obj: Sketch002       Sketch002                 Sketcher::SketchObject   p 0    i 0    o 1    
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
get_root_objects 7
     Name            Label                     TypeId                   p [Parents]    i [InList]    o [OutList]    g [Group]    
obj: Part            my_final_assembly         App::Part                p 0    i 0    o 7    g 6    
obj: Box             Cube_Hidden               Part::Box                p 0    i 0    o 0    
obj: Sphere          world_sphere              Part::Sphere             p 0    i 0    o 0    
obj: Part001         octagon_part              App::Part                p 0    i 0    o 1    g 0    
obj: Cone            blue_cone                 Part::Cone               p 0    i 0    o 0    
obj: Box001          cube_colorfull            Part::Box                p 0    i 0    o 0    
obj: Part002         floor_part                App::Part                p 0    i 0    o 1    g 0    
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
doc.RootObjects 15
     Name            Label                     TypeId                   p [Parents]    i [InList]    o [OutList]    g [Group]    
obj: Part            my_final_assembly         App::Part                p 0    i 0    o 7    g 6    
obj: Origin001       Origin001                 App::Origin              p 0    i 0    o 6    
obj: Sketch          floor_Sketch              Sketcher::SketchObject   p 0    i 0    o 1    
obj: Box             Cube_Hidden               Part::Box                p 0    i 0    o 0    
obj: Sphere          world_sphere              Part::Sphere             p 0    i 0    o 0    
obj: Part001         octagon_part              App::Part                p 0    i 0    o 1    g 0    
obj: Origin003       Origin003                 App::Origin              p 0    i 0    o 6    
obj: Sketch001       octagon_sketch            Sketcher::SketchObject   p 0    i 0    o 1    
obj: Cone            blue_cone                 Part::Cone               p 0    i 0    o 0    
obj: Box001          cube_colorfull            Part::Box                p 0    i 0    o 0    
obj: Part002         floor_part                App::Part                p 0    i 0    o 1    g 0    
obj: Origin005       Origin005                 App::Origin              p 0    i 0    o 6    
obj: Sketch002       Sketch002                 Sketcher::SketchObject   p 0    i 0    o 1    
obj: Origin006       Origin006                 App::Origin              p 0    i 0    o 6    
obj: Origin007       Origin007                 App::Origin              p 0    i 0    o 6    
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
get_toplevel_objects 15
     Name            Label                     TypeId                   p [Parents]    i [InList]    o [OutList]    g [Group]    
obj: Part            my_final_assembly         App::Part                p 0    i 0    o 7    g 6    
obj: Origin001       Origin001                 App::Origin              p 0    i 0    o 6    
obj: Sketch          floor_Sketch              Sketcher::SketchObject   p 0    i 0    o 1    
obj: Box             Cube_Hidden               Part::Box                p 0    i 0    o 0    
obj: Sphere          world_sphere              Part::Sphere             p 0    i 0    o 0    
obj: Part001         octagon_part              App::Part                p 0    i 0    o 1    g 0    
obj: Origin003       Origin003                 App::Origin              p 0    i 0    o 6    
obj: Sketch001       octagon_sketch            Sketcher::SketchObject   p 0    i 0    o 1    
obj: Cone            blue_cone                 Part::Cone               p 0    i 0    o 0    
obj: Box001          cube_colorfull            Part::Box                p 0    i 0    o 0    
obj: Part002         floor_part                App::Part                p 0    i 0    o 1    g 0    
obj: Origin005       Origin005                 App::Origin              p 0    i 0    o 6    
obj: Sketch002       Sketch002                 Sketcher::SketchObject   p 0    i 0    o 1    
obj: Origin006       Origin006                 App::Origin              p 0    i 0    o 6    
obj: Origin007       Origin007                 App::Origin              p 0    i 0    o 6    
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
tests done :-)
******************************************
>>>

[/code]

interestingly i can't seem to access the 'Body' objects from the commandline version:
intern
[code]
>>> doc = FreeCAD.ActiveDocument
>>> doc.FileName
'/home/stefan/mydata/github/blender/io_import_fcstd/dev/freecad_linking_example/assembly.FCStd'
>>> obj = doc.getObjectsByLabel("octagon_Body")[0]
>>> obj
<body>
>>> obj.Label
'octagon_Body'
>>> [/code]

extern
[code]
>>> doc.FileName
'./freecad_linking_example/assembly.FCStd'
>>> obj = doc.getObjectsByLabel("octagon_Body")[0]
Traceback (most recent call last):
  File "<stdin>", line 1, in <module>
IndexError: list index out of range
>>> doc.getObjectsByLabel("octagon_Body")
[]
>>>
[/code]

is this expected??

sunny greetings
stefan

EDIT: rework output so its readable in the forum.
