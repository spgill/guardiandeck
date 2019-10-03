#!/bin/sh
brew install python3

pip3 install -r requirement.txt
pip3 install pyinstaller
pyinstaller -F -n guardiandeck-${TRAVIS_TAG}-macos guardiandeck/main.py
