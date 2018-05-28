"""
A blender builder python module, gets blender sources then builds them
"""

import os
import pathlib
import site
import sys

from .common_utils import is_linux, is_mac, is_windows

if is_linux():
    # linux imports go here
    from .linux_utils import install_blender_python, get_blender_sources, make_blender_python
elif is_windows():
    # windows imports go here
    from .win_utils import install_blender_python, get_blender_sources, make_blender_python
elif is_mac():
    # Mac imports goes here
    from .mac_utils import install_blender_python, get_blender_sources, make_blender_python
else:
    raise OSError(f"This module does not support {sys.platform}")

def create_python_module():
    """
    Creates a python module of blender
    """

    if os.path.basename(os.path.realpath(sys.executable)).startswith('blender'):

        raise Exception("You are already in blender, you do not need to build bpy!")

    root_dir = os.path.join(pathlib.Path.home(), '.blenderpy')

    if not os.path.isdir(root_dir):

        os.makedirs(root_dir)

        print(f"Created directory {root_dir}")

    else:

        print(f"Found blenderpy directory at {root_dir}")

    get_blender_sources(root_dir)

    make_blender_python(root_dir)

    install_blender_python(root_dir)
