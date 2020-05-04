#! /usr/bin/python
# -*- coding: future_fstrings -*-
"""
Make Blender python modules binaries
"""

# STD_LIB imports
import logging
import os
import pathlib
import platform
import subprocess
import sys
import typing
from typing import Dict, List, Optional, Tuple

# PYPI imports
import cmake
import cmakegenerators

# Relative imports
from bpybuild import BITNESS

LOGGER = logging.getLogger(__name__)

# Platform-specific PYPI imports
try:
    import distro
except ImportError:
    LOGGER.info("Package `distro` not available")

def get_configure_commands(source: pathlib.Path, destination: pathlib.Path,
                           bitness: Optional[int] = None,
                           with_cuda: Optional[bool]=False, 
                           with_optix: Optional[bool] = False,
                           optix_sdk_path: Optional[str] = None) -> List[List[str]]:

    commands = []

    os_configure_args = []

    if bitness is None: bitness = BITNESS

    if platform.system() == "Windows":

        generators = [generator for generator in 
                      cmakegenerators.get_generators() if 
                      generator.name.startswith("Visual Studio")]

        if len(generators) == 0:

            raise Exception("Windows users must have Visual Studio")

        filtered_generators = [generator for generator in generators if 
                                "Visual Studio".casefold() in 
                                generator.name.casefold()]

        if len(filtered_generators) > 0:

            generator_option : str = None

            if BITNESS == 64:

                filtered_generator_options = [option for option in filtered_generators[0].options if "64".casefold() in option.casefold()]

                if len(filtered_generator_options) > 0:

                    generator_option = filtered_generator_options[0]

                else:

                    raise Exception(f"{BITNESS}bit Visual Studio not found, "
                                    f"but Visual Studio is installed. Make "
                                    f"sure you have the correct compilers for "
                                    f"your Python platform ({BITNESS}bit)")

            else:

                generator_option = filtered_generators[0].options[-1]

            if generator_option is None:

                raise Exception(f"No C++ compilers detected on Windows {BITNESS}bit")

            os_configure_args += ["-G", generator_option]

        else:

            raise Exception(f"Visual Studio not found")        

    elif platform.system() == "Linux":

        os_configure_args += ["-DWITH_AUDASPACE=OFF"]

    elif platform.system() == "Darwin":

        os_configure_args += ["-DWITH_OPENMP=OFF", "-DWITH_AUDASPACE=OFF"]

    if platform.system() != "Windows":

        commands.append(["make", "-C", str(source.absolute()), "update"])

    if platform.system() == "Linux":

        commands.append([os.path.join(str(source.absolute()), 
                         "build_files", "build_environment", 
                         "install_deps.sh")])

    commands.append(['cmake',
                     '-DWITH_PLAYER=OFF', '-DWITH_PYTHON_INSTALL=OFF',
                     '-DWITH_PYTHON_MODULE=ON', 
                     f"-DPYTHON_VERSION={sys.version_info[0]}."
                     f"{sys.version_info[1]}", 
                     "-DWITH_CYCLES_CUDA_BINARIES=ON" if with_cuda else "",
                     "-DWITH_CYCLES_DEVICE_OPTIX=ON" if with_optix else "",
                     f"-DOPTIX_ROOT_DIR={optix_sdk_path}" if 
                     optix_sdk_path is not None else ""] + os_configure_args + 
                    ['-S' + str(source.absolute()), 
                     '-B' + str(destination.absolute())])

    return commands

def get_build_commands(location: pathlib.Path,
                       is_release: Optional[bool] = True) -> List[List[str]]:

    commands = []

    os_build_args = []

    if platform.system() == "Windows": # Windows specific build requirements

        os_build_args += ["--target", "INSTALL", "--config", 
                          f"{'Release' if is_release else 'Debug'}"]

        commands.append(["cmake", "--build", 
                        str(location.absolute())] + os_build_args)

    else:

        commands.append(["make", "-C", str(location.absolute()), "install"])

    return commands

def get_make_commands(source_location: pathlib.Path, 
                      build_location: Optional[pathlib.Path] = None,
                      bitness: Optional[int] = BITNESS,
                      is_release: Optional[bool] = True,
                      with_cuda: Optional[bool]=False, 
                      with_optix: Optional[bool] = False,
                      optix_sdk_path: Optional[str] = None) -> List[List[str]]:

    build_location = build_location if build_location else source_location

    return get_configure_commands(source_location, build_location, bitness, 
                                  with_cuda, with_optix, optix_sdk_path) +\
    get_build_commands(build_location, is_release)
