#!/bin/sh

# Generate names
export APP_NAME=guardiandeck
export PACKAGE_NAME=${APP_NAME}-${TRAVIS_TAG}-win64

# Install python 3 and zip on the vm
choco install python zip

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
cd dist
mv ${APP_NAME} ${PACKAGE_NAME}
zip -r ${PACKAGE_NAME}.zip ${PACKAGE_NAME}
rm -rf ${PACKAGE_NAME}

