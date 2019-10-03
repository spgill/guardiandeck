#!/bin/sh
choco install python
pip install pyinstaller
pyinstaller -F -n guardiandeck-win.exe guardiandeck/main.py
