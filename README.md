<!--lint disable list-item-indent-->
<!--lint disable list-item-bullet-indent-->

# io_import_fcstd
blender importer for FreeCAD files

based on gist [yorikvanhavre/FreeCAD .FCStd importer for Blender 2.80](https://gist.github.com/yorikvanhavre/680156f59e2b42df8f5f5391cae2660b)

# description

This script imports FreeCAD .FCStd files into Blender.  
This is a work in progress, so not all geometry elements of FreeCAD
might be supported at this point.
And the `update` option will make some mess on older already imported objects..


The development of this addon happens on the FreeCAD forum at  
[FreeCAD .FCStd importer for Blender 2.80](https://forum.freecadweb.org/viewtopic.php?f=22&t=39778)

# download
if you feel comfortable with git clone the repository -
it is the easiest way to stay up to date ;-)

otherwise you can use the download button to get a zip file.
than you can install it in blender by going to
`edit` - `preferences` - `Add-ons`
and there is a button `Install...` in the top right corner.
select the downloaded zip..
then enable it (you can search for FreeCAD)
after this please read [setup](#setup)
(check the addon-preferences and set your path to FreeCAD lib folder..)

# setup

This addon requires FreeCAD to be installed on your system.  
A word of warning, your version of FreeCAD must be compiled
with the same version of python as Blender.

The first two numbers of the python version must be the same.  
For example, if Blender is using Python 3.7.2, your version of FreeCAD must
use Python 3.7 too (the third number after 3.7 can be different)

Once you have a Python3 version of FreeCAD installed, the FreeCAD
Python module must be known to Blender.

<!-- There are several ways to obtain this: -->
Set the correct path to FreeCAD.so (or FreeCAD.pyd on windows) in
the Addons preferences in user settings, there is a setting for
that under the addon panel.
(these settings are only shown if the addon is enabled)
<!-- 2. Copy or symlink FreeCAD.so (or FreeCAD.pyd on windows) to one of the
directories from the list you get when doing this in a Python console:  
`import sys; print(sys.path)`  
On Debian/Ubuntu and most Linux systems, an easy way to do this is is
to symlink FreeCAD.so to your local (user) python modules folder:  
`ln -s /path/to/FreeCAD.so /home/YOURUSERNAME/.local/lib/python3.6/site-packages`  
(make sure to use the same python version your blender is using instead
of 3.6) -->


A simple way to test if everything is OK is to enter the following line
in the Python console of Blender.  
If no error message appears, everything is fine:

`import FreeCAD`


# working with...
currently i only test under linux 64bit.
please let me know in the issues if it is / is not working for you on other setups.


Blender
```
version: 3.1.0, branch: master, commit date: 2022-03-08 18:16, hash: c77597cd0e15, type: release
build date: 2022-03-09, 00:34:48
platform: 'Linux-5.11.0-50-generic-x86_64-with-glibc2.33'
```
and
FreeCAD 0.19
```python
OS: Ubuntu 21.04 (KDE/plasma)
Word size of OS: 64-bit
Word size of FreeCAD: 64-bit
Version: 0.19.
Build type: Release
Branch: unknown
Hash: 0d9536ed3e8c7f40197b5606e1b7873625e1d6fe
Python version: 3.9.5
Qt version: 5.15.2
Coin version: 4.0.0
OCC version: 7.5.2
Locale: English/United States (en_US)


# build in python console:
Python 3.9.5 (default, Nov 18 2021, 16:00:48)
[GCC 10.3.0] on linux
Type 'help', 'copyright', 'credits' or 'license' for more information.
>>> App.Version()[4]
'2021/07/21 08:10:00'
```
and
FreeCAD-daily 0.20
```python
OS: Ubuntu 21.04 (KDE/plasma)
Word size of FreeCAD: 64-bit
Version: 0.20.
Build type: Release
Branch: unknown
Hash: 4acef3f14fe694f28f7935108d36341b8df83a39
Python version: 3.9.5
Qt version: 5.15.2
Coin version: 4.0.0
OCC version: 7.5.2
Locale: English/United States (en_US)

# build in python console:
Python 3.9.5 (default, Nov 18 2021, 16:00:48)
[GCC 10.3.0] on linux
>>> App.Version()[4]
'2022/01/26 04:18:00'
```

# TODO
see the [issues for open points](https://github.com/s-light/io_import_fcstd/issues).

- support clones
- support texts, dimensions, etc (non-part/mesh objects)
