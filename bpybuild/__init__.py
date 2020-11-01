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

__all__ = ["make", "sources"]

BITNESS = struct.calcsize("P") * 8
