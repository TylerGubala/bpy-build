#! /usr/bin/python
# -*- coding: utf-8 -*-
"""A module for building Blender

This module is mostly meant as an automation tool for building Blender and 
packaging up the module nicely for upload to "bpy-build" later using `twine`
"""

import os
import pathlib
import platform
import struct
import sys

# Monkey-patch 3.4 and below

if sys.version_info < (3,5):

    def home_path() -> pathlib.Path:

        return pathlib.Path(os.path.expanduser("~"))

    pathlib.Path.home = home_path

__all__ = ["make", "sources"]

BITNESS = struct.calcsize("P") * 8
