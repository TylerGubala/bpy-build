#! /usr/bin/python
# -*- coding: future_fstrings -*-
"""
Build blender into a python module
"""

from distutils.command.install_data import install_data
import os
import pathlib
import re
from setuptools import find_packages, setup, Extension
from setuptools.command.build_ext import build_ext
from setuptools.command.install import install
from setuptools.command.install_lib import install_lib
from setuptools.command.install_scripts import install_scripts
import shutil
import struct
import sys
from typing import List, Set

# Monkey-patch 3.4 and below

if sys.version_info < (3,5):

    def home_path() -> pathlib.Path:

        return pathlib.Path(os.path.expanduser("~"))

    pathlib.Path.home = home_path

PYTHON_EXE_DIR = os.path.dirname(sys.executable)

BLENDERPY_DIR = os.path.join(str(pathlib.Path.home()), ".blenderpy")
BLENDER_DESIRED_VERSION = None
BLENDER_VERSION_PATTERN = r'v(\d\.\d\d)(a|b|c|\-rc\d*)'
BLENDER_VERSION_REGEX = re.compile(BLENDER_VERSION_PATTERN)
BLENDER_VERSION_MASTER = 'master'

BITS = struct.calcsize("P") * 8

class BlenderVersion():
    """
    Info about a specific version, where the svn libs are located, etc
    """

    def __init__(self, version: str):
        from git import Repo as GitRepo
        from svn.remote import RemoteClient as SvnRepo

        self.git_repo = None
        self.svn_repo = None

        if version is BLENDER_VERSION_MASTER:

            self.git_repo = GitRepo(Blender.GIT_BASE_URL)
            self.svn_repo = SvnRepo(os.path.join(Blender.SVN_BASE_URL, 
                                                 Blender.SVN_MASTER))

        else:

            self.match = BLENDER_VERSION_REGEX.match(version)

            if self.match:

                matching_git_tags = [tag for tag in GitRepo(Blender.GIT_BASE_URL).tags 
                                     if tag == self.match.group(0)]

                self.git_repo = matching_git_tags[0] if matching_git_tags else None

                if self.git_repo:

                    pass

                else:

                    raise Exception(f"Blender {version} does not exist in git")

                svn_version_tag = (f"blender-{self.match.group(1)}"
                                   f"{self.match.group(2) if not self.match.group(2).startswith("-rc")}-release")

                blender_svn_tags = os.path.join(Blender.SVN_BASE_URL,
                                                Blender.SVN_TAGS)

                matching_svn_tags = [os.path.join(blender_svn_tags, tag) for 
                                     tag in 
                                     SvnRepo(os.path.join(Blender.SVN_BASE_URL,
                                             Blender.SVN_TAGS)).list() if 
                                     tag == svn_version_tag]

                self.svn_repo = SvnRepo(matching_svn_tags[0]) if matching_svn_tags else None

    def variants(self):
        """
        The different 'types' of releases this version supports
        """

        results = []

        for

        return results

class Blender():
    """
    Info about Blender, top level that gets the compatible version for us
    """

    GIT_BASE_URL = 'git://git.blender.org/blender.git'

    SVN_BASE_URL = 'https://svn.blender.org/svnroot/bf-blender'
    SVN_MASTER = 'trunk'
    SVN_TAGS = 'tags'

    def __init__(self):
        from git import Repo as GitRepo

        self.git_repo = GitRepo(self.GIT_BASE_URL)

    @property
    def versions(self) -> List(BlenderVersion):
        """
        The versions associated with Blender
        """

        return [BlenderVersion(tag) for tag in self.git_repo.tags] + [BlenderVersion(BLENDER_VERSION_MASTER)]

class CMakeExtension(Extension):
    """
    An extension to run the cmake build
    """

    def __init__(self, name, sources=[]):

        super().__init__(name = name, sources = sources)

class BlenderpyInstall(install):
    """
    We use this class solely to set the Blender desired version parameter
    """

    user_options = install.user_options + [
        ("version", None, "The desired Blender version to be installed "
                          "(ie: v2.74-rc2)")
    ]

    def initialize_options(self):
        super().initialize_options()
        self.version = None

    def run(self):
        global BLENDER_DESIRED_VERSION
        BLENDER_DESIRED_VERSION = self.version
        super().run()

