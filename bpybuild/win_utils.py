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

def is_admin():
    """
    Check if the user is a windows administrator

    NOT NECESSARY
    """
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def run_as_admin(program: Optional[str] = __file__):
    """
    If the user is not an adminstrator, elevate
    """

    if not is_admin():
        ctypes.windll.shell32.ShellExecuteW(None, "runas", 
                                            sys.executable, program, None, 1)

def get_vs_version():
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
        result = 2013

    # Check for vs2015
    try:
        winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, 'VisualStudio.DTE.14.0')
    except:
        pass
    else:
        is_vs2015_available = True
        result = 2015

    # Check for vs2017
    try:
        winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, 'VisualStudio.DTE.15.0')
    except:
        pass
    else:
        is_vs2017_available = True
        result = 2017

    if all([not available for available in [is_vs2013_available, 
                                            is_vs2015_available,
                                            is_vs2017_available]]):

        raise Exception("Visual Studio 13 (or higher) and c++ build tools are "
                        "required to build blender as a module, please "
                        "install Visual Studio and the c++ build tools too")

    return result

VS_VERSION =  get_vs_version()

VS_DEV_TOOLS_KNOWN_DIRS = {14.0: ["C:\\Program Files (x86)\\"
                                  "Microsoft Visual Studio\\2017\\BuildTools"]}

VS_DEV_TOOLS_KNOWN_COMMANDS = ['VsDevCmd.bat', 'vcvarsall.bat']

def find_vs_dev_tools_in_dir(base_dir_path: str) -> List[str]:
    """
    Find all of the build tools environments from the dir
    """

    dev_tools = None

    for dir_path, dir_names, file_names in os.walk(base_dir_path):

        for tool in VS_DEV_TOOLS_KNOWN_COMMANDS:

            for file_name in file_names:

                if tool.upper() == file_name.upper():

                    if dev_tools is None:

                        dev_tools = []

                    dev_tools.append(os.path.join(dir_path, file_name))

    return dev_tools

def find_vs_dev_tools_from_subkeys(base_key: winreg.HKEYType) -> Dict[str, List[str]]:
    """
    Find dev tools from the basekey that are specific to different vs versions

    Because there are different key locations and paths depending on the vs
    version, it can be highly version specific; this function wrangles the
    specificness for each of the cases.
    """

    dev_tools = {}

    for i in range(winreg.QueryInfoKey(base_key)[0]):

        sub_key_name = winreg.EnumKey(base_key, i)

        if sub_key_name.upper() == 'SXS': # Because VS2017

            vs2017_key_root = winreg.OpenKey(base_key, sub_key_name)

            for j in range(winreg.QueryInfoKey(vs2017_key_root)[0]):

                final_key_name = winreg.EnumKey(vs2017_key_root, j)

                if final_key_name.upper() == 'VS7':

                    final_key = winreg.OpenKey(vs2017_key_root, final_key_name)

                    for k in range(winreg.QueryInfoKey(final_key)[1]):

                        value_tuple = winreg.EnumValue(final_key, k)

                        try:

                            value = value_tuple[1]

                            dict_key_name = float(value_tuple[0])

                        except:

                            pass

                        else:

                            found_dev_tools = find_vs_dev_tools_in_dir(value)

                            if found_dev_tools is not None:

                                try:

                                    ver_dev_tools = dev_tools[dict_key_name]

                                except KeyError:

                                    dev_tools[dict_key_name] = [found_dev_tools]

                                else:

                                    ver_dev_tools += found_dev_tools

        elif sub_key_name == '14.0': # Because VS2015

            vs2015_key_root = winreg.OpenKey(base_key, sub_key_name)

            for j in range(winreg.QueryInfoKey(vs2015_key_root)[0]):

                vs2015_subkey_name = winreg.EnumKey(vs2015_key_root, j)

                if vs2015_subkey_name.upper() == 'SETUP':

                    setup_key = winreg.OpenKey(vs2015_key_root,
                                               vs2015_subkey_name)

                    for k in range(winreg.QueryInfoKey(setup_key)[0]):

                        setup_subkey_name = winreg.EnumKey(setup_key, k)

                        if setup_subkey_name.upper() == 'VC':

                            vc_key = winreg.OpenKey(setup_key, 
                                                    setup_subkey_name)

                            for h in range(winreg.QueryInfoKey(vc_key)[1]):

                                value_tuple = winreg.EnumValue(vc_key, h)

                                if value_tuple[0].upper() == 'PRODUCTDIR':

                                    value = value_tuple[1]

                                    found_dev_tools = find_vs_dev_tools_in_dir(value)

                                    if found_dev_tools is not None:

                                        dict_key_name = float(sub_key_name)

                                        try:

                                            ver_dev_tools = dev_tools[dict_key_name]

                                        except KeyError:

                                            dev_tools[dict_key_name] = [found_dev_tools]

                                        else:

                                            dev_tools[dict_key_name] += found_dev_tools

        elif sub_key_name == '12.0': # Because VS2013

            vs2013_key_root = winreg.OpenKey(base_key, sub_key_name)

            for j in range(winreg.QueryInfoKey(vs2013_key_root)[0]):

                vs2013_subkey_name = winreg.EnumKey(vs2013_key_root, j)

                if vs2013_subkey_name.upper() == 'SETUP':

                    setup_key = winreg.OpenKey(vs2013_key_root,
                                               vs2013_subkey_name)

                    for k in range(winreg.QueryInfoKey(setup_key)[0]):

                        setup_subkey_name = winreg.EnumKey(setup_key, k)

                        if setup_subkey_name.upper() == 'VC':

                            vc_key = winreg.OpenKey(setup_key, 
                                                    setup_subkey_name)

                            for h in range(winreg.QueryInfoKey(vc_key)[1]):

                                value_tuple = winreg.EnumValue(vc_key, h)

                                if value_tuple[0].upper() == 'PRODUCTDIR':

                                    value = value_tuple[1]

                                    found_dev_tools = find_vs_dev_tools_in_dir(value)

                                    if found_dev_tools is not None:

                                        dict_key_name = float(sub_key_name)

                                        try:

                                            ver_dev_tools = dev_tools[dict_key_name]

                                        except KeyError:

                                            dev_tools[dict_key_name] = [found_dev_tools]

                                        else:

                                            dev_tools[dict_key_name] += found_dev_tools

    return dev_tools

