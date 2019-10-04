#!/bin/sh

# Generate names
export APP_NAME=guardiandeck
export PACKAGE_NAME=${APP_NAME}-${TRAVIS_TAG}-linux

# Install pyinstaller
pip install pyinstaller

# Build the application
pyinstaller -n ${APP_NAME} guardiandeck/main.py

# Package the app up and clean up
mv dist/${APP_NAME} dist/${PACKAGE_NAME}
tar -C dist -cvzf dist/${PACKAGE_NAME}.tar.gz ${PACKAGE_NAME}
rm -rf dist/${PACKAGE_NAME}
