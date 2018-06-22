from setuptools import setup, find_packages

setup(
    name="bpybuild",
    version="1.0.1",
    packages=find_packages(),
    author="Tyler Gubala",
    author_email="gubalatyler@gmail.com",
    description="A package that builds blender",
    install_requires=["GitPython", 'cmake', 'svn;platform_system=="Windows"',
                      'python-apt;platform_system=="Linux"'],
    url="https://github.com/TylerGubala/bpy-build",
    keywords="blender 3d stub autocomplete",
    license="GPL-3.0"
)