class InstallCMakeLibsData(install_data):
    """
    Just a wrapper to get the install data into the egg-info
    """

    def run(self):
        """
        Outfiles are the libraries that were built using cmake
        """

        # There seems to be no other way to do this; I tried listing the
        # libraries during the execution of the InstallCMakeLibs.run() but
        # setuptools never tracked them, seems like setuptools wants to
        # track the libraries through package data more than anything...
        # help would be appriciated

        self.outfiles = self.distribution.data_files

class InstallCMakeLibs(install_lib):
    """
    Get the libraries from the parent distribution, use those as the outfiles

    Skip building anything; everything is already built, forward libraries to
    the installation step
    """

    def run(self):
        """
        Copy libraries from the bin directory and place them as appropriate
        """

        self.announce("Moving library files", level=3)

        # We have already built the libraries in the previous build_ext step

        self.skip_build = True

        bin_dir = self.distribution.bin_dir

        libs = [os.path.join(bin_dir, _lib) for _lib in 
                os.listdir(bin_dir) if 
                os.path.isfile(os.path.join(bin_dir, _lib)) and 
                os.path.splitext(_lib)[1] in [".dll", ".so"]
                and not (_lib.startswith("python") or _lib.startswith("bpy"))]

        for lib in libs:

            shutil.move(lib, os.path.join(self.build_dir,
                                          os.path.basename(lib)))

        # Mark the libs for installation, adding them to 
        # distribution.data_files seems to ensure that setuptools' record 
        # writer appends them to installed-files.txt in the package's egg-info
        #
        # Also tried adding the libraries to the distribution.libraries list, 
        # but that never seemed to add them to the installed-files.txt in the 
        # egg-info, and the online recommendation seems to be adding libraries 
        # into eager_resources in the call to setup(), which I think puts them 
        # in data_files anyways. 
        # 
        # What is the best way?

        self.distribution.data_files = [os.path.join(self.install_dir, 
                                                     os.path.basename(lib))
                                        for lib in libs]

        # Must be forced to run after adding the libs to data_files

        self.distribution.run_command("install_data")

        super().run()

class InstallBlenderScripts(install_scripts):
    """
    Install the scripts available from the "version folder" in the build dir
    """

    def run(self):
        """
        Copy the required directory to the build directory and super().run()
        """

        self.announce("Moving scripts files", level=3)

        self.skip_build = True

        bin_dir = self.distribution.bin_dir

        scripts_dirs = [os.path.join(bin_dir, _dir) for _dir in
                        os.listdir(bin_dir) if
                        os.path.isdir(os.path.join(bin_dir, _dir))]

        for scripts_dir in scripts_dirs:

            dst_dir = os.path.join(self.build_dir,
                                   os.path.basename(scripts_dir))

            # Mostly in case of weird things happening during build
            if os.path.exists(dst_dir):
                
                if os.path.isdir(dst_dir): 

                    shutil.rmtree(dst_dir)

                elif os.path.isfile(dst_dir):

                    os.remove(dst_dir)

            shutil.move(scripts_dir,
                        os.path.join(self.build_dir,
                                     os.path.basename(scripts_dir)))

        # Mark the scripts for installation, adding them to 
        # distribution.scripts seems to ensure that the setuptools' record 
        # writer appends them to installed-files.txt in the package's egg-info

        self.distribution.scripts = scripts_dirs

        super().run()

