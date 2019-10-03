#!/bin/sh
pip install pyinstaller
pyinstaller -F -n guardiandeck-${TRAVIS_TAG}-linux guardiandeck/main.py