def find_vs_dev_tools_from_keys() -> List[str]:
    """
    Subdivides the search down to 32bit vs 64bit
    """

    if PLATFORM == 32: # 32 bit checks

        try:
            
            base_key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, 
                                      "SOFTWARE\\Microsoft\\VisualStudio")

        except:

            raise Exception(f"Detected {PLATFORM}bit Python but "
                            f"{PLATFORM}bit Visual Studio is not installed")

        else:

            print(f"Found {PLATFORM}bit Visual Studio installed, searching "
                  f"for C/C++ build tools...")

            return find_vs_dev_tools_from_subkeys(base_key)
            
    elif PLATFORM == 64:

        try:

            base_key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, 
                                      "SOFTWARE\\WOW6432Node\\Microsoft\\"
                                      "VisualStudio")

        except:

            raise Exception(f"Detected {PLATFORM}bit Python but "
                            f"{PLATFORM}bit Visual Studio is not installed")

        else:

            print(f"Found {PLATFORM}bit Visual Studio installed, searching "
                  f"for C/C++ build tools...")

            return find_vs_dev_tools_from_subkeys(base_key)

    else:

        print(f"{PLATFORM}bit not supported")

def find_vs_dev_tools_from_known_dirs() -> List[str]:
    """
    Finds build tools based on guesses about the system archetecture
    """

    dev_tools = {}

    for version in VS_DEV_TOOLS_KNOWN_DIRS:

        for root_dir_path in VS_DEV_TOOLS_KNOWN_DIRS[version]:

            found_dev_tools = find_vs_dev_tools_in_dir(root_dir_path)

            if found_dev_tools is not None:

                try:

                    ver_dev_tools = dev_tools[version]

                except KeyError:

                    dev_tools[version] = []

                else:

                    ver_dev_tools += found_dev_tools

    return dev_tools

def get_all_vc_dev_tools() -> Dict[float, Set[str]]:
    """
    Find the directory from which we can execute vcvarsall

    Vcvars all is the build setup for c/c++ on windows
    """

    all_dev_tools = {}

    dev_tools_from_keys = find_vs_dev_tools_from_keys()

    dev_tools_from_known_dirs = find_vs_dev_tools_from_known_dirs()

    for dev_tool_version in dev_tools_from_keys:

        try:

            ver_dev_tool = all_dev_tools[dev_tool_version]

        except KeyError:

            all_dev_tools[dev_tool_version] = set()

            ver_dev_tool = all_dev_tools[dev_tool_version]

        finally:

            for dev_tool in dev_tools_from_keys[dev_tool_version]:

                ver_dev_tool.update(dev_tool)

    for dev_tool_version in dev_tools_from_known_dirs:

        try:

            ver_dev_tool = all_dev_tools[dev_tool_version]

        except KeyError:

            all_dev_tools[dev_tool_version] = set()

            ver_dev_tool = all_dev_tools[dev_tool_version]

        finally:

            for dev_tool in dev_tools_from_known_dirs[dev_tool_version]:

                ver_dev_tool.update(dev_tool)

    return all_dev_tools

