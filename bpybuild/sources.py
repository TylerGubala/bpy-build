#! /usr/bin/python
# -*- coding: utf-8 -*-
"""Functions for searching for and retrieving Blender sources and libs
"""

# STD_LIB imports
import abc
import logging
import os
import pkg_resources
import pathlib
import platform
import posixpath
import re
import sys
import typing
from typing import Dict, List, Tuple

# PYPI imports
import git
from git import Repo as GitRepo
from git.exc import NoSuchPathError
from svn.exception import SvnException
from svn.remote import RemoteClient as SvnRepo

# Relative imports
from bpybuild import BITNESS

LOGGER = logging.getLogger(__name__)

# Platform-specific PYPI imports
try:
    import distro
except ImportError as e:
    # Only raise the error if it's Linux environment
    if platform.system == "Linux":
        LOGGER.info("Package `distro` not available")
        raise e

def git_remote_tags(url:str) -> List[Tuple[str, str]]:
    """Get the tags of a remote repository from the repo's `url`
    
    Arguments:
        url {str} -- The repo's address
    """

    return [(tag.split("\t")[0], tag.split("\t")[1]) for tag in 
             git.cmd.Git().ls_remote(url, tags=True).split("\n") if 
             not tag.endswith(r"^{}")]

def git_remote_tagnames(url:str) -> List[str]:
    """Get a list of just names of tags in the remote
    
    Arguments:
        url {str} -- The repo's address
    """

    return [posixpath.basename(tag[1]) for tag in git_remote_tags(url)]

class VersionNotFoundError(Exception):
    """Thrown when `git` or `svn` does not have the specified tag
    
    Arguments:
        Exception {[type]} -- Derived from base exception
    """

    pass

class SourceVersionControl(abc.ABC):
    """Represents code repositories that can be checked out
    """

    @abc.abstractmethod
    def checkout(self, full_path:pathlib.Path):
        """Retrieves the code in an impliementation-specific way

        Must be reimplimented per the code repository type
        """

        raise NotImplementedError

class SvnOSPlatform():

    PYTHON_PATTERN = (r'(?<=python)(\d)(?:\.?)(\d)')
    PYTHON_REGEX = re.compile(PYTHON_PATTERN)

    def __init__(self, svn_url: str):

        self.url = svn_url

        self.repo = SvnRepo(svn_url)

        self.svn_name = posixpath.basename(svn_url)

        self.os_name = None
        self.os_version = None
        self.processor = None
        self.bitness = None
        self.build_environment = None

        if self.svn_name.casefold().startswith("android".casefold()):

            self.os_name = "Android"
        
        elif self.svn_name.casefold().startswith("darwin".casefold()):

            self.os_name = "Darwin"

            darwin_platform_tokens = re.split(r"[\.-]", self.svn_name)

            if len(darwin_platform_tokens) >= 4:

                self.os_version = pkg_resources.parse_version(".".join(darwin_platform_tokens[1: -1]))

                self.processor = darwin_platform_tokens[-1]

        elif self.svn_name.casefold().startswith("linux".casefold()):

            self.os_name = "Linux"

        elif self.svn_name.casefold().startswith("win".casefold()):

            self.os_name = "Windows"

            if "64".casefold() in self.svn_name.casefold():

                self.bitness = 64

            else:

                self.bitness = 32

            if "vc".casefold() in self.svn_name.casefold():

                self.build_environment = "vc" + self.svn_name.split("vc")[-1]

        else:

            self.os_name = None

    def python_versions(self) -> List[Tuple[int, int]]:

        try:

            versions = [re.search(self.PYTHON_REGEX, 
                                  version["name"]) for version in 
                        self.repo.list(extended = True,
                                       rel_path = "python/lib") if
                        re.search(self.PYTHON_REGEX, version["name"]) and 
                        version["kind"] == "file"]

            return [(int(version.group(1)), int(version.group(2))) for version in versions]

        except SvnException:

            return []

