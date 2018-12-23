# bpy-build
Python build script for Blender as a python module

It needs to be its own repository to satisfy the `install_requires` of blenderpy

## Note

While it is possible to install this module standalone, you will probably get better results installing `blenderpy` via `pip install bpy` rather than installing `pip install bpy-build`, as `pip install bpy` will attempt to take care of making sure the `bpy` installation is good.

## Option 1 - Get prebuilt bdist_wheel from pypi

### Prerequisites

1. A supported python installation with pip installed

### Installation

`py -m pip install bpy-build`

## Option 2 - Build from sources using pypi

### Prerequisites

1. Windows users must have Visual Studio 2013 or later and C++ build tools installed to build from sources
2. ALL users must have an SVN command-line provider to build from sources (see https://stackoverflow.com/questions/1625406/using-tortoisesvn-via-the-command-line) (this is a requirement as it is how we determine the correct release tag to grab, if any)
3. All users must `py -m pip install cmake` in their python environment to build from sources (currently adding it as a `setup_requires` does not install it properly); after build it may be uninstalled with `py -m pip uninstall cmake`
4. Users of Python versions below 3.6 must have `future-fstrings` installed `pip install -U future-fstrings`
5. Users of Python versions 3.4 and below will probably need to update `setuptools` `pip install -U setuptools`
6. Up-to-date `wheel`

### Installation

`py -m pip install bpy-build --no-binary`

### How it works

0. Create overriding classes CMakeExtension & BuildCMake, which inheirit from the setuptools classes; bpy is a python extension (.pyd) and an instance of CMakeExtension, BuildCMake is the command that is run when installing the extension from pip (or running setup.py)
1. Using GitPython, clone Blender sources from https://git.blender.org/
2. If on Windows, detect the installed version of Visual Studio and 64bit vs 32bit, and download the appropriate svn library based on that
3. Using cmake, configure blender as a python module per the Ideasman42 wiki page (now defunct) https://wiki.blender.org/wiki//User:Ideasman42/BlenderAsPyModule; configure this build solution in the build_temp directory of the bpy package
4. Using cmake, build the configured solution
5. Place the built binaries in the built extension parent directory (important!)
6. Relocate the /<Version> directory (i.e: /2.79) into the directory containing the executable from which this installation was spawned (where 'python.exe' is)
7. Clean up using the remaining functionality from the superclasses `build_ext` and `Extension`
8. bpy.pyd/ .so should now be installed into the site-packages