class BuildCMakeExt(build_ext):
    """
    Builds using cmake instead of the python setuptools implicit build
    """

    def run(self):
        """
        Perform build_cmake before doing the 'normal' stuff
        """

        for extension in self.extensions:

            if extension.name == "bpy":

                self.build_cmake(extension)

        super().run()

    def build_cmake(self, extension: Extension):
        """
        The steps required to build the extension
        """

        # We import the setup_requires modules here because if we import them
        # at the top this script will always fail as they won't be present

        from git import Repo as GitRepo
        from svn.remote import RemoteClient as SvnRepo

        self.announce("Preparing the build environment", level=3)

        blender_dir = os.path.join(BLENDERPY_DIR, "blender")

        build_dir = pathlib.Path(self.build_temp)

        extension_path = pathlib.Path(self.get_ext_fullpath(extension.name))

        os.makedirs(blender_dir, exist_ok=True)
        os.makedirs(str(build_dir), exist_ok=True)
        os.makedirs(str(extension_path.parent.absolute()), exist_ok=True)

        # Now that the necessary directories are created, ensure that OS 
        # specific steps are performed; a good example is checking on linux 
        # that the required build libraries are in place.

        os_build_args = []

        # Have to find the correct release tag to checkout here, as potentially
        # master may not be the correct one for this Python version. We use svn
        # to find whether or not master, or a specific tag supports the 
        # current python version

        if sys.platform == "win32": # Windows only steps

            import winreg

            vs_versions = []

            for version in [12, 14, 15]:

                try:

                    winreg.OpenKey(winreg.HKEY_CLASSES_ROOT,
                                   f"VisualStudio.DTE.{version}.0")

                except:

                    pass
                    
                else:

                    vs_versions.append(version)

            if not vs_versions:

                raise Exception("Windows users must have Visual Studio 2013 "
                                "or later installed")

            if max(vs_versions) == 15:

                os_build_args += ["-G", f"Visual Studio 15 2017"
                                        f"{' Win64' if BITS == 64 else ''}"]

            elif max(vs_versions) == 14:

                os_build_args += ["-G", f"Visual Studio 14 2015"
                                        f"{' Win64' if BITS == 64 else ''}"]

            elif max(vs_versions) == 12:

                os_build_args += ["-G", f"Visual Studio 12 2013"
                                        f"{' Win64' if BITS == 64 else ''}"]

            # TODO: Clean up here

            svn_lib_options += [f"win{64 if BITS == 64 else 'dows'}_vc{version}" 
                                for version in vs_versions]

            blender_svn_repo = SvnRepo(svn_url)

            os.makedirs(svn_dir, exist_ok=True)

            self.announce(f"Checking out svn libs from {svn_url}", level=3)

            try:
                
                blender_svn_repo.checkout(svn_dir)

            except Exception as e:

                self.warn("Windows users must have the svn executable "
                          "available from the command line")
                self.warn("Please install Tortoise SVN with \"command line "
                          "client tools\" as described here")
                self.warn("https://stackoverflow.com/questions/1625406/using-"
                          "tortoisesvn-via-the-command-line")
                raise e

        elif sys.platform == "linux": # Linux only steps

            # TODO: Test linux environment, issue #1

            pass

        elif sys.platform == "darwin": # MacOS only steps

            # TODO: Test MacOS environment, issue #2

            pass

        # Perform relatively common build steps

        # TODO: if blender desired version, then see if we can install that
        # Otherwise fail, if no desired version, find the latest version that
        # supports our python and install that

        git_repo = GitRepo(GIT_BASE_URL)
        svn_repo = SvnRepo(SVN_BASE_URL)

        if BLENDER_DESIRED_VERSION:

            match = BLENDER_VERSION_REGEX.match(BLENDER_DESIRED_VERSION)

            if match:

                # We have a blender version that conforms to the naming scheme
                # now to see if it actually exists in git and svn

                if match.group(0) in git_repo.tags:

                    # The version was tagged in the git repository
                    # now, format the version to match the svn versioning 
                    # scheme...

                    svn_version_tag = (f"blender-{match.group(1)}"
                                       f"{match.group(2) if not match.group(2).startswith("-rc")}-release")

                    svn_tag_repo = SvnRepo(os.path.join(SVN_BASE_URL, SVN_TAGS))

                    if svn_version_tag in svn_tag_repo.list():

                        # The version was released in svn and we found it
                        # Now, is it compatible with our OS and python version?

                    else:

                        raise Exception(f"{BLENDER_DESIRED_VERSION} was found "
                                        f"in the git repository but not the "
                                        f"svn repository.")

                else:

                    raise Exception(f"The provided version "
                                    f"{BLENDER_DESIRED_VERSION} does not "
                                    f"exist; please check "
                                    f"https://git.blender.org/gitweb/"
                                    f"gitweb.cgi/blender.git/tags for a list "
                                    f"of valid Blender releases")

            else:

                # The blender version did not conform to the naming scheme
                # fail and notify the user how to list the version

                raise Exception(f"The provided version "
                                f"{BLENDER_DESIRED_VERSION} did not match "
                                f"Blender's naming scheme. Please list your "
                                f"desired version as 'v' followed by a digit, "
                                f"followed by a period, followed by two "
                                f"digits and either 'a', 'b', 'c' or '-rc' "
                                f"(versions using '-rc' can optionally add "
                                f"a number which specifies which release "
                                f"candidate they want to install) such that "
                                f"the version looks like the following: "
                                f"v2.74-rc2")

        else:

            if sys.version_info >= (3, 6):

                # we can get from svn and git master branch

            else:

                # we must find a compatible version

        self.announce(f"Cloning Blender source from {BLENDER_GIT_REPO_URL}",
                      level=3)

        try:

            blender_git_repo = GitRepo(blender_dir)

        except:

            GitRepo.clone_from(BLENDER_GIT_REPO_URL, blender_dir)
            blender_git_repo = GitRepo(blender_dir)

        finally:
                
            blender_git_repo.heads.master.checkout()
            blender_git_repo.remotes.origin.pull()

        self.announce(f"Updating Blender git submodules", level=3)

        blender_git_repo.git.submodule('update', '--init', '--recursive')

        for submodule in blender_git_repo.submodules:
                
            submodule_repo = submodule.module()
            submodule_repo.heads.master.checkout()
            submodule_repo.remotes.origin.pull()

        self.announce("Configuring cmake project", level=3)

        self.spawn(['cmake', '-H'+blender_dir, '-B'+self.build_temp,
                    '-DWITH_PLAYER=OFF', '-DWITH_PYTHON_INSTALL=OFF',
                    '-DWITH_PYTHON_MODULE=ON', 
                    f"-DPYTHON_VERSION="
                    f"{sys.version_info[0]}.{sys.version_info[1]}"]
                    + os_build_args)
        
        self.announce("Building binaries", level=3)

        self.spawn(["cmake", "--build", self.build_temp, "--target", "INSTALL",
                    "--config", "Release"])

        # Build finished, now copy the files into the copy directory
        # The copy directory is the parent directory of the extension (.pyd)

        self.announce("Moving Blender python module", level=3)

        bin_dir = os.path.join(str(build_dir), 'bin', 'Release')
        self.distribution.bin_dir = bin_dir

        bpy_path = [os.path.join(bin_dir, _bpy) for _bpy in
                    os.listdir(bin_dir) if
                    os.path.isfile(os.path.join(bin_dir, _bpy)) and
                    os.path.splitext(_bpy)[0].startswith('bpy') and
                    os.path.splitext(_bpy)[1] in [".pyd", ".so"]][0]

        shutil.move(str(bpy_path), str(extension_path))

        # After build_ext is run, the following commands will run:
        # 
        # install_lib
        # install_scripts
        # 
        # These commands are subclassed above to avoid pitfalls that
        # setuptools tries to impose when installing these, as it usually
        # wants to build those libs and scripts as well or move them to a
        # different place. See comments above for additional information

