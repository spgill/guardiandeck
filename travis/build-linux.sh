#!/bin/sh
pip install pyinstaller
pyinstaller -F -n guardiandeck-linux guardiandeck/main.py
