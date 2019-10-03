#!/bin/sh
sudo apt install libusb-1.0-0-dev libudev-dev
pip install pyinstaller
pyinstaller -F -n guardiandeck-linux guardiandeck/main.py
