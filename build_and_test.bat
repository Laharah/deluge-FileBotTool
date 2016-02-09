taskkill /im /f deluged-debug.exe
taskkill /im /f deluge-debug.exe
set scriptdrive=%~d0
set scriptpath=%~p0
if "%ProgramFiles(x86)%"=="" (set delugepath="%ProgramFiles%") else (set delugepath="%ProgramFiles(x86)%")

%scriptdrive%
cd %scriptdrive%%scriptpath%
py -2.7 setup.py bdist_egg
py -2.6 setup.py bdist_egg
copy dist\* %APPDATA%\deluge\plugins

start cmd.exe /K "%delugepath%\Deluge\deluged-debug.exe -L debug"
start cmd.exe /K "%delugepath%\Deluge\deluge-debug.exe -L debug"
