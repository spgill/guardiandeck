#!/bin/sh
brew install python3

pip3 install -r requirement.txt
pip3 install pyinstaller
pyinstaller -F -n guardiandeck-macos guardiandeck/main.py
