"""
windows build utilities convenience functions

These utilities help python find the correct C/C++ build tools
"""

import ctypes
import os
import shutil
import site
import subprocess
import sys
from typing import Dict, List, Optional, Set
import winreg

# site-packages dependencies imports
# install_requires these onlypy pip for windows
import svn.remote

# local imports
from .common_utils import (BPY_PACKAGE_DIR, is_32_bit, is_64_bit, PLATFORM, 
                           PYTHON_EXE_DIR, get_blender_git_sources,
                           recursive_copy)

def get_vs_version() -> Dict[str, int]:
    is_vs2013_available = False
    is_vs2015_available = False
    is_vs2017_available = False

    result = None

    # check for vs2013
    try:
        winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, 'VisualStudio.DTE.12.0')
    except:
        pass
    else:
        is_vs2013_available = True
        result = {'version': 12, 'year': 2013}

    # Check for vs2015
    try:
        winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, 'VisualStudio.DTE.14.0')
    except:
        pass
    else:
        is_vs2015_available = True
        result = {'version': 14, 'year': 2015}

    # Check for vs2017
    try:
        winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, 'VisualStudio.DTE.15.0')
    except:
        pass
    else:
        is_vs2017_available = True
        result = {'version': 15, 'year': 2017}

    if all([not available for available in [is_vs2013_available, 
                                            is_vs2015_available,
                                            is_vs2017_available]]):

        raise Exception("Visual Studio 13 (or higher) and c++ build tools are "
                        "required to build blender as a module, please "
                        "install Visual Studio and the c++ build tools too")

    return result

VS_VERSION =  get_vs_version()

# 32bit windows uses the windows path
def compute_svn_path() -> str:
    return "windows" if PLATFORM == 32 else "win64"

VS_LIBS = (f"{compute_svn_path()}_vc12" if 
           VS_VERSION == 2013 else f"{compute_svn_path()}_vc14")

BLENDER_SVN_REPO_URL = (f"https://svn.blender.org/svnroot/bf-blender/trunk/lib/"
                        f"{VS_LIBS}")

def get_blender_sources(root_dir: str):
    """
    Grab the sources from the git repo, as well as some windows libs from svn

    The windows libs from svn are specific to the windows build process,
    whereas linux just uses apt-get
    """
    # Root dir contains the blender directory as well as the lib and 
    # vs directory

    get_blender_git_sources(root_dir)

    # Get the code contained in the svn repo

    print(f"Getting svn code modules from {BLENDER_SVN_REPO_URL}")

    lib_dir = os.path.join(root_dir, 'lib', 'windows_vc12' if 
                           VS_VERSION == 2013 else 'windows_vc14')

    if not os.path.isdir(lib_dir):
        os.makedirs(lib_dir)

    blender_svn_repo = svn.remote.RemoteClient(BLENDER_SVN_REPO_URL)
    blender_svn_repo.checkout(lib_dir)

    print(f"Svn code modules checked out successfully into {lib_dir}")

def choose_generator() -> str:
    return (f"Visual Studio {VS_VERSION['version']} {VS_VERSION['year']}"
            f"{'' if PLATFORM == 32 else ' Win64'}")

def configure_blender_as_python_module(root_dir: str):
    """
    using a call to cmake, set the blender project to build as a python module

    We need to call this because make.bpy does not work currently...
    """

    print("Configuring Blender project as python module...")

    try:

        blender_dir = os.path.join(root_dir, 'blender')

        build_dir = os.path.join(root_dir, 'build')

        print(f"Creating solution in {build_dir}")

        # Most of this is hard-coded for now
        # TODO: replace static calls with something we know is best...
        subprocess.call(['cmake', '-H'+blender_dir, '-B'+build_dir,
                        '-DWITH_PLAYER=OFF', '-DWITH_PYTHON_INSTALL=OFF',
                        '-DWITH_PYTHON_MODULE=ON', f"-G{choose_generator()}"])

    except Exception as e:

        print("Something went wrong... check the console output for now")

        raise e

    else:

        print("Blender successfully configured!")

def make_blender_python(root_dir: str):
    """
    Using the automated build script, make bpy with the correct C++ build utils
    """

    install_solution = os.path.join(root_dir, 'build', 'INSTALL.vcxproj')

    blender_solution = os.path.join(root_dir, 'build', 'Blender.sln')
    platform = 'x' + str(PLATFORM)

    print("Making Blender from sources...")

    configure_blender_as_python_module(root_dir)

    try:

        subprocess.call(["cmake", "--build", ".", "--target build",
                         "--config Release"])

    except Exception as e:

        print("Make sure cmake is installed properly and that the prereqs "
              "described here are in place: https://wiki.blender.org/"
              "index.php/Dev:Doc/Building_Blender")

        raise e

    else:

        print("Built Blender python module successfully")

def install_blender_python(root_dir: str):
    """
    Copy files into the right places (what is the best way to do this?)

    version directory -> parent directory of current executable
    bpy.pyd -> site-packages/bpy of current environment
    *.dll besides python36.dll -> site-packages/bpy of current environment
    __init__.py (from this repo) -> site-packages/bpy of current environment
    """

    build_dir = None

    for dir_name in os.listdir(root_dir):

        if dir_name.startswith('build'): # This is the build directory

            build_dir = os.path.join(root_dir, dir_name)

            break

    if build_dir is None:

        raise Exception('Could not find the build dir')

    bin_dir = os.path.join(build_dir, 'bin', 'Release')

    bpy_to_copy = os.path.join(bin_dir, 'bpy.pyd')

    dirs_to_copy = [os.path.join(bin_dir, folder) for folder in 
                    os.listdir(bin_dir) if 
                    os.path.isdir(os.path.join(bin_dir, folder))]

    dlls_to_copy = [os.path.join(bin_dir, dll) for dll in 
                    os.listdir(bin_dir) if 
                    os.path.isfile(os.path.join(bin_dir, dll)) and 
                    os.path.splitext(dll)[1] == ".dll" and not
                    dll.startswith("python")]

    print("Copying files...")

    shutil.copy(bpy_to_copy, BPY_PACKAGE_DIR)

    for dll in dlls_to_copy:

        shutil.copy(dll, BPY_PACKAGE_DIR)

    print("Making required dirs")

    for dir_name in dirs_to_copy:

        dir_basename = os.path.basename(dir_name)

        dir_newname = os.path.join(PYTHON_EXE_DIR, dir_basename)

        try:
        
            os.makedirs(dir_newname)

        except FileExistsError:

            print(f"Directory {dir_newname} already exists, skipping...")

        else:

            print(f"Created folder {dir_newname}")

        recursive_copy(dir_name, dir_newname)

    print("Installation completed!")

def find_blender_python(root_dir: str) -> str:
    """
    Find the containing folder for bpy.pyd, all module contents are relative

    DEPRECIATED: Using install_blender_python instead
    """

    for dir_name, dir_path, file_names in os.walk(root_dir):

        if 'bpy.pyd' in file_names:

            return dir_name

    raise Exception(f"Blender python module failed to build; "
                    f"we could not find it in {root_dir}")