setup(name='bpy-build',
      version='1.0.2a1',
      packages=find_packages(),
      ext_modules=[CMakeExtension(name="bpy")],
      description='A package that builds blender',
      long_description=open("./README.md", 'r').read(),
      long_description_content_type="text/markdown",
      keywords="Blender, 3D, Animation, Renderer, Rendering",
      classifiers=["Development Status :: 3 - Alpha",
                   "Environment :: Win32 (MS Windows)",
                   "Intended Audience :: Developers",
                   "License :: OSI Approved :: "
                   "GNU Lesser General Public License v3 (LGPLv3)",
                   "Natural Language :: English",
                   "Operating System :: Microsoft :: Windows :: Windows 10",
                   "Programming Language :: C",
                   "Programming Language :: C++",
                   "Programming Language :: Python",
                   "Programming Language :: Python :: 3.4",
                   "Programming Language :: Python :: 3.5",
                   "Programming Language :: Python :: 3.6",
                   "Programming Language :: Python :: 3.7",
                   "Programming Language :: Python :: Implementation :: "
                   "CPython",
                   "Topic :: Artistic Software",
                   "Topic :: Education",
                   "Topic :: Multimedia",
                   "Topic :: Multimedia :: Graphics",
                   "Topic :: Multimedia :: Graphics :: 3D Modeling",
                   "Topic :: Multimedia :: Graphics :: 3D Rendering",
                   "Topic :: Games/Entertainment"],
      author='Tyler Gubala',
      author_email='gubalatyler@gmail.com',
      license='GPL-3.0',
      python_requires=">=3.4.0",
      setup_requires=["cmake", "future-fstrings", "GitPython", 'svn'],
      url="https://github.com/TylerGubala/bpy-build",
      cmdclass={
          'build_ext': BuildCMakeExt,
          'install_data': InstallCMakeLibsData,
          'install_lib': InstallCMakeLibs,
          'install_scripts': InstallBlenderScripts
          }
     )
