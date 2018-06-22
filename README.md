# bpy-build
Python build script for Blender as a python module

It needs to be its own repository to satisfy the ```setup_requires``` of blenderpy

## Installation
```py -m pip install bpybuild```

This will install the python build scripts for blender as a python module. This does not build blender directly, this is just the module that is used as the setup-requires for the actual bpy module.

## Requirements

Users using this module must have git and GitPython, svn and the python svn package (windows) as well as platform specific build tools