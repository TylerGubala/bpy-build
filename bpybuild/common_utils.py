"""
Cross platform utilities for building blender
"""

import os
import shutil
import subprocess
import struct
import site
import sys

# site-packages imports
# install_requires these for all platforms
import cmake
from git import Repo

PYTHON_EXE_DIR = os.path.dirname(sys.executable)

BPY_PACKAGE_DIR = site.getsitepackages()[1]

BLENDER_GIT_REPO_URL = 'git://git.blender.org/blender.git'

def is_linux():
    return sys.platform in ['linux', 'linux2']

def is_windows():
    return sys.platform == 'win32'

def is_mac():
    return sys.platform == 'darwin'

def archetecture_bit_width() -> int:
    return struct.calcsize("P") * 8

def is_32_bit() -> bool:
    return archetecture_bit_width == 32

def is_64_bit() -> bool:
    return archetecture_bit_width == 64

PLATFORM = archetecture_bit_width()

def get_blender_git_sources(root_dir: str):
    """
    Check out the most up to date blender sources

    TODO: Display progress somehow
    """

    repo_directory = os.path.join(root_dir, 'blender')

    try:

        blender_git_repo = Repo(repo_directory)

    except:

        if not os.path.isdir(repo_directory):
        
            os.makedirs(repo_directory)

        print(f"Cloning blender from {BLENDER_GIT_REPO_URL}")

        Repo.clone_from(BLENDER_GIT_REPO_URL, repo_directory)

        print(f"Blender successfully cloned into {repo_directory}")

        blender_git_repo = Repo(repo_directory)

    finally:

        blender_git_repo.heads.master.checkout()

        blender_git_repo.remotes.origin.pull()

    print("Updating submodules...")

    # The submodule update method may fail due to a permissions error

    # GitPython's implimentation of submodule_update (derived from the 
    # RootModule object's update command) automatically is recursive 
    # and autoinits, so we don't have to worry about that
    blender_git_repo.git.submodule('update', '--init', '--recursive')

    print(f"Submodules updated!")

    print("Checking out master for submodules")

    for submodule in blender_git_repo.submodules:

        submodule_repo = submodule.module()

        submodule_repo.heads.master.checkout()

        submodule_repo.remotes.origin.pull()

def recursive_copy(src: str, dst: str):

    for shortname in os.listdir(src):

        fullname = os.path.join(src, shortname)

        if os.path.isfile(fullname):
            shutil.copy(fullname, dst)

        elif os.path.isdir(fullname):
            new_dst = os.path.join(dst, shortname)
            os.mkdir(new_dst)
            recursive_copy(os.path.abspath(fullname), new_dst)
