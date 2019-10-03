#!/bin/sh
pip install pyinstaller
pyinstaller -F -n guardiandeck-win.exe guardiandeck/main.py
