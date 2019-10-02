<!--lint disable list-item-indent-->
<!--lint disable list-item-bullet-indent-->

# io_import_fcstd
blender importer for FreeCAD files

based on gist [yorikvanhavre/FreeCAD .FCStd importer for Blender 2.80](https://gist.github.com/yorikvanhavre/680156f59e2b42df8f5f5391cae2660b)

# description

This script imports FreeCAD .FCStd files into Blender.
This is a work in progress,
so not all geometry elements of FreeCAD might be supported at this point.

The development of this addon happens on the FreeCAD forum at
[https://forum.freecadweb.org](https://forum.freecadweb.org)
(no thread yet, please create one ;) !)

# warning

This addon requires FreeCAD to be installed on your system.  
A word of warning, your version of FreeCAD must be compiled
with the same version of python as Blender.

The first two numbers of the python version must be the same.  
For example, if Blender is using Python 3.7.2, your version of FreeCAD must
use Python 3.7 too (the third number after 3.7 can be different)

Once you have a Python3 version of FreeCAD installed, the FreeCAD
Python module must be known to Blender.

There are several ways to obtain this:
1. Set the correct path to FreeCAD.so (or FreeCAD.pyd on windows) in
the Addons preferences in user settings, there is a setting for
that under the addon panel
2. Copy or symlink FreeCAD.so (or FreeCAD.pyd on windows) to one of the
directories from the list you get when doing this in a Python console:  
`import sys; print(sys.path)`  
On Debian/Ubuntu and most Linux systems, an easy way to do this is is
to symlink FreeCAD.so to your local (user) python modules folder:  
`ln -s /path/to/FreeCAD.so /home/YOURUSERNAME/.local/lib/python3.6/site-packages`  
(make sure to use the same python version your blender is using instead
of 3.6)
3. A more brutal way if the others fail is to
uncomment the following line in the script
and set the correct path to where your FreeCAD.so or FreeCAD.pyd resides:
`import sys; sys.path.append("/path/to/FreeCAD.so")`

A simple way to test if everything is OK is to enter the following line
in the Python console of Blender.  
If no error message appears, everything is fine:

`import FreeCAD`

# TODO
- support PartDesign
- support clones + hires
- support texts, dimensions, etc (non-part/mesh objects)