ALL_VC_DEV_TOOLS = get_all_vc_dev_tools()

VS_LIBS = (f"lib/win{PLATFORM}_vc12" if 
           VS_VERSION == 2013 else f"lib/win{PLATFORM}_vc14")

BLENDER_SVN_REPO_URL = (f"https://svn.blender.org/svnroot/bf-blender/trunk/"
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

    blender_svn_repo = svn.remote.RemoteClient(BLENDER_SVN_REPO_URL)

    blender_svn_repo.checkout(lib_dir)

    print(f"Svn code modules checked out successfully into {lib_dir}")

    # print(f"Copying svn libs to the other directory blender wants...")

    vc_ver = str(int(max(ALL_VC_DEV_TOOLS))) # I would rather find the version and use it below

    lib_dir2 = os.path.join(root_dir, "lib", f"win{PLATFORM}_vc14")

    if not os.path.isdir(lib_dir2):

        os.makedirs(lib_dir2)

    # common_utils.recursive_copy(lib_dir, lib_dir2) instead of copy, let's just checkout

    blender_svn_repo.checkout(lib_dir2)

def configure_blender_as_python_module(root_dir: str, version: int):
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
                        '-DWITH_PYTHON_MODULE=ON', f"-GVisual Studio {version} 2017 "
                        f"Win{PLATFORM}"])

    except Exception as e:

        print("Something went wrong... check the console output for now")

        raise e

    else:

        print("Blender successfully configured!")

def make_blender_python(root_dir: str) -> str:
    """
    Using the automated build script, make bpy with the correct C++ build utils
    """

    install_solution = os.path.join(root_dir, 'build', 'INSTALL.vcxproj')

    blender_solution = os.path.join(root_dir, 'build', 'Blender.sln')
    platform = 'x' + str(PLATFORM)

    # How to best determine the best dev tools to use?

    if not ALL_VC_DEV_TOOLS:

        raise Exception("Visual Studio 13 (or higher) and c++ build tools are "
                        "required to build blender as a module, please "
                        "install Visual Studio and the c++ build tools too")

    best_dev_tool = None

    for dev_tool in ALL_VC_DEV_TOOLS[max(ALL_VC_DEV_TOOLS)]:

        # Get the first in the list
        # Easy, but is it the best?
        best_dev_tool = dev_tool
        break

    if best_dev_tool is None:

        raise Exception("Could not determine the best dev tool")

    print("Making Blender from sources...")

    configure_blender_as_python_module(root_dir, int(max(ALL_VC_DEV_TOOLS)))

    try:

        # I did not have much luck using the make.bat file; it was easier to
        # follow build steps myself

        # subprocess.call([os.path.join(root_dir, 'blender/make.bat'), 'bpy', 
        #                  str(VS_VERSION)])

        subprocess.call(['C:\\Program Files (x86)\\Microsoft Visual Studio\\2017\\BuildTools\\VC\\Auxiliary\\Build\\vcvars64.bat', '&&',
                         'msbuild', blender_solution, '/target:build',
                         '/property:Configuration=Release',
                         f"/p:platform={platform}",
                         '/flp:Summary;Verbosity=minimal;LogFile=%BUILD_DIR%\Build.log',
                         '&&','msbuild', install_solution,
                         '/property:Configuration=Release',
                         f"/p:platform={platform}"])

        #subprocess.call([best_dev_tool, '&&',
        #                 'msbuild', blender_solution, '/target:build',
        #                 '/property:Configuration=Release',
        #                 f"/p:platform={platform}",
        #                 '/flp:Summary;Verbosity=minimal;LogFile=%BUILD_DIR%\Build.log',
        #                 '&&','msbuild', install_solution,
        #                 '/property:Configuration=Release',
        #                 f"/p:platform={platform}"])

        # subprocess.call(['msbuild', blender_solution, '/target:build',
        #                  '/property:Configuration=Release',
        #                  f"/p:platform={platform}",
        #                  '/flp:Summary;Verbosity=minimal;LogFile=%BUILD_DIR%\Build.log'])

        # subprocess.call(['msbuild', install_solution,
        #                  '/property:Configuration=Release',
        #                  f"/p:platform={platform}"])

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
                    os.path.splitext(dll)[1] == ".dll"]

    print(f"Making a package for bpy at: {BPY_PACKAGE_DIR}")

    try:
        
        os.makedirs(BPY_PACKAGE_DIR)

    except FileExistsError:

        print("Bpy directory already exists, skipping...")

    else:

        print(f"Created folder {BPY_PACKAGE_DIR}")

    print("Writing __init__.py...")

    with open(os.path.join(BPY_PACKAGE_DIR, "__init__.py"), "w") as bpy_init:

        bpy_init.write("from .bpy import *")

    print("Bpy module init written\nCopying files...")

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