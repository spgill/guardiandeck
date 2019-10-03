#!/bin/sh
choco install python

# refreshenv does not seem to work in bash, so reload it manually.
# Entries in the Machine PATH might contain trailing slashes, drop those.
# Apply Process paths before Machine to ensure /bin appears before others.
export PATH="$(powershell -Command '("Process", "Machine" | % {
  [Environment]::GetEnvironmentVariable("PATH", $_) -Split ";" -Replace "\\$", ""
} | Select -Unique | % { cygpath $_ }) -Join ":"')"
echo "new PATH=$PATH"

pip install -r requirements.txt
pip install pyinstaller
pyinstaller -F -n guardiandeck-win.exe guardiandeck/main.py
