#!/bin/bash
if [[ $TRAVIS_OS_NAME == 'osx' ]]; then
    pip install --upgrade pip
    pip install -U twine future_fstrings cmake wheel typing setuptools
else
    pip3 install --upgrade pip
    pip3 install -U twine future_fstrings cmake wheel typing setuptools
fi