class BlenderGit(SourceVersionControl):
    """The Blender `git` sources

    Provides the source code created by Blender Foundation developers.
    """

    BASE_URL = "git://git.blender.org/blender.git"

    # Here I store the Blender `git` sources in a folder in the home directory
    # so that I don't need to waste time constantly pulling from the repository;
    # only minor updates are needed here and there.

    def __init__(self, tag: str = None):

        self.tag = tag

        self.version = pkg_resources.parse_version(tag)

    @classmethod
    def tags(self) -> List[str]:
        """A list of release tags that git is aware of
        
        Returns:
            List[str] -- release tags that are available
        """
        
        return [version for version in git_remote_tagnames(self.BASE_URL) if 
                not str(version).startswith("Studio")] # what is a studio version?

    def checkout(self, full_path: pathlib.Path):
        """Retrieve Blender code from Git
        
        Keyword Arguments:
            full_path {pathlib.Path} -- place to clone code to 
        """

        try:

            repo = GitRepo(str(full_path))

        except:

            GitRepo.clone_from(self.BASE_URL, str(full_path))
            repo = GitRepo(str(full_path))
        
        repo.heads.master.checkout()
        repo.remotes.origin.pull()

        if self.tag is not None:

            repo.git.checkout(self.tag)

        repo.git.submodule('update', '--init', '--recursive')

        for submodule in repo.submodules:

            submodule_repo = submodule.module()
            submodule_repo.heads.master.checkout()
            submodule_repo.remotes.origin.pull()

            if self.tag is not None:

                try:

                    submodule_repo.git.checkout(self.tag)

                except:

                    pass

class BlenderSvn(SourceVersionControl):
    """The Blender `svn` library index

    Provides the set of required libraries to build Blender
    """

    BASE_URL = "https://svn.blender.org/svnroot/bf-blender"
    BASE_REPO = SvnRepo(BASE_URL)

    def __init__(self, svn_url: str):

        self.url = svn_url

        self.repo = SvnRepo(svn_url)

        self.version = pkg_resources.parse_version(os.path.basename(os.path.normpath(svn_url))
                                                   .replace("blender-", "")
                                                   .replace("-release", "")
                                                   .replace("-winfix", "")
                                                   .replace("-", "."))

        self._platforms = None

        self._platforms_dict = None

    @classmethod
    def tags(cls) -> List[str]:
        """The tags that `svn` found
        
        Able to be run as a class method so that we can query `svn` and build
        our list of svn supported versions

        Returns:
            List[str] -- List of strings, the full paths to the svn version
        """

        return [posixpath.join(cls.BASE_URL, "tags", _version) for _version in
                cls.BASE_REPO.list(rel_path="/tags") if 
                _version.startswith("blender")]

    def platforms(self) -> List[SvnOSPlatform]:

        if self._platforms is not None: # Don't perform expensive search twice

            return self._platforms

        results = self.get_platforms(self.url)

        self._platforms = results

        return results

    def platforms_dict(self) -> Dict[str, List[Tuple[int, int]]]:
        """Provides a dictionary of os and Python version compatibility

        Platforms are determined based on the os listed per release of Blender
        API in the `svn` repos
        """

        # SVN search and checkout is expensive; if this seems overkill it's
        # because any other method was taking ~ 5 minutes to list a
        # svn tag!

        if self._platforms_dict is not None: # Don't perform expensive search twice

            return self._platforms_dict

        results = self.get_platforms_dict(self.url)

        self._platforms_dict = results

        return results

    @staticmethod
    def get_platforms(url: str) -> List[SvnOSPlatform]:

        results = []

        try:

            for _os in SvnRepo(url).list(extended = True, rel_path = "lib"):

                if not any([_os["name"] == x for x in ["benchmarks", "package",
                                                       "python", "tests"]]):

                    results.append(SvnOSPlatform(posixpath.join(url + "lib", 
                                                 _os["name"])))

        except SvnException: # This can happen when the "lib" path does not exist

            pass

        return results

    @staticmethod
    def get_platforms_dict(url: str) -> Dict[str, List[Tuple[int, int]]]:

        results = {}

        try:

            _oss = [SvnOSPlatform(posixpath.join(url + "lib", 
                                                 _os["name"])) for
                    _os in SvnRepo(url).list(extended = True, rel_path = "lib") if
                    any([_os["name"].startswith(x) for x in ["android",
                                                             "darwin", "linux",
                                                             "win"]])]

            for _os in _oss:

                results[_os.svn_name] = _os.python_versions()

        except SvnException: # This can happen when the "lib" path does not exist

            pass

        return results

    def checkout(self, full_path: pathlib.Path):
        """Retrieve the `svn` sources
        
        Arguments:
            full_path {pathlib.Path} -- place to put svn sources
        """

        self.repo.checkout(str(full_path))

