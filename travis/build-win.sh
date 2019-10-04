#!/bin/sh

# Generate names
export APP_NAME=guardiandeck
export PACKAGE_NAME=${APP_NAME}-${TRAVIS_TAG}-win64

# Install python 3 on the vm
choco install python

# refreshenv does not seem to work in bash, so reload it manually.
# Entries in the Machine PATH might contain trailing slashes, drop those.
# Apply Process paths before Machine to ensure /bin appears before others.
export PATH="$(powershell -Command '("Process", "Machine" | % {
  [Environment]::GetEnvironmentVariable("PATH", $_) -Split ";" -Replace "\\$", ""
} | Select -Unique | % { cygpath $_ }) -Join ":"')"
echo "new PATH=$PATH"

# Install dependencies and pyinstaller
pip3 install -r requirements.txt
pip3 install pyinstaller

# Build the application
pyinstaller -n ${APP_NAME} guardiandeck/main.py

# Package the app up and clean up
mv dist/${APP_NAME} dist/${PACKAGE_NAME}
tar -C dist -cvzf dist/${PACKAGE_NAME}.tar.gz ${PACKAGE_NAME}
rm -rf dist/${PACKAGE_NAME}
