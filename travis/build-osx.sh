#!/bin/sh

# Generate names
export APP_NAME=guardiandeck
export PACKAGE_NAME=${APP_NAME}-${TRAVIS_TAG}-osx

# Install python 3 on the vm
brew install python3

# Install dependencies and pyinstaller
pip3 install -r requirements.txt
pip3 install pyinstaller

# Build the application
pyinstaller -n ${APP_NAME} guardiandeck/main.py

# Package the app up and clean up
cd dist
mv ${APP_NAME} ${PACKAGE_NAME}
tar -cvzf ${PACKAGE_NAME}.tar.gz ${PACKAGE_NAME}
rm -rf ${PACKAGE_NAME}