def git_tags() -> List[BlenderGit]:

    return [BlenderGit(str(tag)) for tag in BlenderGit.tags()]

def svn_tags() -> List[BlenderSvn]:

    return [BlenderSvn(tag_full_path) for tag_full_path in BlenderSvn.tags()]

def get_matched_versions() -> Dict[int, Tuple[List[BlenderGit], 
                                              List[BlenderSvn]]]:
    """Get pairs of sources based on available versions
    
    Returns:
        Dict[int, Tuple[List[BlenderGit],List[BlenderSvn]]]
         -- All versions of Blender and appropriate `BlenderGit` and 
            `BlenderSvn` objects
    """

    result = {}

    gits = git_tags()
    svns = svn_tags()

    for version in set([_svc.version for _svc in gits+svns]):

        result[version] = ([_git for _git in gits if _git.version == version],
                           [_svn for _svn in svns if _svn.version == version])

    return result

def get_compatible_sources():

    # There needs to be an svn library to determine Python version 
    # compatibility because we use the name of the Python .dll or .so file to 
    # determine Python version

    compatible_sources = {}

    matched_version_dict = get_matched_versions()

    for version in [_version for _version in matched_version_dict if 
                    matched_version_dict[_version][0] and 
                    matched_version_dict[_version][1]]:

        for _platform in matched_version_dict[version][1][0].platforms():

            if _platform.os_name is not None and\
               _platform.os_name.casefold() != platform.system().casefold():

                continue

            if _platform.bitness is not None and _platform.bitness != BITNESS:

                continue

            platform_python_versions = _platform.python_versions()

            if sys.version_info[:2] in platform_python_versions:

                compatible_sources[version] = matched_version_dict[version]

    return compatible_sources

def checkout_version(path:pathlib.Path, version: str, makedirs: bool = False):
    """Get all the Blender sources for a specific version
    
    Arguments:
        path {str} -- the path to check out the version
        version {int} -- the version to check out the sources of
    
    Keyword Arguments:
        makedirs {bool} -- automatically make directories (default: {False})
    """

    version = pkg_resources.parse_version(version)

    version_dict = get_matched_versions()

    if version in version_dict:

        if makedirs:

            os.makedirs(path, exist_ok=True)

        else:

            os.mkdir(path)

        # Checkout `git` sources
        version_dict[version][0][0].checkout(path)

        if len(version_dict[version]) == 2:
            # Checkout `svn` sources
            version_dict[version][1][0].checkout(path)

    else:

        raise VersionNotFoundError(f"Version {str(version)} of Blender does "
                                   f"not exist.")

def checkout_all(path: pathlib.Path, makedirs: bool = False):
    """Get all the Blender sources for all versions
    
    Arguments:
        path {str} -- The folder to check it out to
        makedirs {bool} -- Automatically create the checkout directory
    """

    for version, vcs in get_matched_versions().items():

        version_dir = os.path.join(path, str(version))

        if makedirs:

            os.makedirs(version_dir, exist_ok=True)

        else:

            os.mkdir(version_dir)

        # Checkout `git` sources
        vcs[0][0].checkout(version_dir)

        if len(vcs) == 2:
            # Checkout `svn` sources
            vcs[1][0].checkout(path)
