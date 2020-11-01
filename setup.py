#! /usr/bin/python
# -*- coding: utf-8 -*-
"""
Setup for build scripting
"""

from setuptools import find_packages, setup

setup(name='bpy-build',
      version='2.0.0',
      packages=find_packages(),
      description='Find Blender sources in version control, create build scripts',
      long_description=open("./README.md", 'r').read(),
      long_description_content_type="text/markdown",
      keywords="Blender, 3D, Animation, Renderer, Rendering",
      classifiers=["Development Status :: 3 - Alpha",
                   "Environment :: Win32 (MS Windows)",
                   "Intended Audience :: Developers",
                   "License :: OSI Approved :: "
                   "GNU General Public License v3 (GPLv3)",
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
      install_requires=["cmake>=3.13.5", "cmake-generators", "GitPython", "svn",
                        "distro"],
      url="https://github.com/TylerGubala/bpy-build"
     )
