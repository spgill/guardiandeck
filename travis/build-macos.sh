#!/bin/sh
pip install pyinstaller
pyinstaller -F -n guardiandeck-macos guardiandeck/main.py
